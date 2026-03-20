#!/usr/bin/env python3
"""
Inkognito API server.

Serves the frontend and exposes a small JSON API:
  POST /api/run         -> starts a background pipeline job
  GET  /api/jobs/<id>   -> returns live job status + module progress
  GET  /api/health      -> health check

Run:
  python api_server.py --host 127.0.0.1 --port 8000
"""

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

from inkognito_models import SubjectProfile
from inkognito_pipeline import SearchPipeline, save_report
from database import Database

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"

DB = Database()
SESSIONS: dict[str, int] = {}  # token -> user_id
SESSIONS_LOCK = threading.Lock()

MODULE_ID_BY_NAME = {
    "eCourts": "ecourts",
    "MCA21": "mca21",
    "GST": "gst",
    "Google Search": "google",
    "Property Records": "property",
    "Social Media": "social",
    "Reverse Image Search": "image",
    "Phone Intelligence": "phone",
    "Matrimonial Cross-check": "matrimonial",
    "NCDRC": "ncdrc",
    "NCLT": "nclt",
    "SEBI": "sebi",
    "EPFO": "epfo",
}

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _parse_social_urls(raw_urls: str) -> dict:
    parsed = {
        "linkedin_url": None,
        "instagram_username": None,
        "facebook_profile_id": None,
    }

    if not raw_urls:
        return parsed

    chunks = [x.strip() for x in raw_urls.split(",") if x.strip()]
    for chunk in chunks:
        lowered = chunk.lower()

        if "linkedin.com/" in lowered and not parsed["linkedin_url"]:
            parsed["linkedin_url"] = chunk
            continue

        if "instagram.com/" in lowered and not parsed["instagram_username"]:
            # Best-effort username extraction from URL path.
            path = chunk.split("instagram.com/")[-1].strip("/")
            if path:
                parsed["instagram_username"] = path.split("/")[0].lstrip("@")
            continue

        if "facebook.com/" in lowered and not parsed["facebook_profile_id"]:
            path = chunk.split("facebook.com/")[-1].strip("/")
            if path:
                parsed["facebook_profile_id"] = path.split("/")[0]
            continue

    return parsed


def _build_subject(payload: dict) -> SubjectProfile:
    name = str(payload.get("name", "")).strip()
    city = str(payload.get("city", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    employer = str(payload.get("employer", "")).strip()
    business = str(payload.get("business", "")).strip()
    finance_role = bool(payload.get("financeRole", False))
    social_urls = str(payload.get("socialUrls", "")).strip()

    if not name:
        raise ValueError("name is required")
    if not city:
        raise ValueError("city is required")

    social = _parse_social_urls(social_urls)

    subject = SubjectProfile(
        full_name=name,
        current_city=city,
        mobile=phone or None,
        employer_name=employer or None,
        business_name=business or None,
        company_name=business or None,
        linkedin_url=social["linkedin_url"],
        instagram_username=social["instagram_username"],
        facebook_profile_id=social["facebook_profile_id"],
    )

    # Optional flag respected by SubjectProfile.has_finance_role().
    if finance_role:
        setattr(subject, "claims_finance_role", True)

    return subject


def _initial_modules() -> list[dict]:
    modules = []
    for module_name, _ in SearchPipeline.module_registry():
        modules.append(
            {
                "id": MODULE_ID_BY_NAME.get(module_name, module_name.lower()),
                "name": module_name,
                "status": "queued",
                "skipReason": "",
                "error": "",
                "findingsCount": 0,
                "durationSec": 0.0,
            }
        )
    return modules


def _elapsed_seconds(job: dict) -> float:
    started_at = job.get("started_monotonic")
    if started_at is None:
        return 0.0

    finished_at = job.get("finished_monotonic")
    end = finished_at if finished_at is not None else time.monotonic()
    return max(0.0, end - started_at)


def _job_payload(job: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "elapsed_sec": round(_elapsed_seconds(job), 2),
        "modules": job["modules"],
        "current_module": job.get("current_module", ""),
        "report_id": job.get("report_id", ""),
        "report_path": job.get("report_path", ""),
        "report": job.get("report"),
        "error": job.get("error", ""),
    }


def _run_job(job_id: str, subject: SubjectProfile, user_id: int):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = _now_iso()
        job["started_monotonic"] = time.monotonic()

    pipeline = SearchPipeline(subject)

    module_index = {m["name"]: i for i, m in enumerate(JOBS[job_id]["modules"])}

    def on_module_start(module_name: str, _idx: int, _total: int):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if not j:
                return
            i = module_index.get(module_name)
            if i is None:
                return
            j["modules"][i]["status"] = "running"
            j["current_module"] = module_name

    def on_module_complete(module_name: str, module_result, _idx: int, _total: int):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if not j:
                return
            i = module_index.get(module_name)
            if i is None:
                return

            if module_result.skipped:
                status = "skipped"
            elif module_result.success:
                status = "complete"
            else:
                status = "failed"

            j["modules"][i].update(
                {
                    "status": status,
                    "skipReason": module_result.skip_reason or "",
                    "error": module_result.error or "",
                    "findingsCount": len(module_result.findings),
                    "durationSec": round(module_result.duration_sec, 2),
                }
            )

    try:
        report = pipeline.run(
            on_module_start=on_module_start,
            on_module_complete=on_module_complete,
        )
        report_path = save_report(report, output_dir=str(ROOT_DIR / "reports"))

        # Save to database
        DB.save_report_metadata(
            user_id=user_id,
            report_id=report.report_id,
            subject_name=report.subject.full_name,
            generated_at=report.generated_at,
            report_path=report_path,
        )

        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "completed"
            job["finished_at"] = _now_iso()
            job["finished_monotonic"] = time.monotonic()
            job["report_id"] = report.report_id
            job["report_path"] = report_path
            job["report"] = report.to_dict()
            job["current_module"] = ""

    except Exception as exc:
        with JOBS_LOCK:
            job = JOBS[job_id]
            job["status"] = "failed"
            job["finished_at"] = _now_iso()
            job["finished_monotonic"] = time.monotonic()
            job["error"] = str(exc)
            job["current_module"] = ""


class InkognitoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, fmt, *args):
        # Keep server logs concise.
        print("[api]" + fmt % args)

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _get_auth_user(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ", 1)[1]
        with SESSIONS_LOCK:
            user_id = SESSIONS.get(token)
        if user_id:
            return DB.get_user_by_id(user_id)
        return None

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/register":
            payload = self._read_json_body()
            username = payload.get("username")
            password = payload.get("password")
            if not username or not password:
                self._send_json(400, {"error": "Username and password required"})
                return
            user_id = DB.register_user(username, password)
            if user_id:
                self._send_json(201, {"message": "User registered successfully"})
            else:
                self._send_json(409, {"error": "Username already exists"})
            return

        if parsed.path == "/api/login":
            payload = self._read_json_body()
            username = payload.get("username")
            password = payload.get("password")
            user = DB.authenticate_user(username, password)
            if user:
                token = uuid.uuid4().hex
                with SESSIONS_LOCK:
                    SESSIONS[token] = user["id"]
                self._send_json(200, {"token": token, "user": user})
            else:
                self._send_json(401, {"error": "Invalid credentials"})
            return

        if parsed.path == "/api/logout":
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                with SESSIONS_LOCK:
                    SESSIONS.pop(token, None)
            self._send_json(200, {"message": "Logged out"})
            return

        if parsed.path == "/api/run":
            user = self._get_auth_user()
            if not user:
                self._send_json(401, {"error": "Authentication required"})
                return

            try:
                payload = self._read_json_body()
                subject = _build_subject(payload)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send_json(400, {"error": str(exc)})
                return

            job_id = uuid.uuid4().hex[:12]
            modules = _initial_modules()

            with JOBS_LOCK:
                JOBS[job_id] = {
                    "job_id": job_id,
                    "status": "queued",
                    "created_at": _now_iso(),
                    "started_at": None,
                    "finished_at": None,
                    "started_monotonic": None,
                    "finished_monotonic": None,
                    "current_module": "",
                    "modules": modules,
                    "report_id": "",
                    "report_path": "",
                    "report": None,
                    "error": "",
                }

            worker = threading.Thread(
                target=_run_job,
                args=(job_id, subject, user["id"]),
                daemon=True,
            )
            worker.start()

            self._send_json(
                202,
                {
                    "job_id": job_id,
                    "status": "queued",
                    "modules": modules,
                },
            )
            return

        self._send_json(404, {"error": "Unknown endpoint"})

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            self._send_json(200, {"status": "ok", "time": _now_iso()})
            return

        if parsed.path == "/api/user":
            user = self._get_auth_user()
            if user:
                self._send_json(200, user)
            else:
                self._send_json(401, {"error": "Authentication required"})
            return

        if parsed.path == "/api/reports":
            user = self._get_auth_user()
            if not user:
                self._send_json(401, {"error": "Authentication required"})
                return
            reports = DB.get_user_reports(user["id"])
            self._send_json(200, reports)
            return

        if parsed.path.startswith("/api/jobs/"):
            job_id = parsed.path.rsplit("/", 1)[-1].strip()
            
            # Special case for historical reports: /api/jobs/report-<id>
            if job_id.startswith("report-"):
                report_id = job_id[7:]
                user = self._get_auth_user()
                user_id = user["id"] if user else None
                
                if not user_id:
                    self._send_json(401, {"error": "Authentication required"})
                    return
                
                # Check database for this report
                with DB._get_connection() as conn:
                    row = conn.execute(
                        "SELECT report_path, subject_name FROM reports WHERE report_id = ? AND user_id = ?",
                        (report_id, user_id)
                    ).fetchone()
                
                if row and os.path.exists(row["report_path"]):
                    with open(row["report_path"], "r") as f:
                        report_json = json.load(f)
                    self._send_json(200, {
                        "job_id": job_id,
                        "status": "completed",
                        "report_id": report_id,
                        "report": report_json,
                        "modules": [], # Modules detail not needed for historical view
                        "elapsed_sec": 0
                    })
                    return
                else:
                    self._send_json(404, {"error": "Report not found or access denied"})
                    return

            with JOBS_LOCK:
                job = JOBS.get(job_id)
                payload = _job_payload(job) if job else None
            if payload is None:
                self._send_json(404, {"error": "Job not found"})
            else:
                self._send_json(200, payload)
            return

        # Static frontend serving
        if parsed.path in ("", "/"):
            self.path = "/index.html"
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(description="Inkognito API server")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)))
    args = parser.parse_args()

    if not FRONTEND_DIR.exists():
        raise SystemExit(f"frontend directory not found: {FRONTEND_DIR}")

    server = ThreadingHTTPServer((args.host, args.port), InkognitoHandler)
    print(f"Inkognito server listening at http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
