import sys
import os
import json

# Setup paths to import from backend
sys.path.append(os.path.join(os.getcwd(), "backend"))

try:
    from backend.app.services.ai_service import ai_service
    from backend.app.core.config import settings
    
    project_name = "x"
    project_dir = os.path.join(settings.STORAGE_DIR, project_name)
    gameplay_path = os.path.join(project_dir, "gameplay.mp4")
    transcript_path = os.path.join(project_dir, "transcript.json")
    
    print(f"--- DIAGNOSTIC: Checking {project_name} ---")
    if not os.path.exists(transcript_path):
        print(f"ERROR: No transcript found at {transcript_path}")
        sys.exit(1)
        
    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = json.load(f)
        
    print(f"Loading CLIP and matching...")
    # Mocking scenes (just first 30s)
    scenes = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30)]
    
    def callback(p):
        print(f"Progress: {p}%")
        
    matches = ai_service.match_scenes_to_segments(scenes, transcript[:3], gameplay_path, progress_callback=callback)
    print(f"SUCCESS: Generated {len(matches)} matches.")
    
except Exception as e:
    print(f"FAIL: {str(e)}")
    import traceback
    traceback.print_exc()
