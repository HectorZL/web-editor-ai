from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class JobBase(BaseModel):
    project_name: str

class JobCreate(JobBase):
    pass

class JobStatus(BaseModel):
    id: str
    status: str # PENDING, PROCESSING, COMPLETED, FAILED
    progress: float
    message: str
    result_url: Optional[str] = None
    created_at: datetime

class ProjectInfo(BaseModel):
    name: str
    gameplay_path: Optional[str] = None
    audio_path: Optional[str] = None
    script: Optional[str] = None
    clips_count: int = 0

class SubtitleRequest(BaseModel):
    language: Optional[str] = "auto"
