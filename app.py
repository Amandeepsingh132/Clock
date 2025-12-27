import webview
import sqlite3
import json
import os
import sys
from datetime import datetime

class AuraApi:
    def __init__(self):
        # Determine the base directory for data (portable mode)
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.db_path = os.path.join(self.base_dir, 'my_database.db')
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Tasks Table
        c.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status INTEGER DEFAULT 0,
            scheduled_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        # Sessions Table (Logs Work and Break times)
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration INTEGER, -- in seconds
            type TEXT, -- 'work' or 'break'
            date TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id)
        )''')
        conn.commit()
        conn.close()

    def get_tasks(self):
        """Fetch all tasks for the current day."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Only show tasks for today
            c.execute("SELECT id, title, status, scheduled_date FROM tasks WHERE scheduled_date = date('now', 'localtime') ORDER BY status ASC, created_at DESC")
            tasks = [{'id': r[0], 'title': r[1], 'status': r[2], 'scheduled_date': r[3]} for r in c.fetchall()]
            conn.close()
            return tasks
        except Exception as e:
            return []

    def add_task(self, title):
        """Add a new task, scheduled for today."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Automatically set date to today
        c.execute("INSERT INTO tasks (title, scheduled_date) VALUES (?, date('now', 'localtime'))", (title,))
        conn.commit()
        conn.close()
        return True

    def toggle_task(self, task_id, status):
        """Mark task as completed/uncompleted."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
        conn.close()
        return True

    def delete_task(self, task_id):
        """Remove a task."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True

    def save_session(self, task_id, start_time, end_time, duration, session_type):
        """Log a work or break session."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO sessions (task_id, start_time, end_time, duration, type, date) VALUES (?, ?, ?, ?, ?, ?)",
                  (task_id, start_time, end_time, duration, session_type, date_str))
        conn.commit()
        conn.close()
        return True

    def get_history(self):
        """Get recent logs for the sidebar."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT s.*, t.title as task_title 
            FROM sessions s 
            LEFT JOIN tasks t ON s.task_id = t.id 
            ORDER BY s.id DESC LIMIT 30
        """)
        history = [dict(row) for row in c.fetchall()]
        conn.close()
        return history

    def export_sessions_to_csv(self):
        """Export all sessions to a CSV file in the app directory."""
        import csv
        output_path = os.path.join(self.base_dir, 'session_history.csv')
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT s.id, t.title as task_title, s.start_time, s.end_time, s.duration, s.type, s.date 
                FROM sessions s 
                LEFT JOIN tasks t ON s.task_id = t.id 
                ORDER BY s.id DESC
            """)
            rows = c.fetchall()
            
            with open(output_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Task', 'Start Time', 'End Time', 'Duration (s)', 'Type', 'Date'])
                for row in rows:
                    writer.writerow(list(row))
            
            conn.close()
            return f"Success! Exported to {output_path}"
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == '__main__':
    api = AuraApi()
    
    # Locate index.html
    if getattr(sys, 'frozen', False):
        template_dir = sys._MEIPASS
    else:
        template_dir = os.path.dirname(os.path.abspath(__file__))
    
    index_path = os.path.join(template_dir, 'index.html')
    
    # Create the window with Apple-style dimensions
    window = webview.create_window(
        'Aura Focus - Desktop Productivity', 
        url=index_path, 
        js_api=api,
        width=1200,
        height=800,
        min_size=(1000, 700),
        background_color='#171717'
    )
    
    # Run the application
    webview.start()
