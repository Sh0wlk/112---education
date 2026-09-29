# ARM-112 Automated Workstation: Modernized Training Simulator

An information system and interactive simulator designed for emergency dispatchers of the "System 112" service in Moscow. The application allows trainees to handle emergency scenarios, tracks time limits for filling out unified emergency cards (EKP), and uses local AI to evaluate dispatcher performance.

Its an a submission on a LCT hackathon of an XD team, made with love and passion :)
links:
  vids:
    1) https://drive.google.com/file/d/1XbN5EVsrpKEmKTm0r0tqzf5YGG-P3vxp/view?usp=sharing
    2) https://drive.google.com/file/d/1foLIZY-kRiXD39Rs_4txiFyn2AHO4tXG/view?usp=sharing
  presentation:
    https://docs.google.com/presentation/d/1ukwPNwPgumriGu-vx_c2tQ91n48GPC5x/edit?usp=sharing&ouid=102541825497758279433&rtpof=true&sd=true
  full documentation on russian:
    https://drive.google.com/file/d/1SpF5vW1u1NLWEBU9v9asck5kCuJGydEH/view?usp=sharing

## 🚀 Tech Stack
* **Backend:** FastAPI (Python), PostgreSQL, and integration with a local Ollama LLM instance (running the `qwen2.5:3b` model).
* **Frontend:** Desktop application built with PyQt6 (Python) using an embedded Chromium rendering engine (`QWebEngineView`).

---

## 🛠 Prerequisites

Before starting the application, ensure you have the following installed:
1. **Python 3.10+**
2. **PostgreSQL** (Create a database named `my_local_db`)
3. **Ollama** (Required for AI-powered applicant behavior simulation and quality checks)

---

## 📦 Installation & Setup

### 1. Folder Structure & Assets
Ensure that the directory for map layers and assets exists on your local machine at the exact path:
`D:\HACKXD\backend\serv_stat\`

This folder **must** contain the following background image file:
* `moscow_map.png` — The background map image for the monitoring screen.

### 2. Install Dependencies
Install all required Python packages using the provided configurations file:
```bash
pip install -r requirements.txt
```

### 3. Pull the AI Model (Ollama)
Make sure the Ollama application is running in the background, then download the required language model:
```bash
ollama run qwen2.5:3b
```

---

## 🚦 How to Run

The system consists of two separate modules. They must be launched in order (Backend first, then Frontend).

### Step 1: Run the Server (Backend)
Open your terminal, navigate to the project directory, and start the backend:
```bash
python server.py
```
*The server automatically initializes all necessary tables in your PostgreSQL database and creates default user accounts upon the first launch. The backend will be active at `http://127.0.0.1:8080`*

### Step 2: Run the App (Frontend Client)
Open a new terminal window and launch the desktop UI:
```bash
python client.py
```

---

## 🔑 Test Accounts (Credentials)

The database comes pre-seeded with the following credentials for testing:

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| **admin1** | `admin` | Instructor / Admin | Can create emergency cards, upload audio lectures, manage access controls, and export statistics to CSV. |
| **student1** | `1234` | Trainee / User | Can launch training sessions, chat with the applicant against the countdown timer, listen to assigned lectures, and view progress graphs. |
| **student2** | `1234` | Trainee / User | Secondary student test account. |

---

## 📈 Key Features
* **Incident Log:** View and filter existing emergency cases.
* **Monitoring Screen:** Displays the live Moscow asset map (`moscow_map.png`) fetched straight from the server.
* **Simulated Telephony:** An interactive chat interface simulating a real call, where applicant responses are generated on-the-fly by the LLM.
* **SLA/Normative Control:** An active countdown timer with dynamic color warnings when processing time limits are reached.
* **Lecture Repository:** Instructors can upload `.mp3` audio files and assign access rights to specific students.
* **Performance Analysis:** Custom analytics rendering using `QPainter` along with comprehensive CSV data exporting for grading sheets.
