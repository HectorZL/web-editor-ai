import os
from backend.app.core.config import settings

def diagnostic():
    project_name = "prueba3"
    storage_dir = os.path.abspath(os.path.join("backend", "..", "storage"))
    project_dir = os.path.join(storage_dir, project_name)
    
    print(f"Project Dir: {project_dir}")
    
    # 0. MUSIC DISCOVERY (Robust search logic mirroring orchestrator.py)
    music_path = None
    for m_dir in [os.path.join(project_dir, "audio"), project_dir]:
        if os.path.exists(m_dir):
            for ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
                for base in ["music", "background", "fondo", "background_audio"]:
                    test_p = os.path.join(m_dir, f"{base}{ext}")
                    if os.path.exists(test_p):
                        music_path = test_p
                        break
                if music_path: break
        if music_path: break
    
    voice_path = os.path.join(project_dir, "audio", "voice.mp3")
    if not os.path.exists(voice_path):
        voice_path = os.path.join(project_dir, "voice.mp3")

    print(f"- Voice Search: {voice_path} (Exists: {os.path.exists(voice_path)})")
    print(f"- Music Search Result: {music_path if music_path else 'NOT FOUND'}")
    
    if music_path and os.path.exists(voice_path):
        v_size = os.path.getsize(voice_path)
        m_size = os.path.getsize(music_path)
        print(f"  > Voice Size: {v_size} bytes")
        print(f"  > Music Size: {m_size} bytes")
        if v_size == m_size:
            print("  > WARNING: FILES ARE IDENTICAL BY SIZE. THIS IS THE PROBLEM.")
    
    # Check for other files in audio folder
    audio_dir = os.path.join(project_dir, "audio")
    if os.path.exists(audio_dir):
        print(f"\nFiles in {audio_dir}:")
        for f in os.listdir(audio_dir):
            print(f"  - {f} ({os.path.getsize(os.path.join(audio_dir, f))} bytes)")

if __name__ == "__main__":
    diagnostic()
