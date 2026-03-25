import os, json, uuid, threading, time, sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# Lazy-loaded instances
_db_instance = None
_pipeline_module = None

def get_db():
    global _db_instance
    if not _db_instance:
        from database import Database
        _db_instance = Database()
    return _db_instance

def get_pipeline():
    global _pipeline_module
    if not _pipeline_module:
        import inkognito_pipeline
        _pipeline_module = inkognito_pipeline
    return _pipeline_module

SESSIONS = {} # token -> uid
SESSIONS_LOCK = threading.Lock()
JOBS = {} # jid -> data
JOBS_LOCK = threading.Lock()

def _run_job(jid, subject_data, uid):
    try:
        with JOBS_LOCK: 
            JOBS[jid]["status"] = "running"
            JOBS[jid]["modules"] = [{"name": "Identity", "status": "running"}, {"name": "PublicRecords", "status": "queued"}]
        
        pipeline = get_pipeline()
        subj = pipeline.SubjectProfile(full_name=subject_data.get("name"), phone=subject_data.get("phone"), city=subject_data.get("city"))
        searcher = pipeline.SearchPipeline(subj)
        profile = searcher.run()
        
        report_id = jid
        path = f"reports/{report_id}.json"
        with open(ROOT / path, "w") as f: json.dump(profile.to_dict(), f)
        get_db().save_report(uid, report_id, subj.full_name, path)
        
        with JOBS_LOCK:
            JOBS[jid]["status"] = "completed"
            JOBS[jid]["report"] = profile.to_dict()
    except Exception as e:
        print(f"❌ Job {jid} failed: {e}")
        with JOBS_LOCK:
            JOBS[jid]["status"] = "failed"
            JOBS[jid]["error"] = str(e)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)

    def _send(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _user(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "): return None
        token = auth.split(" ")[1]
        with SESSIONS_LOCK: uid = SESSIONS.get(token)
        try: return get_db().get_user(uid) if uid else None
        except: return None

    def do_GET(self):
        p = self.path
        if p == "/api/ping": return self._send(200, {"status": "ok", "db": "lazy"})
        
        try:
            if p == "/api/user":
                u = self._user()
                return self._send(200, u) if u else self._send(401, {"err": "Unauthorized"})

            if p == "/api/reports":
                u = self._user()
                if not u: return self._send(401, {"err": "Unauthorized"})
                return self._send(200, get_db().get_reports(u["id"]))

            if p.startswith("/api/jobs/"):
                jid = p.split("/")[-1]
                if jid.startswith("report-"):
                    rid = jid.replace("report-", "")
                    with open(ROOT / f"reports/{rid}.json", "r") as f:
                        return self._send(200, {"status": "completed", "report": json.load(f)})
                with JOBS_LOCK:
                    j = JOBS.get(jid)
                    return self._send(200, j) if j else self._send(404, {"err": "Not found"})
        except Exception as e:
            return self._send(500, {"err": str(e)})
        
        if p in ["", "/"]: self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        p = self.path
        try:
            cl = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(cl).decode()) if cl else {}

            if p == "/api/register":
                uid = get_db().reg(body.get("username"), body.get("password"))
                return self._send(201, {"uid": uid}) if uid else self._send(400, {"err": "Taken"})

            if p == "/api/login":
                u = get_db().auth(body.get("username"), body.get("password"))
                if not u: return self._send(401, {"err": "Invalid"})
                token = uuid.uuid4().hex
                with SESSIONS_LOCK: SESSIONS[token] = u["id"]
                return self._send(200, {"token": token, "user": u})

            if p == "/api/run":
                u = self._user()
                if not u: return self._send(401, {"err": "Unauthorized"})
                jid = uuid.uuid4().hex[:12]
                with JOBS_LOCK: JOBS[jid] = {"status": "queued", "modules": []}
                threading.Thread(target=_run_job, args=(jid, body, u["id"]), daemon=True).start()
                return self._send(202, {"job_id": jid})
        except Exception as e:
            return self._send(500, {"err": str(e)})

        return self._send(404, {"err": "Not found"})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8080)))
    args = parser.parse_args()
    
    # Pre-check DB URL
    url = os.getenv("DATABASE_URL", "sqlite:///nk.db")
    print(f"🚀 Inkognito v2 starting on {args.host}:{args.port}")
    print(f"📦 DB Target: {'PostgreSQL' if 'postgre' in url else 'SQLite'}")
    
    try:
        httpd = HTTPServer((args.host, args.port), Handler)
        httpd.serve_forever()
    except Exception as e:
        print(f"🔥 Fatal Server Error: {e}")
        sys.exit(1)
