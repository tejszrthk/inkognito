import threading
import uuid
import time
import os
from datetime import datetime
from pathlib import Path
from inkognito_models import SubjectProfile
from inkognito_pipeline import SearchPipeline, save_report
from server.db.session import SessionLocal
from server.models import Report

# Global job store (in-memory progress tracking)
JOBS = {}
JOBS_LOCK = threading.Lock()

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def _now_iso():
    return datetime.now().isoformat()

def _build_subject(payload: dict) -> SubjectProfile:
    # Helper to parse social URLs if provided as string
    social_urls = payload.get("socialUrls", "").strip()
    social = {"linkedin": None, "instagram": None, "facebook": None}
    
    if social_urls:
        chunks = [x.strip() for x in social_urls.split(",") if x.strip()]
        for chunk in chunks:
            lowered = chunk.lower()
            if "linkedin.com/" in lowered: social["linkedin"] = chunk
            elif "instagram.com/" in lowered: 
                path = chunk.split("instagram.com/")[-1].strip("/")
                if path: social["instagram"] = path.split("/")[0].lstrip("@")
            elif "facebook.com/" in lowered:
                path = chunk.split("facebook.com/")[-1].strip("/")
                if path: social["facebook"] = path.split("/")[0]

    subject = SubjectProfile(
        full_name=payload["name"],
        current_city=payload["city"],
        mobile=payload.get("phone"),
        employer_name=payload.get("employer") or None,
        business_name=payload.get("business") or None,
        company_name=payload.get("business") or None,
        linkedin_url=social["linkedin"],
        instagram_username=social["instagram"],
        facebook_profile_id=social["facebook"],
    )
    
    if payload.get("financeRole"):
        setattr(subject, "claims_finance_role", True)
        
    return subject

def _run_job_thread(job_id: str, subject: SubjectProfile, user_id: int):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "running"
        job["started_at"] = _now_iso()
        job["started_monotonic"] = time.monotonic()

    pipeline = SearchPipeline(subject)
    module_names = [m[0] for m in SearchPipeline.module_registry()]
    
    def on_module_start(module_name: str, _idx, _total):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if not j: return
            for mod in j["modules"]:
                if mod["name"] == module_name:
                    mod["status"] = "running"
                    break
            j["current_module"] = module_name

    def on_module_complete(module_name: str, result, _idx, _total):
        with JOBS_LOCK:
            j = JOBS.get(job_id)
            if not j: return
            for mod in j["modules"]:
                if mod["name"] == module_name:
                    mod["status"] = "skipped" if result.skipped else ("complete" if result.success else "failed")
                    mod["skipReason"] = result.skip_reason or ""
                    mod["error"] = result.error or ""
                    mod["findingsCount"] = len(result.findings)
                    mod["durationSec"] = round(result.duration_sec, 2)
                    break

    try:
        report = pipeline.run(on_module_start=on_module_start, on_module_complete=on_module_complete)
        reports_dir = ROOT_DIR / "reports"
        reports_dir.mkdir(exist_ok=True)
        report_path = save_report(report, output_dir=str(reports_dir))

        # Update DB
        db = SessionLocal()
        try:
            db_report = Report(
                report_id=report.report_id,
                user_id=user_id,
                subject_name=report.subject.full_name,
                generated_at=datetime.utcnow(),
                report_path=report_path,
                data=report.to_dict()
            )
            db.add(db_report)
            db.commit()
        finally:
            db.close()

        with JOBS_LOCK:
            j = JOBS[job_id]
            j["status"] = "completed"
            j["finished_at"] = _now_iso()
            j["report_id"] = report.report_id
            j["report_path"] = report_path
            j["report"] = report.to_dict()
            j["current_module"] = ""

    except Exception as e:
        with JOBS_LOCK:
            j = JOBS[job_id]
            j["status"] = "failed"
            j["error"] = str(e)
            j["current_module"] = ""

def start_pipeline_job(payload: dict, user_id: int) -> str:
    job_id = uuid.uuid4().hex[:12]
    subject = _build_subject(payload)
    
    modules = []
    for name, _ in SearchPipeline.module_registry():
        modules.append({
            "id": name.lower().replace(" ", "-"),
            "name": name,
            "status": "queued",
            "skipReason": "",
            "error": "",
            "findingsCount": 0,
            "durationSec": 0.0
        })

    with JOBS_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "created_at": _now_iso(),
            "started_at": None,
            "finished_at": None,
            "started_monotonic": None,
            "modules": modules,
            "current_module": "",
            "report_id": "",
            "report_path": "",
            "report": None,
            "error": ""
        }

    thread = threading.Thread(target=_run_job_thread, args=(job_id, subject, user_id), daemon=True)
    thread.start()
    return job_id

def get_job_status(job_id: str) -> dict:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job: return None
        
        # Calculate elapsed
        elapsed = 0.0
        if job["started_monotonic"]:
            end = time.monotonic() if job["status"] not in ["completed", "failed"] else (time.monotonic() if not job.get("finished_monotonic") else job["finished_monotonic"])
            elapsed = round(max(0.0, end - job["started_monotonic"]), 2)
            
        return {**job, "elapsed_sec": elapsed}
