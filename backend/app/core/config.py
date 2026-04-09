import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "VideoFlow AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    STORAGE_DIR: str = os.path.join(BASE_DIR, "..", "storage")
    
    # AI Constraints (6GB VRAM)
    WHISPER_MODEL: str = "medium" # or 'medium' for higher precision
    WHISPER_COMPUTE_TYPE: str = "int8_float16" # Optimizado para GPU
    CLIP_MODEL_NAME: str = "clip-ViT-B-32"
    
    class Config:
        case_sensitive = True

settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
