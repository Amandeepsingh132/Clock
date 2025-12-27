import webview
import sqlite3
import os
import sys
import csv
from datetime import datetime

# The entire HTML/CSS/JS is baked directly into the Python code
# This allows for a single standalone .exe without external file dependencies
HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aura Focus</title>
    <style>
        :root {
            --bg-dark: #171717;
            --bg-card: rgba(33, 33, 33, 0.4);
            --accent: #E1BEE7;
            --text-main: #FFFFFF;
            --text-dim: #A0A0A0;
            --glass-border: rgba(255, 255, 255, 0.05);
        }

        body {
            margin: 0; padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            height: 100vh; overflow: hidden;
        }

        /* Procedural Aura (Lighter than GIF) */
        #aura-bg {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: -2;
            background: radial-gradient(circle at 50% 50%, #2c1a3d 0%, #171717 100%);
            transition: opacity 2s ease;
        }

        .blob {
            position: absolute;
            width: 600px; height: 600px;
            background: #4a148c;
            filter: blur(120px);
            border-radius: 50%;
            opacity: 0.15;
            transition: transform 5s ease, opacity 2s ease;
        }

        .paused .blob {
            opacity: 0.05;
            transform: scale(0.8) !important;
        }

        .app-container {
            display: grid;
            grid-template-columns: 1fr 340px;
            width: 100%; height: 100vh;
            position: relative; z-index: 10;
        }

        .main-content {
            padding: 40px; display: flex; flex-direction: column; align-items: center; position: relative;
        }

        .task-panel {
            background: rgba(23, 23, 23, 0.6);
            backdrop-filter: blur(40px);
            border-left: 1px solid var(--glass-border);
            padding: 30px; display: flex; flex-direction: column;
        }

        .card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--glass-border);
            padding: 40px; border-radius: 32px;
            text-align: center; min-width: 400px;
        }

        .timer-display {
            display: flex; align-items: baseline; gap: 4px; justify-content: center;
        }

        .btn {
            border: none; border-radius: 50%; width: 64px; height: 64px;
            cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            background: rgba(255, 255, 255, 0.05); color: white;
            display: flex; align-items: center; justify-content: center;
        }

        .btn:hover { transform: scale(1.05); background: rgba(255, 255, 255, 0.1); }

        .btn-play { background: var(--accent); color: black; }

        .task-item {
            display: flex; align-items: center; gap: 12px; padding: 16px;
            background: rgba(255, 255, 255, 0.02); border-radius: 16px;
            margin-bottom: 10px; transition: 0.2s;
        }

        .checkbox { width: 20px; height: 20px; border: 2px solid var(--accent); border-radius: 50%; cursor: pointer; }
        .checked { background: var(--accent); }
        .completed { text-decoration: line-through; opacity: 0.4; }

        .add-task-btn {
            background: rgba(255, 255, 255, 0.05); border: 1px solid var(--glass-border);
            color: white; padding: 16px; border-radius: 16px; width: 100%;
            cursor: pointer; font-weight: 600; margin-top: auto;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.05); border: none; color: white;
            padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
        }

        .dim { color: var(--text-dim); font-size: 14px; }
    </style>
</head>
<body class="paused">
    <div id="aura-bg">
        <div class="blob" id="blob1" style="top: -10%; left: -10%;"></div>
        <div class="blob" id="blob2" style="bottom: -10%; right: -10%; background: #311b92;"></div>
    </div>

    <div class="app-container">
        <div class="main-content">
            <button onclick="exportData()" class="btn-secondary" style="position: absolute; top: 20px; left: 20px;">Export Data</button>
            <h1 style="margin-top: 20px; opacity: 0.8; font-weight: 500;">Aura Focus</h1>
            
            <div id="timer-container" style="flex:1; display:flex; align-items:center; justify-content:center; width:100%;">
                <div class="card">
                    <div style="font-size: 12px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.4; margin-bottom: 15px;">Focus Session</div>
                    <div class="timer-display">
                        <span id="time-main" style="font-size: 80px; font-weight: 500;">00:00:00</span>
                        <span id="time-ms" style="font-size: 40px; opacity: 0.5; width: 60px; text-align: left;">.00</span>
                    </div>
                    <div style="display: flex; justify-content: center; gap: 50px; margin-bottom: 40px; opacity: 0.3; font-size: 14px; margin-left: -40px;">
                        <span>hr</span><span>min</span><span>sec</span>
                    </div>
                    <div style="display: flex; justify-content: center; gap: 20px;">
                        <button class="btn btn-play" id="play-btn" onclick="toggleTimer()">▶</button>
                        <button class="btn" onclick="resetTimer()">↺</button>
                    </div>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin-bottom: 40px;">
                <button class="btn-secondary" onclick="setTimer(300)">5m</button>
                <button class="btn-secondary" onclick="setTimer(1500)">25m</button>
                <button class="btn-secondary" onclick="setTimer(3600)">1h</button>
            </div>
        </div>

        <div class="task-panel">
            <h2 style="font-size: 24px; margin-bottom: 5px;">Today</h2>
            <p class="dim" id="date-label" style="margin-bottom: 30px;"></p>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="font-size: 13px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.5;">Focus List</h3>
                <span class="dim" id="task-count">0</span>
            </div>

            <div id="task-list" style="flex:1; overflow-y:auto;"></div>
            <button class="add-task-btn" onclick="handleAddTask()">+ Add Task</button>
        </div>
    </div>

    <script>
        let ms = 0;
        let isActive = false;
        let interval = null;
        let lastTick = null;

        window.addEventListener('pywebviewready', () => {
            const today = new Date();
            document.getElementById('date-label').innerText = today.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
            refreshTasks();
            animateBlobs();
        });

        async function refreshTasks() {
            const tasks = await pywebview.api.get_tasks();
            const list = document.getElementById('task-list');
            list.innerHTML = '';
            document.getElementById('task-count').innerText = tasks.length;
            
            tasks.forEach(t => {
                const el = document.createElement('div');
                el.className = 'task-item';
                el.innerHTML = `
                    <div class="checkbox ${t.status ? 'checked' : ''}" onclick="toggleTask(${t.id}, ${t.status})"></div>
                    <div style="flex:1" class="${t.status ? 'completed' : ''}">${t.title}</div>
                    <div style="opacity:0.2; cursor:pointer;" onclick="deleteTask(${t.id})">✕</div>
                `;
                list.appendChild(el);
            });
        }

        function toggleTimer() {
            const btn = document.getElementById('play-btn');
            const body = document.body;
            if(isActive) {
                clearInterval(interval);
                isActive = false;
                btn.innerText = '▶';
                body.classList.add('paused');
                pywebview.api.save_session(null, '', '', Math.floor(ms/1000), 'focus');
            } else {
                isActive = true;
                lastTick = Date.now();
                btn.innerText = 'Ⅱ';
                body.classList.remove('paused');
                interval = setInterval(() => {
                    const now = Date.now();
                    ms += (now - lastTick);
                    lastTick = now;
                    updateDisplay();
                }, 50);
            }
        }

        function updateDisplay() {
            const h = Math.floor(ms / 3600000);
            const m = Math.floor((ms % 3600000) / 60000);
            const s = Math.floor((ms % 60000) / 1000);
            const curMs = Math.floor((ms % 1000) / 10);
            
            document.getElementById('time-main').innerText = 
                `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
            document.getElementById('time-ms').innerText = `.${curMs.toString().padStart(2,'0')}`;
        }

        function resetTimer() {
            if(isActive) toggleTimer();
            ms = 0;
            updateDisplay();
        }

        function setTimer(secs) {
            resetTimer();
            ms = secs * 1000;
            updateDisplay();
        }

        async function handleAddTask() {
            const title = prompt("What's your priority?");
            if(title) { await pywebview.api.add_task(title); refreshTasks(); }
        }

        async function toggleTask(id, s) { await pywebview.api.toggle_task(id, s?0:1); refreshTasks(); }
        async function deleteTask(id) { await pywebview.api.delete_task(id); refreshTasks(); }
        async function exportData() { alert(await pywebview.api.export_sessions_to_csv()); }

        function animateBlobs() {
            const b1 = document.getElementById('blob1');
            const b2 = document.getElementById('blob2');
            setInterval(() => {
                if(!isActive) return;
                const r1 = Math.random() * 40 - 20;
                const r2 = Math.random() * 40 - 20;
                b1.style.transform = `translate(${r1}px, ${r2}px) scale(${1 + Math.random()*0.2})`;
                b2.style.transform = `translate(${r2}px, ${r1}px) scale(${1 + Math.random()*0.2})`;
            }, 3000);
        }
    </script>
</body>
</html>
"""

class AuraApi:
    def __init__(self):
        # Portable DB location: same folder as the EXE
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.db_path = os.path.join(self.base_dir, 'aura_data.db')
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status INTEGER DEFAULT 0,
            scheduled_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            duration INTEGER,
            type TEXT,
            date TEXT
        )''')
        conn.commit()
        conn.close()

    def get_tasks(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT id, title, status FROM tasks WHERE scheduled_date = date('now', 'localtime') ORDER BY status ASC, id DESC")
            tasks = [{'id': r[0], 'title': r[1], 'status': r[2]} for r in c.fetchall()]
            conn.close()
            return tasks
        except: return []

    def add_task(self, title):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO tasks (title, scheduled_date) VALUES (?, date('now', 'localtime'))", (title,))
        conn.commit()
        conn.close()
        return True

    def toggle_task(self, id, status):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, id))
        conn.commit()
        conn.close()
        return True

    def delete_task(self, id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        return True

    def save_session(self, task_id, start, end, duration, session_type):
        if duration < 5: return False
        date_str = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO sessions (task_id, duration, type, date) VALUES (?, ?, ?, ?)", (task_id, duration, session_type, date_str))
        conn.commit()
        conn.close()
        return True

    def export_sessions_to_csv(self):
        output_path = os.path.join(self.base_dir, 'aura_sessions.csv')
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT s.id, t.title, s.duration, s.type, s.date FROM sessions s LEFT JOIN tasks t ON s.task_id = t.id")
            rows = c.fetchall()
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['ID', 'Task', 'Duration(s)', 'Type', 'Date'])
                w.writerows(rows)
            conn.close()
            return f"Exported to {output_path}"
        except Exception as e: return f"Error: {e}"

if __name__ == '__main__':
    api = AuraApi()
    window = webview.create_window(
        'Aura Focus - Standalone',
        html=HTML_CONTENT,
        js_api=api,
        width=1100, height=750,
        background_color='#171717'
    )
    webview.start()
