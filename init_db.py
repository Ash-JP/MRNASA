"""
Initialize SQLite DB with a simple users table and a default admin & planner accounts.
Run once: python init_db.py
"""
import sqlite3
from werkzeug.security import generate_password_hash
from config import Config

conn = sqlite3.connect(Config.DATABASE)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','planner'))
)
''')
# Insert default users (password: adminpass / plannerpass) - change on first run
try:
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", generate_password_hash("adminpass"), "admin"))
    cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("planner", generate_password_hash("plannerpass"), "planner"))
    conn.commit()
    print("Inserted default admin/planner users (admin/adminpass, planner/plannerpass). Change passwords ASAP.")
except Exception as e:
    print("Probably already initialized:", e)
conn.close()
