#!/usr/bin/env python3
import argparse
import json
import os
import threading
import time
import uuid
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from inkognito_models import SubjectProfile
from inkognito_pipeline import SearchPipeline, save_report
from database import Database

# --- Configuration ---
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
REPORTS_DIR = ROOT_DIR / "reports"
# Reports folder
REPORTS_DIR.mkdir(exist_ok=True)

_DB = None
def get_db():
    global _DB
    if _DB is None:
        _DB = Database()
    return _DB

SESSIONS: dict[str, str] = {} # token -> user_id (string)
SESSIONS_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

# --- Helpers ---
def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _build_subject(payload: dict) -> SubjectProfile:
    name = str(payload.get("name", "")).strip()
    city = str(payload.get("city", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    employer = str(payload.get("employer", "")).strip()
    business = str(payload.get("business", "")).strip()
    finance_role = bool(payload.get("financeRole", False))
    social_urls = str(payload.get("socialUrls", "")).strip()

    if not name or not city or not phone:
        raise ValueError("Name, City, and Phone are required for identity verification.")

    subject = SubjectProfile(
        full_name=name,
        current_city=city,
        mobile=phone,
        employer_name=employer or None,
        business_name=business or None,
        company_name=business or None,
    )
    if finance_role:
        setattr(subject, "claims_finance_role", True)
    
    # Simple social parsing
    if social_urls:
        for url in [u.strip() for u in social_urls.split(",")]:
            if "linkedin.com" in url: subject.linkedin_url = url
            elif "instagram.com" in url: subject.instagram_username = url.split("/")[-1]
            elif "facebook.com" in url: subject.facebook_profile_id = url.split("/")[-1]

    return subject

# --- Background Worker ---
def _run_job(job_id: str, subject: SubjectProfile, user_id: str):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = _now_iso()
        job["started_monotonic"] = time.monotonic()

    pipeline = SearchPipeline(subject)
    
    def on_module_start(name, idx, total):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if j: j["current_module"] = name

    def on_module_complete(name, result, idx, total):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if not j: return
            mod = next((m for m in j["modules"] if m["name"] == name), None)
            if mod:
                mod.update({
                    "status": "complete" if result.success else ("skipped" if result.skipped else "failed"),
                    "findingsCount": len(result.findings),
                    "durationSec": round(result.duration_sec, 2),
                    "error": result.error or "",
                    "skipReason": result.skip_reason or ""
                })

    try:
        report = pipeline.run(on_module_start=on_module_start, on_module_complete=on_module_complete)
        report_path = save_report(report, output_dir=str(REPORTS_DIR))
        
        get_db().save_report_metadata(
            user_id=user_id,
            report_id=report.report_id,
            subject_name=report.subject.full_name,
            generated_at=report.generated_at,
            report_path=report_path
        )

        with JOBS_LOCK:
            job = JOBS[job_id]
            job.update({
                "status": "completed",
                "finished_at": _now_iso(),
                "report_id": report.report_id,
                "report": report.to_dict()
            })
    except Exception as e:
        with JOBS_LOCK:
            if job_id in JOBS:
                JOBS[job_id].update({"status": "failed", "error": str(e)})

# --- Request Handler ---
class InkognitoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def _send_json(self, status: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def _get_user(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "): return None
        token = auth.split(" ")[1]
        with SESSIONS_LOCK:
            uid = SESSIONS.get(token)
        return get_db().get_user_by_id(uid) if uid else None

    def do_OPTIONS(self):
        self._send_json(204, {})

    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == "/api/register":
            data = self._read_json()
            uid = get_db().register_user(data.get("username"), data.get("password"))
            if uid: self._send_json(201, {"message": "Registered"})
            else: self._send_json(400, {"error": "Username taken"})
            return

        if path == "/api/login":
            data = self._read_json()
            user = get_db().authenticate_user(data.get("username"), data.get("password"))
            if user:
                token = uuid.uuid4().hex
                with SESSIONS_LOCK: SESSIONS[token] = user["id"]
                self._send_json(200, {"token": token, "user": user})
            else: self._send_json(401, {"error": "Invalid credentials"})
            return

        if path == "/api/run":
            user = self._get_user()
            if not user: return self._send_json(401, {"error": "Auth required"})
            
            try:
                subject = _build_subject(self._read_json())
            except ValueError as e: return self._send_json(400, {"error": str(e)})

            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "job_id": job_id, "status": "queued", "created_at": _now_iso(),
                    "modules": [{"name": n, "status": "queued"} for n, _ in SearchPipeline.module_registry()]
                }
            
            threading.Thread(target=_run_job, args=(job_id, subject, user["id"]), daemon=True).start()
            self._send_json(202, {"job_id": job_id})
            return

        self._send_json(404, {"error": "Not found"})

    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == "/api/ping":
            self._send_json(200, {"status": "alive", "db": "connected" if get_db().db else "disconnected"})
            return

        if path == "/api/user":
            user = self._get_user()
            if user: self._send_json(200, user)
            else: self._send_json(401, {"error": "Auth required"})
            return

        if path == "/api/reports":
            user = self._get_user()
            if not user: return self._send_json(401, {"error": "Auth required"})
            self._send_json(200, get_db().get_user_reports(user["id"]))
            return

        if path.startswith("/api/jobs/"):
            jid = path.split("/")[-1]
            if jid.startswith("report-"):
                # Historical report lookup
                rid = jid.replace("report-", "")
                user = self._get_user()
                if not user: return self._send_json(401, {"error": "Auth required"})
                
                # Find report in DB
                report_meta = next((r for r in get_db().get_user_reports(user["id"]) if r["report_id"] == rid), None)
                if report_meta and os.path.exists(report_meta["report_path"]):
                    with open(report_meta["report_path"], "r") as f:
                        self._send_json(200, {"status": "completed", "report": json.load(f)})
                    return
                return self._send_json(404, {"error": "Report not found"})

            with JOBS_LOCK:
                job = JOBS.get(jid)
            if job:
                # Calculate elapsed time for live jobs
                elapsed = 0
                if job.get("started_monotonic"):
                    elapsed = time.monotonic() - job["started_monotonic"]
                self._send_json(200, {**job, "elapsed_sec": round(elapsed, 2)})
            else: self._send_json(404, {"error": "Job not found"})
            return

        if path in ["", "/"]: self.path = "/index.html"
        return super().do_GET()

# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)))
    args = parser.parse_args()
    
    server = ThreadingHTTPServer((args.host, args.port), InkognitoHandler)
    print(f"🚀 Inkognito v1 (Refactored) listening on http://{args.host}:{args.port}")
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
