import os
import bcrypt
import json
import sqlite3
from datetime import datetime
from urllib.parse import urlparse

# Optional PostgreSQL support
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

class Database:
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.is_postgres = False
        
        if self.db_url and (self.db_url.startswith("postgres") or self.db_url.startswith("postgresql")):
            if not HAS_POSTGRES:
                print("⚠️ psycopg2 not found. Falling back to SQLite.")
            else:
                self.is_postgres = True
        
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            result = urlparse(self.db_url)
            return psycopg2.connect(
                database=result.path.lstrip('/'),
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port,
                cursor_factory=RealDictCursor
            )
        else:
            conn = sqlite3.connect("inkognito.db")
            conn.row_factory = sqlite3.Row
            return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        report_id TEXT UNIQUE NOT NULL,
                        subject_name TEXT NOT NULL,
                        generated_at TIMESTAMP NOT NULL,
                        report_path TEXT NOT NULL
                    )
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        report_id TEXT UNIQUE NOT NULL,
                        subject_name TEXT NOT NULL,
                        generated_at DATETIME NOT NULL,
                        report_path TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
            conn.commit()
            print(f"✅ Database initialized ({'PostgreSQL' if self.is_postgres else 'SQLite'})")
        except Exception as e:
            print(f"❌ Database Init Error: {e}")
        finally:
            conn.close()

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def _check_password(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except:
            return False

    def register_user(self, username, password):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            pw_hash = self._hash_password(password)
            if self.is_postgres:
                cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id", (username, pw_hash))
                uid = cur.fetchone()['id']
            else:
                cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
                uid = cur.lastrowid
            conn.commit()
            return str(uid)
        except:
            return None
        finally:
            conn.close()

    def authenticate_user(self, username, password):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
            else:
                cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
            
            user = cur.fetchone()
            if user and self._check_password(password, user['password_hash']):
                return {"id": str(user['id']), "username": user['username']}
        except:
            pass
        finally:
            conn.close()
        return None

    def save_report_metadata(self, user_id, report_id, subject_name, generated_at, report_path):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    "INSERT INTO reports (user_id, report_id, subject_name, generated_at, report_path) VALUES (%s, %s, %s, %s, %s)",
                    (int(user_id), report_id, subject_name, generated_at, report_path)
                )
            else:
                cur.execute(
                    "INSERT INTO reports (user_id, report_id, subject_name, generated_at, report_path) VALUES (?, ?, ?, ?, ?)",
                    (int(user_id), report_id, subject_name, generated_at, report_path)
                )
            conn.commit()
        finally:
            conn.close()

    def get_user_reports(self, user_id):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("SELECT report_id, subject_name, generated_at, report_path FROM reports WHERE user_id = %s ORDER BY generated_at DESC", (int(user_id),))
            else:
                cur.execute("SELECT report_id, subject_name, generated_at, report_path FROM reports WHERE user_id = ? ORDER BY generated_at DESC", (int(user_id),))
            
            reports = []
            for row in cur.fetchall():
                r = dict(row)
                if isinstance(r['generated_at'], datetime):
                    r['generated_at'] = r['generated_at'].isoformat()
                reports.append(r)
            return reports
        finally:
            conn.close()

    def get_user_by_id(self, user_id):
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("SELECT id, username FROM users WHERE id = %s", (int(user_id),))
            else:
                cur.execute("SELECT id, username FROM users WHERE id = ?", (int(user_id),))
            
            user = cur.fetchone()
            if user:
                return {"id": str(user['id']), "username": user['username']}
        except:
            pass
        finally:
            conn.close()
        return None
