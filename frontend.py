# -*- coding: utf-8 -*-
import sys
import os
import requests
import random
import csv
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QComboBox, QTextEdit,
                             QScrollArea, QFrame, QMessageBox, QStackedWidget, QCheckBox, QFileDialog, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QTime, QDate, QElapsedTimer, QThread, pyqtSignal, QDateTime, QUrl
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWebEngineWidgets import QWebEngineView

SERVER_URL = "http://127.0.0.1:8080"
OLLAMA_URL = "http://localhost:11434/api/generate"

# --- Строгая регламентная дизайн-система ГБУ "Система 112" ---
POV_112_STYLE = """
    QWidget {
        background-color: #2b313e; 
        color: #ffffff;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 13px;
    }
    
    QFrame#panelBackground {
        background-color: #363d4e; 
        border: 1px solid #4f586a;
        border-radius: 0px; 
    }
    
    QLineEdit, QComboBox, QTextEdit {
        background-color: #1e222b; 
        border: 1px solid #4f586a;
        border-radius: 0px;
        padding: 6px;
        color: #ffffff;
    }
    QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
        border: 1px solid #e25c1d; 
    }
    
    QPushButton {
        background-color: #3f4756;
        border: 1px solid #5a6477;
        border-radius: 0px;
        padding: 8px 16px;
        font-weight: bold;
        color: #ffffff;
    }
    QPushButton:hover {
        background-color: #4e586c;
        border: 1px solid #e25c1d;
    }
    QPushButton:checked {
        background-color: #1e222b;
        border-bottom: 3px solid #e25c1d;
        color: #e25c1d;
    }
    
    QPushButton#orangeBtn {
        background-color: #e25c1d;
        border: none;
        color: white;
        font-weight: bold;
    }
    QPushButton#orangeBtn:hover {
        background-color: #fa6928;
    }

    QPushButton#serviceBtn {
        background-color: #d15219;
        border: 1px solid #a03c10;
        color: white;
        font-weight: bold;
        padding: 10px;
    }
    QPushButton#serviceBtn:checked {
        background-color: #1a6330;
        border: 1px solid #114220;
    }
    
    QTableWidget {
        background-color: #1e222b;
        gridline-color: #2b313e;
        border: 1px solid #4f586a;
        border-radius: 0px;
    }
    QHeaderView::section {
        background-color: #3f4756;
        padding: 10px;
        border: 1px solid #2b313e;
        font-weight: bold;
        color: #ffffff;
    }
"""

class OllamaChatWorker(QThread):
    response_received = pyqtSignal(str)

    def __init__(self, context_prompt, user_message):
        super().__init__()
        self.context_prompt = context_prompt
        self.user_message = user_message

    def run(self):
        try:
            res = requests.post(OLLAMA_URL, json={"model": "qwen2.5:3b", "prompt": f"{self.context_prompt}\nОператор: {self.user_message}\nОтветь коротко:", "stream": False}, timeout=10)
            self.response_received.emit(res.json().get("response", "Повторите связь прерывается..."))
        except Exception:
            self.response_received.emit("Алло? Пожалуйста, заполняйте поля карточки ЕКП на основе имеющихся вводных.")

class PerformanceGraph(QWidget):
    def __init__(self, stats_data=None):
        super().__init__()
        self.stats_data = stats_data if stats_data else []
        self.setMinimumHeight(240)

    def update_data(self, new_data):
        self.stats_data = new_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        padding = 50
        graph_height = height - 2 * padding
        graph_width = width - 2 * padding
        
        painter.setPen(QPen(QColor("#2d3548"), 1, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(QColor("#161a24")))
        painter.drawRoundedRect(padding, padding, graph_width, graph_height, 6, 6)
        
        if not self.stats_data:
            painter.setPen(QColor("#768594"))
            painter.setFont(QFont("Segoe UI", 11))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Нет верифицированных логов сессий для построения аналитики")
            return

        max_time = max([int(d.get('elapsed_time', '0').split()[0]) for d in self.stats_data])
        if max_time == 0: max_time = 1 
        
        points = []
        step = graph_width / max(len(self.stats_data) - 1, 1)
        
        for i, data in enumerate(self.stats_data):
            time_val = int(data.get('elapsed_time', '0').split()[0])
            x = int(padding + i * step)
            y = int(padding + graph_height - (time_val / max_time * graph_height))
            points.append((x, y, time_val, data.get('complexity', 'Средний')))

        painter.setPen(QPen(QColor("#ff6b2b"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

        for x, y, val, comp in points:
            color = "#ef4444" if comp == "Высокий" else ("#ff6b2b" if comp == "Средний" else "#10b981")
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor("#ffffff"), 1.5))
            painter.drawEllipse(x - 6, y - 6, 12, 12)
            
            painter.setPen(QPen(QColor("#ffffff")))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(x - 12, y - 14, f"{val}с")


class LoginWindow(QWidget):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.setWindowTitle("112 — Авторизация")
        self.setStyleSheet(POV_112_STYLE)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(45, 45, 45, 45)
        layout.setSpacing(16)
        
        title = QLabel("ПОВ-112 МОСКВА\nВХОД В СИСТЕМУ")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px; line-height: 26px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Идентификатор сотрудника (admin1 / student1)")
        self.username_input.setMinimumHeight(42)
        layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль доступа")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(42)
        layout.addWidget(self.password_input)
        
        login_btn = QPushButton("ПОДКЛЮЧИТЬСЯ к АРМ")
        login_btn.setObjectName("orangeBtn")
        login_btn.setMinimumHeight(44)
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)
        
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        try:
            res = requests.post(f"{SERVER_URL}/api/login", json={"username": username, "password": password}, timeout=2)
            if res.status_code == 200:
                self.on_login_success(res.json())
            else:
                QMessageBox.critical(self, "Отказ сервера", "Неверный логин или пароль")
        except Exception:
            role = "admin" if "admin" in username else "user"
            full_name = "Ермакова А.В. (Преподаватель)" if role == "admin" else "Герасимов О.И. (Обучающийся)"
            self.on_login_success({"username": username, "full_name": full_name, "role": role})


class ARM112MainInterface(QWidget):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle(f"ПОВ-112 — Смена: {self.current_user['full_name']}")
        self.setStyleSheet(POV_112_STYLE)
        
        self.session_timer = QElapsedTimer()
        self.normative_timer = QTimer(self)
        self.normative_timer.timeout.connect(self.update_card_countdown)
        self.time_left = 30
        
        self.current_active_card = None
        self.cards_data = []
        self.mock_lectures = []
        
        # 🎵 ИНИЦИАЛИЗАЦИЯ АУДИОПЛЕЕРА ДЛЯ ПРОСЛУШИВАНИЯ ЛЕКЦИЙ
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(70) # Громкость 70%
        
        self.setup_ui()

        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)
        
        # --- ВЕРХНИЙ БАР УПРАВЛЕНИЯ ---
        top_bar = QHBoxLayout()
        meta_layout = QVBoxLayout()
        self.date_label = QLabel(f"<b>Оперативные сутки: {QDate.currentDate().toString('dd.MM.yyyy')}</b>")
        self.date_label.setStyleSheet("color: #ff6b2b; font-size: 15px; font-weight: 700;")
        self.user_label = QLabel(f"Служба 112 | {self.current_user['full_name']} ({self.current_user['role'].upper()})")
        self.user_label.setStyleSheet("color: #768594; font-size: 12px;")
        meta_layout.addWidget(self.date_label)
        meta_layout.addWidget(self.user_label)
        top_bar.addLayout(meta_layout)
        
        top_bar.addSpacing(30)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)
        self.nav_group = []
        self.tabs = ["журнал", "лекции", "экран", "УПР", "БД/НН", "ИИ Шаблоны", "Профиль/Успеваемость"]
        
        for name in self.tabs:
            b = QPushButton(name)
            b.setCheckable(True)
            b.setMinimumHeight(38)
            if name == "журнал": b.setChecked(True)
            b.clicked.connect(self.handle_nav_click)
            nav_layout.addWidget(b)
            self.nav_group.append(b)
        top_bar.addLayout(nav_layout)
        
        top_bar.addStretch()
        
        right_layout = QHBoxLayout()
        right_layout.setSpacing(15)
        self.time_label = QLabel(QTime.currentTime().toString("HH:mm:ss"))
        self.time_label.setStyleSheet("font-size: 26px; font-weight: 800; color: #ffffff; font-family: 'Consolas', monospace;")
        right_layout.addWidget(self.time_label)
        
        self.create_btn = QPushButton("Создать карту")
        self.create_btn.setObjectName("orangeBtn")
        self.create_btn.setMinimumHeight(38)
        self.create_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2)) 
        right_layout.addWidget(self.create_btn)
        if self.current_user["role"] != "admin":
            self.create_btn.hide()
            
        top_bar.addLayout(right_layout)
        main_layout.addLayout(top_bar)
        
        # --- СТЕК ЭКРАНОВ ---
        self.stack = QStackedWidget()
        self.setup_journal_screen()
        self.setup_lectures_screen()     
        self.setup_creation_screen()
        self.setup_map_screen()
        self.setup_dummy_screen("Управление силами и средствами реагирования (УПР)")
        self.setup_dummy_screen("База данных нарушений и регламентов взаимодействия")
        self.setup_dummy_screen("Интеллектуальный генератор сценариев ЕКП")
        self.setup_profile_screen()
        
        main_layout.addWidget(self.stack)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(lambda: self.time_label.setText(QTime.currentTime().toString("HH:mm:ss")))
        self.clock_timer.start(1000)
        
        self.load_cards_from_db()

    def handle_nav_click(self):
        sender = self.sender()
        for btn in self.nav_group: btn.setChecked(False)
        sender.setChecked(True)
        
        idx = self.tabs.index(sender.text())
        if idx == 0:
            self.stack.setCurrentIndex(0)
        elif idx == 1:
            self.stack.setCurrentIndex(1)
            self.load_lectures()
        elif idx == 2: # 🟢 ПОЛЬЗОВАТЕЛЬ НАЖАЛ НА «ЭКРАН»
            self.stack.setCurrentIndex(3)
            self.refresh_map_widget() # Инициализируем карту строго в этот момент!
        elif idx == 6:
            self.stack.setCurrentIndex(7)
            self.load_profile_statistics()
        else:
            self.stack.setCurrentIndex(idx + 1)
            
    def refresh_map_widget(self):
        """Просто загружаем страницу с картинкой напрямую с сервера"""
        try:
            map_url = f"{SERVER_URL}/api/map"
            self.web_map_view.setUrl(QUrl(map_url))
        except Exception as e:
            self.web_map_view.setHtml(f"<h3 style='color:white; padding:20px;'>Ошибка сети: {e}</h3>")
        
    def setup_journal_screen(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Номер КП", "Время", "Тип инцидента", "Статус", "Адрес", "Сложность"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.prompt_start_training_dialog)
        layout.addWidget(self.table)
        
        self.telephony_box = QFrame()
        self.telephony_box.setObjectName("panelBackground")
        self.telephony_box.setMinimumHeight(540)
        t_layout = QHBoxLayout(self.telephony_box)
        t_layout.setContentsMargins(14, 14, 14, 14)
        t_layout.setSpacing(16)
        
        chat_panel = QVBoxLayout()
        lbl_chat_title = QLabel("ДИАЛОГОВАЯ СЕССИЯ С ЗАЯВИТЕЛЕМ (ЛИНИЯ 112)")
        lbl_chat_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #768594; letter-spacing: 0.5px;")
        chat_panel.addWidget(lbl_chat_title)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0f121a; border: 1px solid #2d3548; line-height: 20px;")
        chat_panel.addWidget(self.chat_display)
        
        chat_input_box = QHBoxLayout()
        chat_input_box.setSpacing(8)
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Задайте уточняющий вопрос пострадавшему...")
        self.chat_input.setMinimumHeight(38)
        chat_input_box.addWidget(self.chat_input)
        
        send_btn = QPushButton("Сказать")
        send_btn.setMinimumHeight(38)
        send_btn.clicked.connect(self.send_message_to_applicant)
        chat_input_box.addWidget(send_btn)
        chat_panel.addLayout(chat_input_box)
        t_layout.addLayout(chat_panel, 35)
        
        self.card_panel = QVBoxLayout()
        self.no_card_placeholder = QLabel("Выберите назначенную карточку для старта сессии телефонии и фиксации времени")
        self.no_card_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_card_placeholder.setStyleSheet("color: #768594; font-style: italic;")
        self.card_panel.addWidget(self.no_card_placeholder)
        t_layout.addLayout(self.card_panel, 65)
        
        layout.addWidget(self.telephony_box)
        self.stack.addWidget(w)

    def setup_lectures_screen(self):
        """Двухэтапная панель управления лекциями"""
        w = QWidget()
        layout = QHBoxLayout(w)
        
        self.admin_lect_panel = QFrame()
        self.admin_lect_panel.setObjectName("panelBackground")
        alp_layout = QVBoxLayout(self.admin_lect_panel)
        alp_layout.setSpacing(10)
        
        title = QLabel("ЭТАП 1: ЗАГРУЗКА ЛЕКЦИИ В БАЗУ")
        title.setStyleSheet("font-weight: bold; color: #ff6b2b;")
        alp_layout.addWidget(title)
        
        self.lect_title_input = QLineEdit()
        self.lect_title_input.setPlaceholderText("Название лекции...")
        alp_layout.addWidget(self.lect_title_input)
        
        self.btn_choose_mp3 = QPushButton("📎 Выбрать MP3 лекции")
        self.btn_choose_mp3.clicked.connect(self.choose_mp3_file)
        alp_layout.addWidget(self.btn_choose_mp3)
        self.lbl_mp3_path = QLabel("Файл не выбран")
        alp_layout.addWidget(self.lbl_mp3_path)
        
        self.btn_send_lecture = QPushButton("Загрузить в репозиторий")
        self.btn_send_lecture.setObjectName("orangeBtn")
        self.btn_send_lecture.clicked.connect(self.upload_lecture_action)
        alp_layout.addWidget(self.btn_send_lecture)
        
        alp_layout.addSpacing(15)
        title2 = QLabel("ЭТАП 2: УПРАВЛЕНИЕ ДОСТУПОМ")
        title2.setStyleSheet("font-weight: bold; color: #ff6b2b;")
        alp_layout.addWidget(title2)
        
        self.student_checkboxes_layout = QVBoxLayout()
        alp_layout.addLayout(self.student_checkboxes_layout)
        
        self.btn_save_assignments = QPushButton("Применить права доступа")
        self.btn_save_assignments.clicked.connect(self.save_lecture_assignments)
        alp_layout.addWidget(self.btn_save_assignments)
        alp_layout.addStretch()
        
        layout.addWidget(self.admin_lect_panel, 35)
        
        list_panel = QVBoxLayout()
        list_panel.addWidget(QLabel("<b>СПИСОК ЛЕКЦИЙ В СИСТЕМЕ:</b>"))
        
        self.lectures_table = QTableWidget()
        self.lectures_table.setColumnCount(3)
        self.lectures_table.setHorizontalHeaderLabels(["ID", "Название", "Аудиофайл"])
        self.lectures_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.lectures_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.lectures_table.itemSelectionChanged.connect(self.load_selected_lecture_assignments)
        list_panel.addWidget(self.lectures_table)
        
        layout.addLayout(list_panel, 65)
        
        if self.current_user["role"] != "admin":
            self.admin_lect_panel.hide()
            
        self.stack.addWidget(w)
        
    def setup_map_screen(self):
        """Интерактивная ГИС-карта оперативного мониторинга"""
        self.map_container = QWidget()
        self.map_layout = QVBoxLayout(self.map_container)
        self.map_layout.setContentsMargins(0, 0, 0, 0)
        
        # Полностью автономный браузер
        self.web_map_view = QWebEngineView()
        self.web_map_view.page().setBackgroundColor(QColor("#2b313e"))
        
        # Снимаем любые ограничения безопасности Chromium на работу с сетью и скриптами
        settings = self.web_map_view.settings()
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(settings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(settings.WebAttribute.AllowRunningInsecureContent, True)
        
        self.map_layout.addWidget(self.web_map_view)
        self.web_map_view.setMinimumSize(800, 500)
        self.stack.addWidget(self.map_container)
        
    def choose_mp3_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать аудиолекцию", "", "Audio Files (*.mp3)")
        if file_path:
            self.lbl_mp3_path.setText(os.path.basename(file_path))
            self.lbl_mp3_path.full_path = file_path # Запоминаем полный путь для отправки

    def upload_lecture_action(self):
        title = self.lect_title_input.text().strip()
        filename = self.lbl_mp3_path.text()
        full_path = getattr(self.lbl_mp3_path, "full_path", None)
        
        if not title or filename == "Файл не выбран" or not full_path: 
            QMessageBox.warning(self, "Ошибка", "Заполните название и выберите файл!")
            return
            
        try:
            # Открываем физический файл для отправки по сети
            with open(full_path, "rb") as f:
                files = {"file": (filename, f, "audio/mpeg")}
                data = {"title": title}
                res = requests.post(f"{SERVER_URL}/api/lectures", data=data, files=files, timeout=10)
                
                if res.status_code == 200:
                    QMessageBox.information(self, "Успех", f"Лекция '{title}' успешно загружена на сервер!")
                    self.lect_title_input.clear()
                    self.lbl_mp3_path.setText("Файл не выбран")
                    self.load_lectures()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось передать файл на сервер: {e}")


    def load_lectures(self):
        self.lectures_table.setRowCount(0)
        url = f"{SERVER_URL}/api/lectures/all" if self.current_user["role"] == "admin" else f"{SERVER_URL}/api/lectures/my?username={self.current_user['username']}"
        try:
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                data = res.json()
                self.lectures_table.setRowCount(len(data))
                for row, l in enumerate(data):
                    self.lectures_table.setItem(row, 0, QTableWidgetItem(str(l["id"])))
                    self.lectures_table.setItem(row, 1, QTableWidgetItem(l["title"]))
                    
                    # Создаем виджет-контейнер и кнопку воспроизведения внутри ячейки таблицы
                    btn_play = QPushButton(f"▶ Слушать ({l['file']})")
                    btn_play.setProperty("filename", l['file'])
                    btn_play.clicked.connect(self.play_lecture_file)
                    
                    # Вставляем кнопку прямо в ячейку таблицы
                    self.lectures_table.setCellWidget(row, 2, btn_play)

        except Exception:
            pass
        
    def play_lecture_file(self):
        button = self.sender()
        if not button: return
        filename = button.property("filename")
        
        # Было: server_audio_url = f"{SERVER_URL}/static/lectures/{filename}"
        server_audio_url = f"{SERVER_URL}/lectures/{filename}" # 🟢 Обновили путь к аудио
            
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.stop()
            button.setText(f"▶ Слушать ({filename})")
        else:
            # Передаем плееру сетевой URL вместо локального файла
            self.media_player.setSource(QUrl.fromUserInput(server_audio_url))
            self.media_player.play()
            button.setText("⏸ Стоп")


    def load_selected_lecture_assignments(self):
        if self.current_user["role"] != "admin": return
        row = self.lectures_table.currentRow()
        if row == -1: return
        lect_id = int(self.lectures_table.item(row, 0).text())
        
        for i in reversed(range(self.student_checkboxes_layout.count())):
            widget = self.student_checkboxes_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            
        try:
            students = requests.get(f"{SERVER_URL}/api/students", timeout=2).json()
            assigned = requests.get(f"{SERVER_URL}/api/lectures/assigned_users/{lect_id}", timeout=2).json()
            
            self.active_checkboxes = {}
            for s in students:
                cb = QCheckBox(s)
                if s in assigned: cb.setChecked(True)
                self.student_checkboxes_layout.addWidget(cb)
                self.active_checkboxes[s] = cb
        except Exception:
            pass

    def save_lecture_assignments(self):
        row = self.lectures_table.currentRow()
        if row == -1: return
        lect_id = int(self.lectures_table.item(row, 0).text())
        
        selected_students = [user for user, cb in self.active_checkboxes.items() if cb.isChecked()]
        try:
            res = requests.post(f"{SERVER_URL}/api/lectures/assign", json={"lecture_id": lect_id, "usernames": selected_students}, timeout=2)
            if res.status_code == 200:
                QMessageBox.information(self, "Права обновлены", "Доступ изменен/сохранен для выбранных учеников.")
        except Exception:
            pass

    def setup_creation_screen(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        frame = QFrame()
        frame.setObjectName("panelBackground")
        frame.setMaximumWidth(650)
        f_layout = QVBoxLayout(frame)
        f_layout.setContentsMargins(25, 25, 25, 25)
        f_layout.setSpacing(12)
        
        title = QLabel("ПАНЕЛЬ ИНСТРУКТОРА: СОЗДАНИЕ КАРТОЧКИ С НОРМАТИВОМ")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; border-bottom: 1px solid #4f586a; padding-bottom: 5px;")
        f_layout.addWidget(title)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Сложность:"))
        self.nc_priority = QComboBox()
        self.nc_priority.addItems(["Низкий", "Средний", "Высокий"])
        filter_layout.addWidget(self.nc_priority)
        
        filter_layout.addWidget(QLabel("Норматив (сек):"))
        self.nc_time_limit = QLineEdit("30")
        self.nc_time_limit.setMaximumWidth(60)
        filter_layout.addWidget(self.nc_time_limit)
        f_layout.addLayout(filter_layout)
        
        f_layout.addWidget(QLabel("Категория происшествия (неизменяемая для ученика):"))
        self.nc_type_edit = QLineEdit()
        f_layout.addWidget(self.nc_type_edit)
        
        f_layout.addWidget(QLabel("ФИО заявителя:"))
        self.nc_applicant = QLineEdit() 
        f_layout.addWidget(self.nc_applicant)
        
        f_layout.addWidget(QLabel("Скрытая фабула (Вводная для ИИ):"))
        self.nc_desc = QTextEdit() 
        self.nc_desc.setMaximumHeight(70)
        f_layout.addWidget(self.nc_desc)
        
        f_layout.addWidget(QLabel("Характер ИИ:"))
        self.nc_ai_behavior = QLineEdit() 
        f_layout.addWidget(self.nc_ai_behavior)
        
        btn_layout = QHBoxLayout()
        submit = QPushButton("Утвердить сценарий ЧС")
        submit.setObjectName("orangeBtn")
        submit.clicked.connect(self.submit_created_card)
        btn_layout.addWidget(submit)
        
        cancel = QPushButton("Отмена")
        cancel.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_layout.addWidget(cancel)
        f_layout.addLayout(btn_layout)
        
        layout.addWidget(frame)
        self.stack.addWidget(w)

    def start_interactive_telephony_session(self, card_data):
        self.current_active_card = card_data
        self.chat_display.clear()
        self.chat_display.append(f"<span style='color:#768594;'>[СИСТЕМА] Нормативный контроль активирован.</span>")
        
        for i in reversed(range(self.card_panel.count())): 
            w = self.card_panel.itemAt(i).widget()
            if w: w.setParent(None)
            
        self.time_left = int(card_data.get("time_limit", 30))
        self.session_timer.start()
        self.normative_timer.start(1000)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        card_frame = QFrame()
        card_frame.setObjectName("panelBackground")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)
        
        meta_layout = QHBoxLayout()
        meta_layout.addWidget(QLabel(f"<b>КАРТОЧКА ЕКП № {card_data['id']} [{card_data['incident_type']}]</b>"))
        self.countdown_label = QLabel(f"НОРМАТИВ: {self.time_left} сек")
        self.countdown_label.setStyleSheet("color: #ff6b2b; font-weight: bold; background-color: #0f121a; padding: 6px 12px; font-family: 'Consolas', monospace;")
        meta_layout.addWidget(self.countdown_label)
        meta_layout.addStretch()
        card_layout.addLayout(meta_layout)
        
        addr_group = QFrame()
        addr_group.setStyleSheet("background-color: #232833; padding: 6px;")
        addr_grid = QGridLayout(addr_group)
        addr_grid.setSpacing(6)
        
        addr_grid.addWidget(QLabel("Страна:"), 0, 0)
        self.edit_country = QLineEdit("Россия")
        addr_grid.addWidget(self.edit_country, 0, 1)
        addr_grid.addWidget(QLabel("Субъект:"), 0, 2)
        self.edit_region = QLineEdit("Москва")
        addr_grid.addWidget(self.edit_region, 0, 3)
        addr_grid.addWidget(QLabel("Нас. пункт:"), 0, 4)
        self.edit_city = QLineEdit("Москва")
        addr_grid.addWidget(self.edit_city, 0, 5)
        addr_grid.addWidget(QLabel("Округ:"), 1, 0)
        self.edit_okrug = QLineEdit("СВАО")
        addr_grid.addWidget(self.edit_okrug, 1, 1)
        addr_grid.addWidget(QLabel("Район:"), 1, 2)
        self.edit_district = QLineEdit("Южное Медведково")
        addr_grid.addWidget(self.edit_district, 1, 3)
        
        addr_grid.addWidget(QLabel("Улица:"), 1, 4)
        self.edit_street = QLineEdit()
        addr_grid.addWidget(self.edit_street, 1, 5)
        addr_grid.addWidget(QLabel("Дом/Вл:"), 2, 0)
        self.edit_house = QLineEdit()
        addr_grid.addWidget(self.edit_house, 2, 1)
        addr_grid.addWidget(QLabel("Корпус:"), 2, 2)
        self.edit_corp = QLineEdit()
        addr_grid.addWidget(self.edit_corp, 2, 3)
        addr_grid.addWidget(QLabel("Кв/Офис:"), 2, 4)
        self.edit_flat = QLineEdit()
        addr_grid.addWidget(self.edit_flat, 2, 5)
        
        addr_grid.addWidget(QLabel("Подъезд:"), 3, 0)
        self.edit_entrance = QLineEdit()
        addr_grid.addWidget(self.edit_entrance, 3, 1)
        addr_grid.addWidget(QLabel("Этаж:"), 3, 2)
        self.edit_floor = QLineEdit()
        addr_grid.addWidget(self.edit_floor, 3, 3)
        addr_grid.addWidget(QLabel("Код:"), 3, 4)
        self.edit_code = QLineEdit()
        addr_grid.addWidget(self.edit_code, 3, 5)
        
        card_layout.addWidget(QLabel("<b>Адрес происшествия (детализированный):</b>"))
        card_layout.addWidget(addr_group)
        
        card_layout.addWidget(QLabel("<b>Описание ситуации (со слов заявителя):</b>"))
        self.edit_desc = QTextEdit()
        self.edit_desc.setMaximumHeight(70)
        card_layout.addWidget(self.edit_desc)
        
        status_box = QHBoxLayout()
        status_box.addWidget(QLabel("Статус отработки ДДС:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Принята", "Не принята", "Работы завершены"])
        status_box.addWidget(self.combo_status)
        card_layout.addLayout(status_box)
        
        card_layout.addWidget(QLabel("<b>Вызов экстренных оперативных служб (оценивается ИИ):</b>"))
        services_layout = QHBoxLayout()
        services_layout.setSpacing(6)
        
        self.service_buttons = []
        services = ["Служба 102", "Служба 101", "ОМВД", "ЦОДД", "Мос.Без."]
        for svc in services:
            btn = QPushButton(svc)
            btn.setObjectName("serviceBtn")
            btn.setCheckable(True)
            services_layout.addWidget(btn)
            self.service_buttons.append(btn)
            
        card_layout.addLayout(services_layout)
        
        submit_btn = QPushButton("Сохранить и отправить на ИИ-контроль")
        submit_btn.setObjectName("orangeBtn")
        submit_btn.setMinimumHeight(40)
        submit_btn.clicked.connect(self.submit_telephony_results_to_db)
        card_layout.addWidget(submit_btn)
        
        scroll.setWidget(card_frame)
        self.card_panel.addWidget(scroll)
    def setup_dummy_screen(self, title_text):
        w = QWidget()
        layout = QVBoxLayout(w)
        lbl = QLabel(title_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 14px; color: #566675; font-style: italic;")
        layout.addWidget(lbl)
        self.stack.addWidget(w)

    def setup_profile_screen(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        
        self.export_layout = QHBoxLayout()
        self.export_btn = QPushButton("📥 Экспортировать ведомость успеваемости в CSV")
        self.export_btn.setObjectName("orangeBtn")
        self.export_btn.clicked.connect(self.export_statistics_to_csv)
        self.export_layout.addWidget(self.export_btn)
        if self.current_user["role"] != "admin": 
            self.export_btn.hide()
        layout.addLayout(self.export_layout)
        
        self.profile_title = QLabel("МОНИТОРИНГ УСПЕВАЕМОСТИ И ТРЕНДОВ ИНЦИДЕНТОВ")
        self.profile_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px;")
        layout.addWidget(self.profile_title)
        
        self.graph = PerformanceGraph()
        layout.addWidget(self.graph)
        
        self.stats_table = QTableWidget()
        if self.current_user["role"] == "admin":
            self.stats_table.setColumnCount(6)
            self.stats_table.setHorizontalHeaderLabels(["Студент", "Карточка", "Сложность", "Время", "Оценка ИИ", "Рецензия ИИ"])
        else:
            self.stats_table.setColumnCount(5)
            self.stats_table.setHorizontalHeaderLabels(["Карточка", "Сложность", "Время", "Оценка ИИ", "Рецензия ИИ"])
            
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.stats_table)
        self.stack.addWidget(w)

    def update_card_countdown(self):
        if self.time_left > 0:
            self.time_left -= 1
            self.countdown_label.setText(f"НОРМАТИВ: {self.time_left} сек")
            if self.time_left <= 10:
                self.countdown_label.setStyleSheet("color: #ef4444; font-weight: bold; background-color: #0f121a; padding: 6px 12px; border-radius: 4px;")
        else:
            self.normative_timer.stop()
            self.countdown_label.setText("НОРМАТИВ ПРЕВЫШЕН")
    def send_message_to_applicant(self):
        message = self.chat_input.text().strip()
        if not message or not self.current_active_card: return
        self.chat_display.append(f"<span style='color:#ff6b2b;'><b>Диспетчер:</b></span> {message}")
        self.chat_input.clear()
        ai_mood = self.current_active_card.get("ai_behavior", "Паника: заявитель кричит и путает ориентиры")
        context = f"Ты - заявитель на линии 112. Категория ЧС: {self.current_active_card['incident_type']}. Модель поведения: {ai_mood}. Отвечай коротко."
        self.worker = OllamaChatWorker(context, message)
        self.worker.response_received.connect(lambda text: self.chat_display.append(f"<b>Заявитель:</b> {text}"))
        self.worker.start()

    def load_cards_from_db(self):
        try:
            res = requests.get(f"{SERVER_URL}/api/incidents", timeout=2)
            if res.status_code == 200:
                self.cards_data = res.json()
                self.render_table(self.cards_data)
        except Exception:
            self.cards_data = [
                {"id": "913126", "datetime": "27.09.2026 14:22:00", "incident_type": "Пожар: балкон", "status": "Не оповещено", "address": "Москва", "priority": "Высокий", "description": "Горит 4 этаж", "time_limit": 30},
                {"id": "881412", "datetime": "27.09.2026 15:40:11", "incident_type": "Лифт", "status": "Зарегистрирована", "address": "Москва", "priority": "Средний", "description": "Застряли люди", "time_limit": 30}
            ]
            self.render_table(self.cards_data)

    def render_table(self, data):
        self.table.setRowCount(len(data))
        for row, card in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(str(card["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(card["datetime"]))
            self.table.setItem(row, 2, QTableWidgetItem(card["incident_type"]))
            self.table.setItem(row, 3, QTableWidgetItem(card["status"]))
            self.table.setItem(row, 4, QTableWidgetItem(card["address"]))
            self.table.setItem(row, 5, QTableWidgetItem(card["priority"]))

    def prompt_start_training_dialog(self):
        selected_row = self.table.currentRow()
        if selected_row == -1: return
        if self.current_user["role"] == "admin":
            QMessageBox.information(self, "Режим просмотра", "Вы вошли как Администратор. Полные сессии успеваемости доступны на вкладке 'Профиль/Успеваемость'.")
            return
        card_data = self.cards_data[selected_row]
        reply = QMessageBox.question(
            self, 
            "Запуск практического занятия АРМ-112",
            f"Инцидент № {card_data['id']} ({card_data['incident_type']}).\n\n"
            f"Внимание! После запуска будет активирован таймер контроля норматива ({card_data.get('time_limit', 30)} секунд).\n"
            f"Начать тренировку по кейсу?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.start_interactive_telephony_session(card_data)
        else:
            self.table.clearSelection()
    def submit_telephony_results_to_db(self):
        self.normative_timer.stop()
        elapsed_seconds = self.session_timer.elapsed() // 1000
        active_calls = [b.text() for b in self.service_buttons if b.isChecked()]
        called_services_str = ", ".join(active_calls) if active_calls else "Нет вызванных служб"
        full_address_string = f"ул. {self.edit_street.text()}, д. {self.edit_house.text()}, корп. {self.edit_corp.text()}, кв. {self.edit_flat.text()} (под. {self.edit_entrance.text()}, эт. {self.edit_floor.text()})"
        
        payload = {
            "status": self.combo_status.currentText(),
            "comment": f"Категория: {self.current_active_card['incident_type']}. Время сессии опроса: {elapsed_seconds} сек.",
            "username": self.current_user["username"],
            "address_text": full_address_string,
            "description_text": self.edit_desc.toPlainText().strip(),
            "called_services": called_services_str
        }
        try:
            res = requests.put(f"{SERVER_URL}/api/incidents/{self.current_active_card['id']}/status", json=payload, timeout=15)
            if res.status_code == 200:
                QMessageBox.information(self, "ИИ-Контроль завершен", "Карточка обработана. ИИ проверил грамотность текста и экстренные службы!")
                self.load_cards_from_db()
        except Exception:
            pass

    def submit_created_card(self):
        payload = {
            "id": str(random.randint(900000, 999999)),
            "datetime": QDateTime.currentDateTime().toString("dd.MM.yyyy HH:mm:ss"),
            "incident_type": self.nc_type_edit.text().strip(),
            "status": "Зарегистрирована",
            "address": "Ожидает заполнения",
            "description": self.nc_desc.toPlainText().strip(),
            "applicant": self.nc_applicant.text().strip(),
            "priority": self.nc_priority.currentText(),
            "comment": "",
            "ai_behavior": self.nc_ai_behavior.text().strip(),
            "time_limit": int(self.nc_time_limit.text().strip())
        }
        try:
            res = requests.post(f"{SERVER_URL}/api/incidents/create", json=payload, timeout=2)
            if res.status_code == 200:
                self.stack.setCurrentIndex(0)
                self.load_cards_from_db()
        except Exception:
            self.stack.setCurrentIndex(0)

    def export_statistics_to_csv(self):
        try:
            res = requests.get(f"{SERVER_URL}/api/admin/statistics", timeout=3)
            if res.status_code == 200:
                path, _ = QFileDialog.getSaveFileName(self, "Сохранить ведомость", "", "CSV Files (*.csv)")
                if path:
                    with open(path, mode='w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f, delimiter=';')
                        writer.writerow(["Студент", "Карточка КП", "Сложность", "Время выполнения", "Направление/Службы", "Оценка ИИ", "Рецензия ИИ"])
                        for row in res.json():
                            writer.writerow([row.get('username'), row.get('card'), row.get('complexity'), row.get('elapsed_time'), row.get('action_type'), row.get('ai_score'), row.get('ai_report')])
                    QMessageBox.information(self, "Успех", "Протокол успешно экспортирован.")
        except Exception:
            pass
    
    def load_profile_statistics(self):
        try:
            res = requests.get(f"{SERVER_URL}/api/admin/statistics", timeout=2)
            if res.status_code == 200:
                all_stats = res.json()
                stats = all_stats if self.current_user["role"] == "admin" else [s for s in all_stats if s.get('username') == self.current_user['username']]
                self.graph.update_data(stats)
                self.stats_table.setRowCount(len(stats))
                for row, stat in enumerate(stats):
                    if self.current_user["role"] == "admin":
                        self.stats_table.setItem(row, 0, QTableWidgetItem(stat.get("username")))
                        self.stats_table.setItem(row, 1, QTableWidgetItem(stat["card"]))
                        self.stats_table.setItem(row, 2, QTableWidgetItem(stat["complexity"]))
                        self.stats_table.setItem(row, 3, QTableWidgetItem(stat["elapsed_time"]))
                        self.stats_table.setItem(row, 4, QTableWidgetItem(str(stat["ai_score"])))
                        self.stats_table.setItem(row, 5, QTableWidgetItem(stat["ai_report"]))
                    else:
                        self.stats_table.setItem(row, 0, QTableWidgetItem(stat["card"]))
                        self.stats_table.setItem(row, 1, QTableWidgetItem(stat["complexity"]))
                        self.stats_table.setItem(row, 2, QTableWidgetItem(stat["elapsed_time"]))
                        self.stats_table.setItem(row, 3, QTableWidgetItem(str(stat["ai_score"])))
                        self.stats_table.setItem(row, 4, QTableWidgetItem(stat["ai_report"]))
        except Exception:
            pass

class AppController(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учебный тренажёр АРМ-112")
        self.resize(1300, 850)
        self.setStyleSheet(POV_112_STYLE)
        self.login_window = LoginWindow(self.show_main_interface)
        self.addWidget(self.login_window)
        self.setCurrentIndex(0)
        
    def show_main_interface(self, user_data):
        self.main_interface = ARM112MainInterface(user_data)
        self.addWidget(self.main_interface)
        self.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = AppController()
    controller.show()
    sys.exit(app.exec())