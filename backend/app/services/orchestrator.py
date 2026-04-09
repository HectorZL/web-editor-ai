import os
import uuid
import json
import numpy as np
from PIL import Image
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, vfx
from .ai_service import ai_service
from .video_engine import video_engine
from ..core.config import settings

def group_by_sentence(segments, target_duration=13.0):
    """Agrupa segmentos de Whisper en 'Párrafos' o bloques de 12-15s."""
    grouped = []
    if not segments: return grouped
    
    current_text = []
    current_start = segments[0]['start']
    
    for i, seg in enumerate(segments):
        text = seg['text'].strip()
        current_text.append(text)
        
        # Puntos finales o signos de exclamación/interrogación
        is_end = text.endswith(('.', '!', '?', '...'))
        
        # O una pausa de más de 0.6s entre palabras
        has_pause = False
        if i < len(segments) - 1:
            if segments[i+1]['start'] - seg['end'] > 0.6:
                has_pause = True
        
        # Nueva Duración si incluimos este segmento
        current_dur = seg['end'] - current_start
                
        # Solo cortamos si (es fin de frase O tiene pausa) Y llegamos al tiempo deseado (~13s)
        # O si es el último segmento del archivo
        if ( (is_end or has_pause) and current_dur >= target_duration ) or i == len(segments) - 1:
            grouped.append({
                "start": current_start,
                "end": seg['end'],
                "text": " ".join(current_text)
            })
            if i < len(segments) - 1:
                current_start = segments[i+1]['start']
                current_text = []
    return grouped

import re

HOOK_KEYWORDS = [
    "sabías que", "mira esto", "increíble", "truco", "secreto",
    "atención", "escucha", "detente", "lo que no te cuentan",
    "trucazo", "hack", "cómo puedes", "por qué", "nunca",
    "error", "cuidado", "lo que nadie te dice", "para qué sirve",
    "el mejor", "la mejor", "estás haciendo mal", "miren",
    "has visto", "quieres saber"
]

def _calculate_hook_score(text: str):
    """Calcula la potencia del gancho (Hook) para empezar un clip social."""
    score = 1.0
    text_lower = text.lower()
    
    # Bono por preguntas (EL MEJOR GANCHO)
    if "¿" in text or "?" in text:
        score += 3.0
    
    # Bono por palabras clave virales
    for kw in HOOK_KEYWORDS:
        if kw in text_lower:
            score += 2.0
            
    # Bono por frases cortas y directas (punchy)
    if len(text.split()) < 10:
        score += 0.5
        
    return score

def process_video_job(job_id: str, project_name: str, jobs_dict: dict):
    try:
        # PRIORIDAD DE RECURSOS: Dejar aire al sistema para que no se congele
        try:
            import psutil
            p = psutil.Process(os.getpid())
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS) 
        except Exception:
            pass

        # PATHS & PERSISTENCE
        project_dir = os.path.join(settings.STORAGE_DIR, project_name)
        
        # New structure vs Fallback (backward compatibility)
        gameplay_path = os.path.join(project_dir, "video", "gameplay.mp4")
        if not os.path.exists(gameplay_path):
            gameplay_path = os.path.join(project_dir, "gameplay.mp4")
            
        voice_path = os.path.join(project_dir, "audio", "voice.mp3")
        if not os.path.exists(voice_path):
            voice_path = os.path.join(project_dir, "voice.mp3")
            
        # 0. MUSIC DISCOVERY (Robust search across multiple extensions and locations)
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
        
        # LOG WARNING if files are identical
        if music_path and os.path.exists(voice_path):
            if os.path.getsize(music_path) == os.path.getsize(voice_path):
                print(f"--- [WARNING] Voice and Music files have identical size ({os.path.getsize(music_path)} bytes) ---")
        
        transcript_path = os.path.join(project_dir, "transcript.json")
        srt_path = os.path.join(project_dir, "transcript.srt")
        output_base = os.path.join(project_dir, "step_1_assembled.mp4")
        output_ducked = os.path.join(project_dir, "step_2_ducked.mp4")
        output_yt = os.path.join(project_dir, "final_youtube.mp4")
        output_tt_clean = os.path.join(project_dir, "step_4_vertical_clean.mp4")
        output_tiktok = os.path.join(project_dir, "final_tiktok_916.mp4")
        matches_path = os.path.join(project_dir, "matches.json")
        
        # LOGO DETECTION
        logo_path = None
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            potential_logo = os.path.join(project_dir, f"logo{ext}")
            if os.path.exists(potential_logo):
                logo_path = potential_logo
                break

        # 1. TRANSCRIPCIÓN (RESUMABLE)
        jobs_dict[job_id]["status"] = "PROCESSING"
        if os.path.exists(transcript_path):
            jobs_dict[job_id]["message"] = "Cargando transcripción existente..."
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript = json.load(f)
        else:
            jobs_dict[job_id]["message"] = "Fase 1: Transcribiendo audio (Medium Precision)..."
            jobs_dict[job_id]["progress"] = 10.0
            transcript = ai_service.transcribe(voice_path)
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript, f, indent=2)
            # Export SRT
            video_engine.export_srt(transcript, srt_path)
        
        # LIBERAR WHISPER antes de empezar con CLIP (Optimización VRAM)
        ai_service.unload_whisper()
        
        # 2. CLIP MATCHING & ASSEMBLY (INTELLIGENT MONTAJE)
        if not os.path.exists(output_base):
            # A. Detectar escenas con progreso en vivo
            jobs_dict[job_id]["message"] = "Fase 2A: Buscando cortes de cámara (Análisis Completo)..."
            def update_clip_progress(p):
                jobs_dict[job_id]["progress"] = round(p, 1)
                
            scenes = video_engine.detect_scenes(gameplay_path, progress_callback=update_clip_progress)
            
            # B. Si no hay suficientes escenas, forzar auto-split cada 5 segundos
            if len(scenes) < 3:
                print("--- Pocas escenas detectadas. Forzando auto-split dinámico ---")
                with VideoFileClip(gameplay_path) as v:
                    gameplay_dur = v.duration
                scenes = []
                for t in range(0, int(gameplay_dur), 3):
                    scenes.append((float(t), min(float(t+3), gameplay_dur)))
            
            # 0. Definir duracion total para fallback
            total_duration = transcript[-1]['end'] if transcript else 0

            # C. Matching Semántico (Voz vs Imagen) con feedback de progreso
            # AGRUPACIÓN POR SENTENCIAS: Agrupamos segmentos pequeños para que el video cambie por frases
            print(f"--- [MONTAJE] Agrupando {len(transcript)} segmentos en frases lógicas ---")
            grouped_transcript = {
                "segments": group_by_sentence(transcript)
            }
            print(f"--- [MONTAJE] Resultantes: {len(grouped_transcript['segments'])} frases para CLIP ---")

            jobs_dict[job_id]["message"] = "Fase 2B: Emparejando clips con el guion (CLIP)..."

            final_segments = grouped_transcript['segments']
            print(f"--- [DEBUG] Tipo de segments enviado a CLIP: {type(final_segments)} (Largo: {len(final_segments)}) ---")
            
            matches = ai_service.match_scenes_to_segments(
                scenes, final_segments, gameplay_path, 
                progress_callback=update_clip_progress
            )
            with open(matches_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2)
            
            # D. Descargar modelos para liberar VRAM (ahora sí)
            ai_service.unload_clip()
            
            # E. Ensamblado Real de clips
            jobs_dict[job_id]["message"] = "Fase 2: Ensamblando montaje inteligente..."
            video_engine.assemble_matched_video(gameplay_path, matches, voice_path, output_base)
        else:
            print("--- Saltando Ensamblado (Archivo ya existe) ---")
            ai_service.unload_models()

        # 3. AUDIO DUCKING (RESUMABLE)
        if not os.path.exists(output_ducked):
            jobs_dict[job_id]["message"] = "Fase 3: Mezclando música (Ducking active)..."
            jobs_dict[job_id]["progress"] = 50.0
            if music_path and os.path.exists(music_path):
                video_engine.apply_ducking(output_base, music_path, output_ducked)
            else:
                output_ducked = output_base
        else:
            print("--- Saltando Ducking (Archivo ya existe) ---")

        # 4. SUBTITULADO & EXPORTS
        # YouTube Style (Wide)
        if not os.path.exists(output_yt):
            jobs_dict[job_id]["message"] = "Fase 4: Generando versión horizontal (YT Style)..."
            jobs_dict[job_id]["progress"] = 70.0
            video_engine.burn_subtitles(output_ducked, transcript, output_yt, style="yt", logo_path=logo_path)
        
        # TikTok / Shorts Logic (Vertical First)
        if not os.path.exists(output_tiktok):
            jobs_dict[job_id]["message"] = "Fase 5: Generando versión vertical (9:16)..."
            jobs_dict[job_id]["progress"] = 90.0
            
            # Sub-paso A: Recortar a vertical sin subtítulos todavía
            if not os.path.exists(output_tt_clean):
                video_engine.export_vertical_916(output_ducked, output_tt_clean)
            
            # Sub-paso B: Quemar subtítulos sobre el video ya vertical
            video_engine.burn_subtitles(output_tt_clean, transcript, output_tiktok, style="tiktok", logo_path=logo_path)
        
        # 6. TOP 3 SOCIAL CLIPS (HIGH IMPACT)
        jobs_dict[job_id]["message"] = "Fase 6: Generando Top 3 Social Clips (Impacto Semántico)..."
        jobs_dict[job_id]["progress"] = 95.0
        
        if os.path.exists(matches_path):
            with open(matches_path, "r", encoding="utf-8") as f:
                matches = json.load(f)
            
            # 0. Obtener segmentos del transcript (ya es una lista)
            segments = transcript
            if not segments:
                print("--- [WARNING] No se encontraron segmentos en el transcript. Saltando clips sociales. ---")
                return

            # Algoritmo Semántico: Agrupar segmentos de transcript para evitar cortes a mitad de frase
            # Algoritmo Semántico: Agrupar segmentos de transcript para alcanzar el objetivo de ~60s
            target_clip_dur = 60
            max_search_dur = 70 # Buscamos un poco más para encontrar el mejor punto de corte
            best_windows = []
            
            # Buscaremos posibles inicios de clip en cada segmento
            for i, start_seg in enumerate(segments):
                start_t = start_seg['start']
                current_scores = []
                
                # Agregamos segmentos sucesivos
                subset = []
                best_end_t = start_t
                best_window_score = -1
                
                for j in range(i, len(segments)):
                    next_seg = segments[j]
                    current_dur = next_seg['end'] - start_t
                    
                    if current_dur > max_search_dur:
                        break
                    
                    subset.append(next_seg)
                    
                    # Buscamos el score de CLIP para este segmento
                    for m in matches:
                        if m['segment']['start'] == next_seg['start']:
                            current_scores.append(m['score'])
                            break
                    
                    # Solo evaluamos ventanas que duren al menos 30 segundos
                    if current_dur >= 30:
                        avg_clip_score = sum(current_scores) / len(current_scores) if current_scores else 0
                        hook_power = _calculate_hook_score(start_seg['text'])
                        
                        # Base Score: 40% Visión + 60% Gancho
                        semantic_score = (avg_clip_score * 0.4) + (hook_power * 0.6)
                        
                        # BONO POR DURACIÓN: Queremos que se acerque a 60s. 
                        # Penalizamos desviarse del objetivo de 60s.
                        duration_factor = 1.0 - (abs(target_clip_dur - current_dur) / target_clip_dur)
                        final_score = semantic_score * (0.7 + 0.3 * duration_factor)
                        
                        if final_score > best_window_score:
                            best_window_score = final_score
                            best_end_t = next_seg['end']

                if best_window_score > 0:
                    best_windows.append({"start": start_t, "end": best_end_t, "score": best_window_score, "duration": best_end_t - start_t})
            
            # Ordenar por puntuación y evitar solapamiento excesivo
            best_windows = sorted(best_windows, key=lambda x: x['score'], reverse=True)
            
            final_selection = []
            for win in best_windows:
                # Evitar que los clips se solapen demasiado (al menos 45s de diferencia en el inicio)
                if not any(abs(win['start'] - s['start']) < 45 for s in final_selection):
                    final_selection.append(win)
                if len(final_selection) >= 3: break
            
            if not final_selection:
                # Fallback si el video es muy corto
                final_selection = [{"start": 0, "end": total_duration, "score": 1.0}]

            for i, win in enumerate(final_selection):
                clip_name = f"social_clip_{i+1}.mp4"
                clip_path = os.path.join(project_dir, clip_name)
                if not os.path.exists(clip_path):
                    print(f"--- Exportando Social Clip {i+1} (Score: {win['score']:.2f}) ---")
                    video_engine.create_social_clip(
                        output_ducked, 
                        win['start'], 
                        win['end'], 
                        transcript, 
                        part_text=f"PARTE #{i+1}", 
                        cta_text="DALE LIKE Y SÍGUEME", 
                        output_path=clip_path,
                        logo_path=logo_path
                    )

        # FINAL
        jobs_dict[job_id]["status"] = "COMPLETED"
        jobs_dict[job_id]["progress"] = 100.0
        jobs_dict[job_id]["message"] = "¡Pipeline completado! Revisa la carpeta storage para ver tus 3 clips y el video largo."
        jobs_dict[job_id]["result_url"] = f"/storage/{project_name}/final_youtube.mp4"
        
    except Exception as e:
        jobs_dict[job_id]["status"] = "FAILED"
        jobs_dict[job_id]["message"] = f"Error en el Pipeline: {str(e)}"
        print(f"ERROR: {str(e)}")

def process_audio_job(job_id: str, project_name: str, jobs_dict: dict):
    try:
        project_dir = os.path.join(settings.STORAGE_DIR, project_name)
        
        voice_path = os.path.join(project_dir, "audio", "voice.mp3")
        if not os.path.exists(voice_path):
            voice_path = os.path.join(project_dir, "voice.mp3")
            
        # Robust music discovery
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

        output_audio = os.path.join(project_dir, "mixed_audio.mp3")

        jobs_dict[job_id]["status"] = "PROCESSING"
        jobs_dict[job_id]["message"] = "Fase 1: Preparando mezcla de audio..."
        jobs_dict[job_id]["progress"] = 25.0

        if not os.path.exists(voice_path):
            raise Exception("No se encontró el archivo de voz. Súbelo antes de procesar.")

        jobs_dict[job_id]["message"] = "Fase 2: Mezclando capas de sonido (Ducking)..."
        jobs_dict[job_id]["progress"] = 60.0
        
        # Mezclar usando el motor de video
        video_engine.mix_audio_ducking(voice_path, music_path, output_audio)

        jobs_dict[job_id]["status"] = "COMPLETED"
        jobs_dict[job_id]["progress"] = 100.0
        jobs_dict[job_id]["message"] = "¡Audio mezclado con éxito!"
        jobs_dict[job_id]["result_url"] = f"/storage/{project_name}/mixed_audio.mp3"
        
    except Exception as e:
        jobs_dict[job_id]["status"] = "FAILED"
        jobs_dict[job_id]["message"] = f"Error en mezcla de audio: {str(e)}"
        print(f"AUDIO_ERROR: {str(e)}")

def process_subtitles_job(job_id: str, project_name: str, jobs_dict: dict, language: str = "auto"):
    """Pipeline dedicado para quemar subtítulos rápidos en un video con limpieza de audio."""
    try:
        project_dir = os.path.join(settings.STORAGE_DIR, project_name)
        
        # Localización de video
        video_path = os.path.join(project_dir, "video", "gameplay.mp4")
        if not os.path.exists(video_path):
            video_path = os.path.join(project_dir, "gameplay.mp4")
            
        if not os.path.exists(video_path):
            raise Exception("No se encontró el video original para subtitular.")

        # Paths temporales y finales
        clean_audio_path = os.path.join(project_dir, "cleaned_audio_temp.wav")
        output_path = os.path.join(project_dir, "video_with_subs.mp4")
        
        jobs_dict[job_id]["status"] = "PROCESSING"
        jobs_dict[job_id]["message"] = "Fase 1: Extrayendo y limpiando audio (Denoising active)..."
        jobs_dict[job_id]["progress"] = 10.0

        # 1. Limpieza de Audio (FFT Denoise)
        video_engine.denoise_audio(video_path, clean_audio_path)

        # 2. Transcripción (Usamos el audio limpio)
        jobs_dict[job_id]["message"] = f"Fase 2: Analizando voz ({language.upper()}) con Whisper Medium..."
        jobs_dict[job_id]["progress"] = 30.0
        
        transcript = ai_service.transcribe(clean_audio_path, language=language)
        
        # Opcional: Eliminar audio temporal para ahorrar espacio
        if os.path.exists(clean_audio_path):
            try: os.remove(clean_audio_path)
            except: pass

        jobs_dict[job_id]["message"] = "Fase 3: Quemando subtítulos (White & Gray style)..."
        jobs_dict[job_id]["progress"] = 70.0

        # 3. Quemado de subtítulos con el nuevo estilo 'clean'
        # Pasamos el video original para la imagen
        video_engine.burn_subtitles(video_path, transcript, output_path, style="clean")

        jobs_dict[job_id]["status"] = "COMPLETED"
        jobs_dict[job_id]["progress"] = 100.0
        jobs_dict[job_id]["message"] = "¡Video subtitulado con éxito y audio filtrado!"
        jobs_dict[job_id]["result_url"] = f"/storage/{project_name}/video_with_subs.mp4"
        
    except Exception as e:
        jobs_dict[job_id]["status"] = "FAILED"
        jobs_dict[job_id]["message"] = f"Error en proceso de subtítulos: {str(e)}"
        print(f"SUBS_ERROR: {str(e)}")

video_engine = video_engine
