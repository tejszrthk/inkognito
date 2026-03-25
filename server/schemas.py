import datetime
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

# --- Auth ---

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- Pipeline ---

class RunPayload(BaseModel):
    name: str
    phone: str
    city: str
    employer: Optional[str] = ""
    business: Optional[str] = ""
    financeRole: Optional[bool] = False
    socialUrls: Optional[str] = ""

class ModuleStatus(BaseModel):
    id: str
    name: str
    status: str
    skipReason: Optional[str] = ""
    error: Optional[str] = ""
    findingsCount: int = 0
    durationSec: float = 0.0

class JobStatus(BaseModel):
    job_id: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_sec: float = 0.0
    modules: List[ModuleStatus] = []
    current_module: Optional[str] = ""
    report_id: Optional[str] = ""
    report_path: Optional[str] = ""
    report: Optional[dict] = None
    error: Optional[str] = ""

# --- Reports ---

class ReportMetadata(BaseModel):
    report_id: str
    subject_name: str
    generated_at: datetime.datetime
    report_path: str

    class Config:
        from_attributes = True
