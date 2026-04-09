import os
import uuid
from typing import List
from scenedetect import detect, ContentDetector
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, vfx, TextClip, CompositeVideoClip, ColorClip
from ..core.config import settings

class VideoEngine:
    @staticmethod
    def detect_scenes(video_path: str, progress_callback=None):
        """Detecta cortes de escena en TODO el video con PROGRESO EN VIVO."""
        import subprocess
        import re
        import time
        from moviepy import VideoFileClip
        
        start_time = time.time()
        print(f"--- [FFMPEG SCENE] Iniciando Análisis Completo: {os.path.basename(video_path)}... ---")
        
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"
            
        # 0. Obtener duración real para la barra de progreso
        with VideoFileClip(video_path) as v:
            real_duration = v.duration
            
        # 1. Comando: Análisis a 10 FPS para mayor precisión
        cmd = [
            ffmpeg_exe, "-ss", "00:00:00", "-i", video_path,
            "-vf", "fps=10,select='gt(scene,0.25)',showinfo",
            "-f", "null", "-"
        ]
        
        # 2. Ejecución con Lectura en Vivo (Popen)
        process = subprocess.Popen(
            cmd, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding="utf-8", 
            universal_newlines=True,
            bufsize=1
        )
        
        timestamps = [0.0]
        last_log_t = 0
        
        # Leer línea por línea mientras FFmpeg trabaja
        while True:
            line = process.stderr.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                # Extraemos pts_time del log de info
                pts_search = re.search(r"pts_time:([\d.]+)", line)
                if pts_search:
                    pts = float(pts_search.group(1))
                    
                    # Guardar timestamp si es un cambio de escena real
                    if "n:" in line and "pts:" in line: # Filtro de FFmpeg confirmando frame
                        if pts > timestamps[-1] + 1.0:
                            timestamps.append(pts)
                    
                    # Actualizar progreso cada ~2 segundos para no saturar la consola
                    if time.time() - last_log_t > 2.0:
                        percent = (pts / real_duration) * 100 if real_duration > 0 else 0
                        print(f"[{percent:4.1f}%] Analizando segundo {int(pts)} de {int(real_duration)}...")
                        if progress_callback:
                            progress_callback(20.0 + (percent / 100) * 10.0)
                        last_log_t = time.time()

        # 3. Finalizar
        if timestamps[-1] < real_duration:
            timestamps.append(real_duration)
            
        scenes = []
        for i in range(len(timestamps) - 1):
            start, end = timestamps[i], timestamps[i+1]
            # --- [VARIETY FIX] --- 
            # Si la escena es muy larga (partida larga sin cortes), la dividimos 
            # artificialmente en bloques de 6s para que CLIP tenga varios 'snapshots' 
            # y no repita siempre el inicio del mismo clip.
            dur = end - start
            if dur > 12.0:
                num_splits = int(dur // 6)
                split_dur = dur / num_splits
                for s in range(num_splits):
                    scenes.append((start + s * split_dur, start + (s + 1) * split_dur))
            else:
                scenes.append((start, end))
            
        duration = time.time() - start_time
        print(f"--- [DONE] {len(scenes)} escenas (con sub-splits) encontradas en {duration:.1f}s. ---")
        return scenes


    @staticmethod
    def extract_clip(video_path: str, start: float, end: float, output_path: str):
        with VideoFileClip(video_path) as video:
            clip = video.subclipped(start, end)
            clip.write_videofile(output_path, codec="h264_nvenc", audio_codec="aac", threads=6, preset="p1")

    @staticmethod
    def _get_ffmpeg_exe():
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            return "ffmpeg"

    @staticmethod
    def mix_audio_ducking(voice_path: str, music_path: str, output_path: str):
        """Mezcla voz y música (Audio-Only) con sidechain compression profesional."""
        import subprocess
        import os
        ffmpeg_exe = VideoEngine._get_ffmpeg_exe()
        
        # Sanitizar rutas
        voice_path = os.path.abspath(voice_path)
        music_path = os.path.abspath(music_path)
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"--- Mezclando Audio (Sidechain Compression) -> {output_path} ---")
        
        if not music_path or not os.path.exists(music_path):
            cmd = [ffmpeg_exe, "-y", "-i", voice_path, "-af", "volume=1.5", output_path]
        else:
            # VITAL: En FFmpeg, si usas una etiqueta [v], se "consume". 
            # Para usar la voz como 'sidechain' Y además escucharla en el mix, hay que usar 'asplit'.
            # [0:a] (voz) -> asplit=2 -> [v1] (para sidechain) y [v2] (para mix final)
            filter_str = (
                "[0:a]volume=1.5,aresample=async=1,asplit=2[v1][v2];"
                "[1:a]volume=0.15,aresample=async=1[m];"
                "[m][v1]sidechaincompress=threshold=0.15:ratio=4:attack=5:release=200[m_d];"
                "[v2][m_d]amix=inputs=2:duration=first:dropout_transition=0[outa]"
            )
            cmd = [
                ffmpeg_exe, "-y",
                "-i", voice_path, "-i", music_path,
                "-filter_complex", filter_str,
                "-map", "[outa]",
                "-c:a", "libmp3lame" if output_path.endswith(".mp3") else "aac",
                "-b:a", "192k",
                output_path
            ]
            
        subprocess.run(cmd, check=True, capture_output=True)

    @staticmethod
    def apply_ducking(video_path: str, music_path: str, output_path: str):
        """Aplica ducking dinámico profesional al montar música sobre vídeo."""
        import subprocess
        import os
        ffmpeg_exe = VideoEngine._get_ffmpeg_exe()
        
        # Sanitizar rutas
        video_path = os.path.abspath(video_path)
        music_path = os.path.abspath(music_path)
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"--- Aplicando Ducking Pro (Sidechain) -> {output_path} ---")
        
        # Aplicamos asplit=2 para usar la voz de video [0:a] como sidechain Y para el mix
        filter_str = (
            "[0:a]volume=1.5,aresample=async=1,asplit=2[v1][v2];"
            "[1:a]volume=0.15,aresample=async=1[m];"
            "[m][v1]sidechaincompress=threshold=0.15:ratio=4:attack=5:release=200[m_d];"
            "[v2][m_d]amix=inputs=2:duration=first:dropout_transition=0[outa]"
        )
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path, "-i", music_path,
            "-filter_complex", filter_str,
            "-map", "0:v", "-map", "[outa]",
            "-c:v", "copy", # Mantener video original (Ultra rápido)
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"--- [DONE] Ducking Pro completado en {os.path.basename(output_path)} ---")

    @staticmethod
    def denoise_audio(video_path: str, output_audio: str):
        """Extrae el audio y aplica reducción de ruido FFT para mejorar la transcripción."""
        import subprocess
        import os
        ffmpeg_exe = VideoEngine._get_ffmpeg_exe()
        
        print(f"--- [CLEANING] Reduciendo ruido de fondo -> {os.path.basename(output_audio)} ---")
        
        # Filtro: afftdn (FFT-based Noise Reduction) + highpass para limpiar frecuencias bajas de fondo
        # nr=12: reducción de 12dB (seguro para no distorsionar voz)
        filter_str = "afftdn=nr=12,highpass=f=100,lowpass=f=8000"
        
        cmd = [
            ffmpeg_exe, "-y",
            "-i", video_path,
            "-version" # Dummy check
        ]
        
        # Real command
        cmd = [
            ffmpeg_exe, "-y", "-i", video_path,
            "-af", filter_str,
            "-vn", # No video
            "-ac", "1", # Mono (mejor para Whisper)
            "-ar", "16000", # Sample rate ideal para Whisper
            output_audio
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"--- [DONE] Audio limpio generado: {output_audio} ---")
        except subprocess.CalledProcessError as e:
            print(f"ERROR en Denoising: {e.stderr.decode()}")
            # Fallback a extracción simple si falla el filtro
            subprocess.run([ffmpeg_exe, "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", output_audio], check=True)


    @staticmethod
    def export_srt(transcript: list, output_path: str):
        """Genera un archivo .srt estándar."""
        print(f"--- Exportando subtítulos SRT -> {output_path} ---")
        
        def format_time(seconds):
            td = int(seconds * 1000)
            ms = td % 1000
            s = (td // 1000) % 60
            m = (td // (1000 * 60)) % 60
            h = (td // (1000 * 60 * 60))
            return f"{h:02}:{m:02}:{s:02},{ms:03}"

        lines = []
        for i, seg in enumerate(transcript):
            lines.append(f"{i + 1}")
            lines.append(f"{format_time(seg['start'])} --> {format_time(seg['end'])}")
            lines.append(seg['text'])
            lines.append("")
            
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def burn_subtitles(video_path: str, transcript: list, output_path: str, style: str = "yt", logo_path: str = None):
        """Quema subtítulos ULTRA-RÁPIDO usando motor nativo FFmpeg (.ass) y Logo opcional."""
        import subprocess
        from moviepy import VideoFileClip
        
        with VideoFileClip(video_path) as v:
            duration = v.duration
            w, h = v.size
        
        ass_path = os.path.join(os.path.dirname(output_path), f"burn_{uuid.uuid4().hex[:8]}.ass")
        VideoEngine._generate_ass_file(transcript, None, -1, duration, ass_path, res_x=w, res_y=h, style_type=style)
        
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"

        ass_path_esc = ass_path.replace("\\", "/").replace(":", "\\:")
        
        # Filtro: Subtítulos + Logo (si existe)
        inputs = ["-i", video_path]
        if logo_path and os.path.exists(logo_path):
            inputs.extend(["-i", logo_path])
            # Mapping complejo: [video] -> [subtitles] -> [overlay]
            # Redimensionamos el logo a 180px de ancho (proporcional) y bajamos un poco de los bordes
            filter_str = f"[0:v]subtitles='{ass_path_esc}'[vsub];[1:v]scale=180:-1[logo];[vsub][logo]overlay=main_w-overlay_w-35:main_h-overlay_h-35"
        else:
            filter_str = f"subtitles='{ass_path_esc}'"

        cmd = [ffmpeg_exe, "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-c:v", "h264_nvenc", "-preset", "p1", "-cq", "24",
            "-c:a", "copy",
            output_path
        ]
        
        print(f"--- [PRO BURN] Quemando subtítulos y Logo [{style}] -> {output_path} ---")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"--- [DONE] Quemado Pro completado: {output_path} ---")
        except subprocess.CalledProcessError as e:
            print(f"ERROR en FFmpeg Pro: {e.stderr.decode()}")
        finally:
            if os.path.exists(ass_path): os.remove(ass_path)

    @staticmethod
    def export_vertical_916(video_path: str, output_path: str):
        """Recorte vertical (9:16) ULTRA-RÁPIDO vía FFmpeg (GPU)."""
        import subprocess
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"

        # Aplicar Crop (16:9 -> 9:16) + Scale (720x1280) en GPU
        cmd = [
            ffmpeg_exe, "-y", "-i", video_path,
            "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=720:1280",
            "-c:v", "h264_nvenc", "-preset", "p1", "-cq", "24",
            "-c:a", "copy",
            output_path
        ]
        
        print(f"--- [PRO CROP] Exportando Vertical -> {output_path} ---")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"--- [DONE] Vertical Exportado: {output_path} ---")
        except subprocess.CalledProcessError as e:
            print(f"ERROR en FFmpeg Pro: {e.stderr.decode()}")

    @staticmethod
    def _generate_ass_file(transcript: list, cta_text: str, cta_start: float, duration: float, ass_path: str, res_x: int = 720, res_y: int = 1280, style_type: str = "tiktok"):
        """Genera un archivo de subtítulos (.ass) optimizado para engagement (Viral Style)."""
        # Estilos Ultra-Visibles para Shorts/TikTok
        # Estilos Ultra-Visibles para Shorts/TikTok
        # Dynamic Scaling (Detect 9:16 vs 16:9)
        is_vertical = res_y > res_x
        if is_vertical:
            margin_v = 450 if style_type in ["tiktok", "clean"] else 120
            font_size = 100 if style_type in ["tiktok", "clean"] else 65
        else:
            # Standard horizontal scaling (YouTube Style)
            margin_v = 60 if style_type in ["tiktok", "clean"] else 50
            font_size = 55 if style_type in ["tiktok", "clean"] else 45
        
        outline = 6 if style_type in ["tiktok", "clean"] else 4
        # TikTok default color is now White (&H00FFFFFF). 
        # Highlight color will be Yellow (&H0000FFFF) via override tags.
        base_color = "&H00FFFFFF" 
        
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},{base_color},&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,{outline},0,2,10,10,{margin_v},1
Style: CTA,Arial,75,&H0000FF00,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,5,0,5,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        def format_ass_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = seconds % 60
            return f"{h}:{m:02}:{s:05.2f}"

        events = []
        # Subtítulos dinámicos (HIGHLIGHT REAL-TIME)
        for seg in transcript:
            words = seg.get('words', [])
            if not words:
                c_start, c_end, c_text = seg['start'], seg['end'], seg['text']
                events.append(f"Dialogue: 0,{format_ass_time(c_start)},{format_ass_time(c_end)},Default,,0,0,0,,{c_text.upper()}")
            else:
                # Group in chunks of 3 for visibility
                for i in range(0, len(words), 3):
                    subset = words[i:i+3]
                    group_start = subset[0]['start']
                    group_end = subset[-1]['end']
                    
                    # Highlight each word precisely
                    for j, current_w in enumerate(subset):
                        h_start = current_w['start']
                        # Highlight lasts until next word starts OR whole group ends
                        if j < len(subset) - 1:
                            h_end = subset[j+1]['start']
                        else:
                            h_end = group_end
                        
                        # Fix for very small/negative intervals (FFmpeg safety)
                        if h_end <= h_start: h_end = h_start + 0.1
                        
                        # Generate text with color tags: Yellow (&H00FFFF) for active, White (&HFFFFFF) for others
                        parts = []
                        for k, w in enumerate(subset):
                            txt = w['word'].upper().replace(",", "").replace(".", "")
                            if k == j:
                                if style_type == "tiktok": # Highlight logic for TikTok (Yellow)
                                    parts.append(f"{{\\1c&H00FFFF&}}{txt}{{\\1c&HFFFFFF&}}")
                                elif style_type == "clean": # Highlight logic for Clean (Gray)
                                    parts.append(f"{{\\1c&H00CCCCCC&}}{txt}{{\\1c&HFFFFFF&}}")
                                else:
                                    parts.append(txt)
                            else:
                                parts.append(txt)
                                
                        final_txt = " ".join(parts)
                        events.append(f"Dialogue: 0,{format_ass_time(h_start)},{format_ass_time(h_end)},Default,,0,0,0,,{final_txt}")


        # CTA animado con Efecto 'Shake' (Solo TikTok)
        if cta_text and cta_start >= 0 and style_type == "tiktok":
            import random
            shake_duration = duration - cta_start
            t = cta_start
            # Generamos micro-líneas de 0.05s con desplazamientos aleatorios para simular temblor
            while t < duration:
                step = 0.05
                dx = random.randint(-5, 5)
                dy = random.randint(-5, 5)
                # Posición base 360, 1050 (Más arriba para no chocar)
                shake_pos = f"\\pos({360 + dx},{1050 + dy})"
                events.append(f"Dialogue: 1,{format_ass_time(t)},{format_ass_time(min(t + step, duration))},CTA,,0,0,0,,{{{shake_pos}}}{cta_text.upper()}")
                t += step
        elif cta_text and cta_start >= 0:
            events.append(f"Dialogue: 1,{format_ass_time(cta_start)},{format_ass_time(duration)},CTA,,0,0,0,,{cta_text.upper()}")

        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events))

    @staticmethod
    def create_social_clip(video_path: str, start: float, end: float, transcript: list, part_text: str, cta_text: str, output_path: str, logo_path: str = None):
        """Genera un clip vertical (9:16) con Outro Animado y Logo."""
        import subprocess
        
        # En TikTok Social, la CTA debe ser después de la voz.
        # Buscamos el final de la voz en este rango.
        last_voice_t = 0
        for seg in transcript:
            if seg['start'] >= start and seg['end'] <= end:
                last_voice_t = max(last_voice_t, seg['end'] - start)
        
        duration = end - start
        cta_start_abs = last_voice_t + 0.5 # Empezar medio segundo después de la voz
        if cta_start_abs > duration - 1.0:
            cta_start_abs = max(0, duration - 3.0) # Fallback si no hay espacio

        project_dir = os.path.dirname(output_path)
        ass_path = os.path.join(project_dir, f"subtitles_{uuid.uuid4().hex[:8]}.ass")
        sfx_path = os.path.join(settings.BASE_DIR, "..", "assets", "lys.mp3")
        
        sub_transcript = []
        for seg in transcript:
            if seg['start'] >= start and seg['end'] <= end:
                new_seg = seg.copy()
                new_seg['start'] -= start
                new_seg['end'] -= start
                if 'words' in new_seg:
                    new_seg['words'] = [
                        {"start": w['start'] - start, "end": w['end'] - start, "word": w['word']}
                        for w in new_seg['words']
                    ]
                sub_transcript.append(new_seg)

        VideoEngine._generate_ass_file(sub_transcript, cta_text, cta_start_abs, duration, ass_path, res_x=720, res_y=1280, style_type="tiktok")
        
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_exe = "ffmpeg"

        ass_path_esc = ass_path.replace("\\", "/").replace(":", "\\:")
        
        # Filtros de Video: Crop -> Scale/Zoom -> Subtitles -> LOGO (opcional)
        video_filters = (
            f"setpts=PTS-STARTPTS,"
            f"crop=ih*9/16:ih:(iw-ih*9/16)/2:0,"
            f"scale=w='720*min(1.2,1+0.066*t)':h='1280*min(1.2,1+0.066*t)':eval=frame,crop=720:1280,"
            f"subtitles='{ass_path_esc}'"
        )
        
        # Cambiamos a Input Seeking (-ss antes de -i) para máxima precisión y velocidad
        inputs = ["-ss", str(start), "-t", str(duration), "-i", video_path]
        overlay_map = "[0:v]"
        
        # Logo en TikTok (Top-Right)
        if logo_path and os.path.exists(logo_path):
            inputs.extend(["-i", logo_path])
            # Aplicamos overlay al final de los filtros, redimensionando el logo a 180px
            video_filters += f"[vid];[1:v]scale=180:-1[logo];[vid][logo]overlay=main_w-overlay_w-35:35"
        
        # Mezcla de Audio: Original + SFX (lys.mp3) al final
        audio_inputs = []
        if os.path.exists(sfx_path):
            # Asset de sonido al final (lys.mp3) temporalmente desplazado
            inputs.extend(["-itsoffset", str(last_voice_t), "-i", sfx_path])
            sfx_idx = 2 if (logo_path and os.path.exists(logo_path)) else 1
            # Sincronizamos audio con aresample=async=1 y dropout_transition=0
            audio_filters = (
                f"[0:a]aresample=async=1[maina];"
                f"[{sfx_idx}:a]aresample=async=1[sfx];"
                f"[maina][sfx]amix=inputs=2:duration=first:dropout_transition=0[outa];"
                f"[outa]afade=t=out:st={duration-1}:d=1[finala]"
            )
            mapping = ["-map", "[outv]", "-map", "[finala]"]
        else:
            audio_filters = f"[0:a]aresample=async=1,afade=t=out:st={duration-1}:d=1[finala]"
            mapping = ["-map", "[outv]", "-map", "[finala]"]

        cmd = [ffmpeg_exe, "-y"] + inputs + [
            "-filter_complex", f"[0:v]{video_filters}[outv];{audio_filters}",
        ] + mapping + [
            "-c:v", "h264_nvenc", "-preset", "p1", "-cq", "24",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]

        print(f"--- [PRO RENDER] Social Clip [{cta_text}] -> {output_path} ---")
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"--- [DONE] Renderizado Pro completado ---")
        except subprocess.CalledProcessError as e:
            print(f"ERROR en FFmpeg Pro: {e.stderr.decode()}")
        finally:
            if os.path.exists(ass_path): os.remove(ass_path)

    @staticmethod
    def assemble_matched_video(video_path: str, matches: list, voice_path: str, output_path: str):
        """Monta un video usando clips seleccionados por CLIP para cada segmento de voz."""
        print(f"--- Ensamblando montaje inteligente ({len(matches)} escenas) ---")
        
        final_clips = []
        with VideoFileClip(video_path) as original_video:
            for match in matches:
                seg = match['segment']
                scene_start, scene_end = match['scene']
                
                # Duración del audio para este segmento
                duration = seg['end'] - seg['start']
                
                # RELLENO INTELIGENTE: Si la escena está muy cerca del final y es más corta que el audio,
                # retrocedemos el punto de inicio para que siempre haya imagen fluida (adiós frames negros).
                # Usamos una holgura de 0.1s para evitar errores de redondeo al final del archivo.
                actual_start = max(0.0, min(scene_start, original_video.duration - duration - 0.1))
                
                # Recortamos con el punto de inicio ajustado
                clip = original_video.subclipped(actual_start, actual_start + duration)
                
                # Forzamos la duración exacta para sincronización perfecta
                clip = clip.with_duration(duration)
                
                final_clips.append(clip)
            
            final_video = concatenate_videoclips(final_clips, method="compose")
            
            # AUDIO LAYERS: Solo Voz
            audio_layers = [AudioFileClip(voice_path)]
            
            from moviepy.audio.AudioClip import CompositeAudioClip
            final_audio = CompositeAudioClip(audio_layers)
            final_audio = CompositeAudioClip(audio_layers)
            final_video = final_video.with_audio(final_audio)
            
            final_video.write_videofile(output_path, fps=30, codec="h264_nvenc", audio_codec="aac", threads=6, preset="p1")
            
            for c in final_clips:
                c.close()

video_engine = VideoEngine()
