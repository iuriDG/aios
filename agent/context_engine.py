import sqlite3
import json
from datetime import datetime

DB_PATH = "profiles/aios.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS app_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            binary_name TEXT NOT NULL,
            mode TEXT NOT NULL,
            cpu_avg REAL,
            ram_avg_mb REAL,
            gpu_avg REAL,
            disk_read_avg_mb REAL,
            disk_write_avg_mb REAL,
            user_override INTEGER DEFAULT 0,
            override_rules TEXT,
            last_updated TEXT,
            session_count INTEGER DEFAULT 0,
            UNIQUE(binary_name, mode)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            mode TEXT,
            gear TEXT,
            result TEXT
        )
    """)

    conn.commit()
    conn.close()

def upsert_app_profile(binary_name, mode, metrics):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        INSERT INTO app_profiles 
            (binary_name, mode, cpu_avg, ram_avg_mb, gpu_avg,
             disk_read_avg_mb, disk_write_avg_mb, last_updated, session_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(binary_name, mode) DO UPDATE SET
            cpu_avg = (cpu_avg * session_count + excluded.cpu_avg) / (session_count + 1),
            ram_avg_mb = (ram_avg_mb * session_count + excluded.ram_avg_mb) / (session_count + 1),
            gpu_avg = (gpu_avg * session_count + excluded.gpu_avg) / (session_count + 1),
            disk_read_avg_mb = (disk_read_avg_mb * session_count + excluded.disk_read_avg_mb) / (session_count + 1),
            disk_write_avg_mb = (disk_write_avg_mb * session_count + excluded.disk_write_avg_mb) / (session_count + 1),
            last_updated = excluded.last_updated,
            session_count = session_count + 1
    """, (
        binary_name, mode,
        metrics.get("cpu_avg", 0),
        metrics.get("ram_avg_mb", 0),
        metrics.get("gpu_avg", 0),
        metrics.get("disk_read_avg_mb", 0),
        metrics.get("disk_write_avg_mb", 0),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

def set_user_override(binary_name, mode, rules: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE app_profiles
        SET user_override = 1, override_rules = ?
        WHERE binary_name = ? AND mode = ?
    """, (json.dumps(rules), binary_name, mode))
    conn.commit()
    conn.close()

def get_app_profile(binary_name, mode):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT * FROM app_profiles
        WHERE binary_name = ? AND mode = ?
    """, (binary_name, mode))
    row = c.fetchone()
    conn.close()
    return row

def set_user_pref(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_profile (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_user_pref(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM user_profile WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def log_action(action, target, mode, gear, result):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO audit_log (timestamp, action, target, mode, gear, result)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), action, target, mode, gear, result))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DB initialised at", DB_PATH)