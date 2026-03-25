import os, json, uuid, threading, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from database import Database
from inkognito_pipeline import SubjectProfile, run_pipeline

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

_db_instance = None
def get_db():
    global _db_instance
    if not _db_instance: _db_instance = Database()
    return _db_instance

SESSIONS = {} # token -> uid
SESSIONS_LOCK = threading.Lock()
JOBS = {} # jid -> data
JOBS_LOCK = threading.Lock()

def _run_job(jid, subject, uid):
    try:
        with JOBS_LOCK: 
            JOBS[jid]["status"] = "running"
            JOBS[jid]["modules"] = [{"name": "Identity", "status": "running"}, {"name": "PublicRecords", "status": "queued"}]
        
        # Simulate / Run
        profile = run_pipeline(subject)
        
        # Save
        report_id = jid
        path = f"reports/{report_id}.json"
        with open(ROOT / path, "w") as f: json.dump(profile.to_dict(), f)
        get_db().save_report(uid, report_id, subject.full_name, path)
        
        with JOBS_LOCK:
            JOBS[jid]["status"] = "completed"
            JOBS[jid]["report"] = profile.to_dict()
    except Exception as e:
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
        return get_db().get_user(uid) if uid else None

    def do_GET(self):
        p = self.path
        if p == "/api/ping": return self._send(200, {"status": "ok"})
        
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
        
        if p in ["", "/"]: self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        p = self.path
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
            subj = SubjectProfile(full_name=body.get("name"), phone=body.get("phone"), city=body.get("city"))
            with JOBS_LOCK: JOBS[jid] = {"status": "queued", "modules": []}
            threading.Thread(target=_run_job, args=(jid, subj, u["id"]), daemon=True).start()
            return self._send(202, {"job_id": jid})

        return self._send(404, {"err": "Not found"})

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    print(f"🚀 Inkognito v2 starting on {args.host}:{args.port}")
    HTTPServer((args.host, args.port), Handler).serve_forever()
