import os
from datetime import timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from server.db.session import engine, get_db, Base
from server.models import User, Report
from server.schemas import UserCreate, User as UserSchema, Token, RunPayload, JobStatus, ReportMetadata
from server.core.auth import (
    verify_password, get_password_hash, create_access_token, 
    SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
)
from server.services.pipeline_service import start_pipeline_job, get_job_status

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inkognito API v2", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

# --- Auth Dependencies ---

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# --- Routes ---

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/token", response_model=Token)
@app.post("/api/login", response_model=Token) # Alias for convenience
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/user", response_model=UserSchema)
def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/api/run", status_code=status.HTTP_202_ACCEPTED)
def run_verification(payload: RunPayload, current_user: User = Depends(get_current_user)):
    job_id = start_pipeline_job(payload.dict(), current_user.id)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}", response_model=JobStatus)
def read_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    job = get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/reports", response_model=List[ReportMetadata])
def read_user_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Report).filter(Report.user_id == current_user.id).order_by(Report.generated_at.desc()).all()

@app.get("/api/jobs/report-{report_id}")
def read_historical_report(report_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Support for old frontend hack / compatibility
    report = db.query(Report).filter(Report.report_id == report_id, Report.user_id == current_user.id).first()
    if not report:
         raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "job_id": f"report-{report_id}",
        "status": "completed",
        "report_id": report_id,
        "report": report.data,
        "modules": [],
        "elapsed_sec": 0
    }

# --- Static Files & SPA Routing ---

CLIENT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dist")

if os.path.exists(CLIENT_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(CLIENT_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API route not found")
        
        # Serve index.html for all other routes to support SPA
        index_file = os.path.join(CLIENT_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"detail": "Frontend not built. Run 'npm run build' in client directory."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
