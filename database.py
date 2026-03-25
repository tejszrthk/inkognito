import os, sqlite3, bcrypt, json
from datetime import datetime
from urllib.parse import urlparse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

class Database:
    def __init__(self, url=None):
        self.url = url or os.getenv("DATABASE_URL")
        self.is_pg = False
        if self.url and ("postgre" in self.url or "rlwy.net" in self.url):
            if HAS_POSTGRES: self.is_pg = True
            else: print("⚠️ psycopg2-binary missing; falling back to SQLite.")
        
        try: self._init_schema()
        except Exception as e: print(f"⚠️ DB Init Delayed: {e}")

    def _conn(self):
        if self.is_pg:
            p = urlparse(self.url)
            return psycopg2.connect(
                database=p.path.lstrip('/'),
                user=p.username, password=p.password,
                host=p.hostname, port=p.port,
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )
        else:
            c = sqlite3.connect("nk.db")
            c.row_factory = sqlite3.Row
            return c

    def _init_schema(self):
        with self._conn() as cn:
            cur = cn.cursor()
            if self.is_pg:
                cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, password TEXT, created_at TIMESTAMP DEFAULT NOW())")
                cur.execute("CREATE TABLE IF NOT EXISTS reports (id SERIAL PRIMARY KEY, user_id INT, report_id TEXT UNIQUE, name TEXT, date TIMESTAMP, path TEXT)")
            else:
                cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
                cur.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT, report_id TEXT UNIQUE, name TEXT, date DATETIME, path TEXT)")
            cn.commit()
            print(f"✅ DB Ready: {'PostgreSQL' if self.is_pg else 'SQLite'}")

    def reg(self, u, p):
        try:
            with self._conn() as cn:
                cur = cn.cursor()
                hw = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                if self.is_pg:
                    cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id", (u, hw))
                    uid = cur.fetchone()['id']
                else:
                    cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, hw))
                    uid = cur.lastrowid
                cn.commit()
                return str(uid)
        except Exception as e:
            print(f"❌ Reg error: {e}")
            return None

    def auth(self, u, p):
        try:
            with self._conn() as cn:
                cur = cn.cursor()
                if self.is_pg: cur.execute("SELECT * FROM users WHERE username = %s", (u,))
                else: cur.execute("SELECT * FROM users WHERE username = ?", (u,))
                r = cur.fetchone()
                if r and bcrypt.checkpw(p.encode('utf-8'), r['password'].encode('utf-8')):
                    return {"id": str(r['id']), "username": r['username']}
        except: pass
        return None

    def get_user(self, uid):
        try:
            with self._conn() as cn:
                cur = cn.cursor()
                if self.is_pg: cur.execute("SELECT id, username FROM users WHERE id = %s", (int(uid),))
                else: cur.execute("SELECT id, username FROM users WHERE id = ?", (int(uid),))
                r = cur.fetchone()
                return {"id": str(r['id']), "username": r['username']} if r else None
        except: return None

    def save_report(self, uid, rid, name, path):
        try:
            with self._conn() as cn:
                cur = cn.cursor()
                dt = datetime.now()
                if self.is_pg: cur.execute("INSERT INTO reports (user_id, report_id, name, date, path) VALUES (%s, %s, %s, %s, %s)", (int(uid), rid, name, dt, path))
                else: cur.execute("INSERT INTO reports (user_id, report_id, name, date, path) VALUES (?, ?, ?, ?, ?)", (int(uid), rid, name, dt, path))
                cn.commit()
        except Exception as e: print(f"❌ Save report error: {e}")

    def get_reports(self, uid):
        try:
            with self._conn() as cn:
                cur = cn.cursor()
                if self.is_pg: cur.execute("SELECT * FROM reports WHERE user_id = %s ORDER BY date DESC", (int(uid),))
                else: cur.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY date DESC", (int(uid),))
                return [{"report_id":r['report_id'], "subject_name":r['name'], "generated_at":str(r['date']), "report_path":r['path']} for r in cur.fetchall()]
        except: return []
