import os
import shutil
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from ..core.config import settings
from ..schemas.job import JobStatus, ProjectInfo, SubtitleRequest
from ..services.orchestrator import process_video_job, process_audio_job, process_subtitles_job
from ..services.queue_manager import queue_manager

router = APIRouter()

# In-memory job store (replace with sqlite for persistence later)
jobs = {}

@router.post("/upload/gameplay/{project_name}")
async def upload_gameplay(project_name: str, file: UploadFile = File(...)):
    project_dir = os.path.join(settings.STORAGE_DIR, project_name, "video")
    os.makedirs(project_dir, exist_ok=True)
    
    file_path = os.path.join(project_dir, "gameplay.mp4")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "file_path": file_path}

@router.post("/upload/voice/{project_name}")
async def upload_voice(project_name: str, file: UploadFile = File(...)):
    project_dir = os.path.join(settings.STORAGE_DIR, project_name, "audio")
    os.makedirs(project_dir, exist_ok=True)
    
    file_path = os.path.join(project_dir, "voice.mp3")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "file_path": file_path}

@router.post("/upload/music/{project_name}")
async def upload_music(project_name: str, file: UploadFile = File(...)):
    project_dir = os.path.join(settings.STORAGE_DIR, project_name, "audio")
    os.makedirs(project_dir, exist_ok=True)
    
    file_path = os.path.join(project_dir, "music.mp3")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "file_path": file_path}

@router.post("/upload/logo/{project_name}")
async def upload_logo(project_name: str, file: UploadFile = File(...)):
    project_dir = os.path.join(settings.STORAGE_DIR, project_name)
    os.makedirs(project_dir, exist_ok=True)
    
    # We'll save it as logo.png (could be jpg/webp too but for FFmpeg we'll handle any)
    ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(project_dir, f"logo{ext}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"status": "success", "file_path": file_path}

@router.post("/process/{project_name}")
async def start_process(project_name: str):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "PENDING",
        "progress": 0.0,
        "message": "En cola...",
        "created_at": datetime.now()
    }
    
    # Añadir a la cola secuencial (Evita saturar VRAM)
    queue_manager.add_job(process_video_job, job_id, project_name, jobs)
    
    return {"job_id": job_id}

@router.post("/process-audio/{project_name}")
async def start_audio_process(project_name: str):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "PENDING",
        "progress": 0.0,
        "message": "En cola (Audio)...",
        "created_at": datetime.now()
    }
    
    queue_manager.add_job(process_audio_job, job_id, project_name, jobs)
    
    return {"job_id": job_id}

@router.post("/process-subtitles/{project_name}")
async def start_subtitles_process(project_name: str, request: SubtitleRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "PENDING",
        "progress": 0.0,
        "message": "En cola (Subtítulos)...",
        "created_at": datetime.now()
    }
    
    queue_manager.add_job(process_subtitles_job, job_id, project_name, jobs, language=request.language)
    
    return {"job_id": job_id}


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@router.get("/queue/stats")
async def get_queue_stats():
    """Devuelve estadísticas de la cola: procesados, activo y pendientes."""
    active_info = None
    
    if queue_manager.active_job:
        job_id = queue_manager.active_job["job_id"]
        # Obtener progreso real desde el diccionario de trabajos
        job_details = jobs.get(job_id, {})
        active_info = {
            **queue_manager.active_job,
            "progress": job_details.get("progress", 0.0),
            "status": job_details.get("status", "PROCESSING"),
            "message": job_details.get("message", "")
        }

    return {
        "total_processed": queue_manager.processed_count,
        "queued_count": queue_manager.job_queue.qsize(),
        "currently_processing": active_info
    }
