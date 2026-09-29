# -*- coding: utf-8 -*-
import re
import json
import hashlib
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import requests
from fastapi import UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import shutil
import os
from fastapi.responses import HTMLResponse

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

app = FastAPI(title="Сервер АРМ-112: Модернизированный")

OLLAMA_URL = "http://localhost:11434/api/generate"

DB_CONFIG = {
    "dbname": "my_local_db",
    "user": "postgres",
    "password": "Sakuromoti3!", 
    "host": "127.0.0.1",
    "port": "5432"
}

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2_sha256$100000${salt}${pwd_hash.hex()}"

def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations, salt, hash_val = encoded_hash.split('$')
        iterations = int(iterations)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
        return secrets.compare_digest(new_hash.hex(), hash_val)
    except Exception:
        return False

# --- СХЕМЫ ДАННЫХ ---
class LoginRequest(BaseModel):
    username: str
    password: str

class IncidentCreateRequest(BaseModel):
    id: str
    datetime: str
    incident_type: str
    status: str
    address: str
    description: str
    applicant: str
    priority: str
    comment: str
    ai_behavior: str 
    time_limit: int # ⏱ Кастомный норматив времени в секундах

class StatusUpdateRequest(BaseModel):
    status: str
    comment: str
    username: str
    address_text: Optional[str] = ""
    description_text: Optional[str] = ""
    called_services: Optional[str] = "" # 🚨 Переданный список вызванных служб через запятую

class LectureCreateRequest(BaseModel):
    title: str
    file: str

class LectureAssignRequest(BaseModel):
    lecture_id: int
    usernames: List[str] # Список тех, кому даем доступ. Кого нет в списке - доступ забирается.

def seed_default_data():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_client_encoding('UTF8')
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    full_name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS incident_cards (
                    id VARCHAR(20) PRIMARY KEY,
                    datetime VARCHAR(30) NOT NULL,
                    incident_type TEXT NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    address TEXT NOT NULL,
                    description TEXT,
                    applicant TEXT,
                    priority VARCHAR(20) NOT NULL,
                    comment TEXT,
                    ai_behavior TEXT,
                    time_limit INT DEFAULT 30
                );
                CREATE TABLE IF NOT EXISTS incident_logs (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                    incident_id VARCHAR(20) REFERENCES incident_cards(id) ON DELETE CASCADE,
                    complexity VARCHAR(20) NOT NULL,
                    elapsed_time_seconds INT NOT NULL,
                    action_type TEXT NOT NULL,
                    ai_score INT DEFAULT 5,
                    ai_report TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS lectures (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                -- 🔗 Таблица связей: Кому назначена лекция
                CREATE TABLE IF NOT EXISTS lecture_assignments (
                    lecture_id INT REFERENCES lectures(id) ON DELETE CASCADE,
                    username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                    PRIMARY KEY (lecture_id, username)
                );
            """)
            
            cursor.execute("SELECT COUNT(*) FROM users;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO users (username, password, role, full_name) VALUES 
                    ('admin1', %s, 'admin', 'Ермакова А.В. (Преподаватель)'),
                    ('student1', %s, 'user', 'Герасимов О.И. (Обучающийся)'),
                    ('student2', %s, 'user', 'Кузнецова М.Д. (Обучающийся)');
                """, (hash_password('admin'), hash_password('1234'), hash_password('1234')))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Ошибка инициализации БД]: {e}")

seed_default_data()

@app.post("/api/login")
def login(data: LoginRequest):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT username, password, role, full_name FROM users WHERE username = %s", (data.username,))
            user = cursor.fetchone()
            if user and verify_password(data.password, user['password']):
                return {"username": user['username'], "role": user['role'], "full_name": user['full_name']}
    raise HTTPException(status_code=401, detail="Неверный логин или пароль")

@app.get("/api/incidents")
def get_incidents():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM incident_cards ORDER BY datetime DESC;")
            return cursor.fetchall()

@app.post("/api/incidents/create")
def create_incident(data: IncidentCreateRequest):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO incident_cards (id, datetime, incident_type, status, address, description, applicant, priority, comment, ai_behavior, time_limit) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (data.id, data.datetime, data.incident_type, data.status, data.address, data.description, data.applicant, data.priority, data.comment, data.ai_behavior, data.time_limit)
                )
                conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/incidents/{incident_id}/status")
def update_status(incident_id: str, data: StatusUpdateRequest):
    try:
        time_match = re.search(r"Время сессии опроса: (\d+) сек", data.comment)
        elapsed_time = int(time_match.group(1)) if time_match else 0
        
        ai_score = 5
        ai_report = "Проверка завершена. Нарушений нет."
        
        if data.address_text and data.description_text:
            analysis_prompt = f"""
            Ты - инспектор контроля качества Службы 112 Москвы.
            Проверь карточку, заполненную оператором.
            Категория происшествия: {data.comment}
            Введенный адрес: {data.address_text}
            Описание ситуации диспетчером: {data.description_text}
            Вызванные диспетчером службы: [{data.called_services}]
            Выведи ответ строго в формате JSON:
            {{"score": оценка_числом, "report": "короткий текст рецензии на русском языке"}}
            """
            try:
                res = requests.post(OLLAMA_URL, json={"model": "qwen2.5:3b", "prompt": analysis_prompt, "stream": False}, timeout=12)
                if res.status_code == 200:
                    ai_response = res.json().get("response", "").strip()
                    json_match = re.search(r"\{.*\}", ai_response)
                    if json_match:
                        ai_data = json.loads(json_match.group(0))
                        ai_score = int(ai_data.get("score", 5))
                        ai_report = ai_data.get("report", ai_report)
            except Exception:
                ai_report = "ИИ-анализ временно недоступен. Службы проверены в ручном режиме."

        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE incident_cards SET status = %s, address = %s, description = %s WHERE id = %s;", 
                               (data.status, data.address_text, data.description_text, incident_id))
                
                cursor.execute("SELECT priority FROM incident_cards WHERE id = %s;", (incident_id,))
                res = cursor.fetchone()
                priority = res[0] if res else "Средний"
                
                cursor.execute(
                    """INSERT INTO incident_logs (username, incident_id, complexity, elapsed_time_seconds, action_type, ai_score, ai_report) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                    (data.username, incident_id, priority, elapsed_time, f"Вызов служб: {data.called_services}", ai_score, ai_report)
                )
                conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/statistics")
def get_statistics():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT l.username, l.incident_id as card, l.complexity, 
                CONCAT(l.elapsed_time_seconds, ' секунд') as elapsed_time,
                l.action_type, l.ai_score, l.ai_report
                FROM incident_logs l ORDER BY l.timestamp DESC;
            """)
            return cursor.fetchall()

# --- УПРАВЛЕНИЕ ЛЕКЦИЯМИ (ЭТАП 1: ЗАГРУЗКА В БД) ---
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "server_lectures")
os.makedirs(UPLOAD_DIR, exist_ok=True)
# 🟢 Заменили префикс на /lectures, чтобы он не конфликтовал с картой
app.mount("/lectures", StaticFiles(directory=UPLOAD_DIR), name="lectures")

# Настройка абсолютного пути к папке со статическими файлами
STATIC_DIR = r"D:\HACKXD\backend\serv_stat"
os.makedirs(STATIC_DIR, exist_ok=True)

# Монтируем статические файлы карт с поддержкой кэширования и проверки
app.mount("/static", StaticFiles(directory=STATIC_DIR, html=False), name="static")

@app.get("/api/map", response_class=HTMLResponse)
def get_universal_map(t: Optional[str] = None):
    """Просто отображаем картинку moscow_map.png во всю доступную область"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Карта Москвы</title>
        <style>
            html, body {
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background-color: #2b313e;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
            }
            img {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain; /* Картинка пропорционально впишется в экран */
            }
        </style>
    </head>
    <body>
        <img src="/static/moscow_map.png" alt="Карта Москвы">
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, media_type="text/html; charset=utf-8")


@app.post("/api/lectures")
def add_lecture(title: str = Form(...), file: UploadFile = File(...)):
    """Эндпоинт принимает настоящий файл и сохраняет его на сервере"""
    try:
        # Сохраняем файл на диск сервера
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Записываем метаданные в PostgreSQL
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO lectures (title, file_name) VALUES (%s, %s);", (title, file.filename))
                conn.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/lectures/all")
def get_all_lectures():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, title, file_name as file FROM lectures ORDER BY id DESC;")
            return cursor.fetchall()

# --- НАЗНАЧЕНИЕ ЛЕКЦИЙ (ЭТАП 2: УПРАВЛЕНИЕ ДОСТУПОМ) ---
@app.post("/api/lectures/assign")
def assign_lecture(data: LectureAssignRequest):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM lecture_assignments WHERE lecture_id = %s;", (data.lecture_id,))
            for user in data.usernames:
                cursor.execute("INSERT INTO lecture_assignments (lecture_id, username) VALUES (%s, %s);", (data.lecture_id, user))
            conn.commit()
    return {"status": "success"}

@app.get("/api/lectures/assigned_users/{lecture_id}")
def get_assigned_users(lecture_id: int):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM lecture_assignments WHERE lecture_id = %s;", (lecture_id,))
            return [row[0] for row in cursor.fetchall()]

@app.get("/api/lectures/my")
def get_my_lectures(username: str):
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT l.id, l.title, l.file_name as file FROM lectures l
                INNER JOIN lecture_assignments la ON l.id = la.lecture_id
                WHERE la.username = %s ORDER BY l.id DESC;
            """, (username,))
            return cursor.fetchall()

@app.get("/api/students")
def get_students_list():
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT username FROM users WHERE role = 'user';")
            return [row[0] for row in cursor.fetchall()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
