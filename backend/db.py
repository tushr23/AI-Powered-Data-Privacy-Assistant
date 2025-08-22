import sqlite3
import os

def _db_path():
    return os.environ.get("DATABASE_NAME", "privacy_assistant.db")


def get_connection():
    db_name = _db_path()
    conn = sqlite3.connect(db_name, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            input TEXT,
            findings TEXT,
            risk_score INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def add_log(event_type, input_text, findings, risk_score):
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO audit_logs (event_type, input, findings, risk_score)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, input_text, str(findings), risk_score),
            )
    finally:
        conn.close()

def get_logs():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_type, input, findings, risk_score, timestamp FROM audit_logs ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
