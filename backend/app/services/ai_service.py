import os
import torch
import cv2
import numpy as np
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer, util
from PIL import Image
from ..core.config import settings

class AIService:
    _instance = None
    _whisper_model = None
    _clip_model = None

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.compute_type = settings.WHISPER_COMPUTE_TYPE if self.device == "cuda" else "int8"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_whisper(self) -> WhisperModel:
        if self._whisper_model is None:
            print(f"--- Cargando Whisper ({settings.WHISPER_MODEL}) en {self.device} ---")
            self._whisper_model = WhisperModel(
                settings.WHISPER_MODEL, 
                device=self.device, 
                compute_type=self.compute_type
            )
        return self._whisper_model

    def get_clip(self) -> SentenceTransformer:
        if self._clip_model is None:
            print(f"--- Cargando CLIP ({settings.CLIP_MODEL_NAME}) en {self.device} ---")
            self._clip_model = SentenceTransformer(settings.CLIP_MODEL_NAME, device=self.device)
            if self.device == "cuda":
                # OPTIMIZACIÓN SAFE: Cargar en FP16 para ganar un 40-50% de velocidad en NVIDIA
                self._clip_model.half()
        return self._clip_model

    def transcribe(self, audio_path: str, language: str = None):
        model = self.get_whisper()
        
        # Si el idioma es "auto", lo tratamos como None para Whisper
        target_lang = None if language == "auto" else language
        
        print(f"--- [WHISPER] Transcribiendo. Idioma forzado: {target_lang or 'Auto-Detect'} ---")
        
        # Word timestamps enable the platform-specific styling later
        segments, info = model.transcribe(
            audio_path, 
            beam_size=5, 
            word_timestamps=True,
            language=target_lang
        )
        
        results = []
        for segment in segments:
            results.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "words": [
                    {"start": w.start, "end": w.end, "word": w.word.strip()} 
                    for w in (segment.words or [])
                ]
            })
        return results

    def unload_whisper(self):
        """Libera Whisper de la VRAM."""
        import gc
        if self._whisper_model is not None:
            self._whisper_model = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            print("--- Whisper descargado. ---")

    def unload_clip(self):
        """Libera CLIP de la VRAM."""
        import gc
        if self._clip_model is not None:
            self._clip_model = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            print("--- CLIP descargado. ---")

    def unload_models(self):
        """Sequential VRAM optimization: Clear models from Memory/GPU."""
        self.unload_whisper()
        self.unload_clip()
        print("--- Todos los modelos descargados. VRAM liberada. ---")

    def get_frame_from_cap(self, cap, timestamp: float, size=(224, 224)) -> Image:
        """Extrae un frame optimizado (224x224) para CLIP. Ahorra 40x de RAM."""
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        if ret:
            # OPTIMIZACIÓN CRÍTICA: Redimensionar ANTES de convertir a PIL
            # CLIP usa 224x224 internamente. No necesitamos 1080p en RAM.
            frame_resized = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            return Image.fromarray(frame_rgb)
        return None

    def match_scenes_to_segments(self, scenes: list, segments, video_path: str, progress_callback=None):
        """Usa CLIP con procesamiento iterativo para evitar saturar la RAM."""
        # PARCHE DE SEGURIDAD: Asegurar que segments sea una lista, no el envoltorio dict
        if isinstance(segments, dict) and "segments" in segments:
            segments = segments["segments"]
        elif isinstance(segments, dict):
            segments = list(segments.values())
            
        clip = self.get_clip()
        
        # 1. Procesar escenas en bloques (Batch Processing) para ahorrar RAM/VRAM
        batch_size = 48  # Aumentado de 32 para mejorar ITS/s (Velocidad Segura)
        scene_embeddings = []
        total_scenes = len(scenes)
        
        print(f"--- [RAM-SAFE] Procesando {total_scenes} escenas en lotes de {batch_size} ---")
        
        cap = cv2.VideoCapture(video_path)
        for i in range(0, total_scenes, batch_size):
            batch_scenes = scenes[i : i + batch_size]
            batch_frames = []
            
            for start, end in batch_scenes:
                mid = (start + end) / 2
                frame = self.get_frame_from_cap(cap, mid) # Ya viene a 224x224
                if frame: batch_frames.append(frame)
            
            if batch_frames:
                # Codificar el bloque actual y guardarlo en la GPU/RAM como tensor ligero
                with torch.no_grad():
                    embeddings = clip.encode(
                        batch_frames, 
                        batch_size=batch_size, 
                        convert_to_tensor=True,
                        show_progress_bar=False
                    )
                    # Extendemos la lista general de embeddings (muy ligeros comparados con fotos)
                    for emb in embeddings:
                        scene_embeddings.append(emb)
            
            if progress_callback:
                progress_callback(30.0 + (min(i + batch_size, total_scenes) / total_scenes) * 10.0)
                
            print(f"Batch {i//batch_size + 1}: {len(batch_frames)} frames procesados. RAM a salvo.")

        cap.release()

        # 2. Match para cada segmento (MODO MONTAGE: Si es largo, pedimos varios recortes)
        results = []
        last_used_indices = []
        
        # Pre-codificar todos los textos del script en un solo batch (más rápido)
        all_texts = [seg['text'] for seg in segments]
        text_embeddings = clip.encode(all_texts, convert_to_tensor=True, batch_size=48)
        
        print(f"--- [MONTAJE] Procesando {len(segments)} frases con cortes dinámicos ---")
        for i, seg in enumerate(segments):
            duration = seg['end'] - seg['start']
            
            # Decidimos cuántos cortes/escenas queremos para esta frase
            # Si dura 12s, queremos al menos 3 escenas (~4s cada una)
            num_cuts = 1
            if duration > 10.0: num_cuts = 3
            elif duration > 5.0: num_cuts = 2
            
            cut_duration = duration / num_cuts
            text_emb = text_embeddings[i]
            
            # Para cada corte de esta frase, buscamos la mejor escena compatible
            for cut_idx in range(num_cuts):
                cut_start = seg['start'] + (cut_idx * cut_duration)
                cut_end = cut_start + cut_duration
                
                # Comparar contra todas las escenas
                best_score = -1
                best_scene_idx = 0
                
                if scene_embeddings:
                    stack_embs = torch.stack(scene_embeddings)
                    scores = util.cos_sim(text_emb, stack_embs)[0]
                    
                    # VARIEDAD DINÁMICA: Penalizar escenas usadas recientemente
                    for idx in last_used_indices:
                        scores[idx] *= 0.15 # Penalización extrema (85%) para forzar variedad total
                        # Penalización de vecinos: No usar lo que está justo antes o después
                        if idx > 0: scores[idx-1] *= 0.5
                        if idx < len(scenes)-1: scores[idx+1] *= 0.5
                    
                    # BONO CRONOLÓGICO: Favorecer escenas que avanzan con el video
                    # Calculamos progreso del 'sub-corte' actual
                    total_video_dur = scenes[-1][1] if scenes else 1.0
                    subcut_progress = cut_start / segments[-1]['end'] # Progreso en el guion
                    
                    scene_times = torch.tensor([(s[0] + s[1]) / 2 / total_video_dur for s in scenes], device=self.device)
                    temporal_weights = 1.0 - torch.abs(scene_times - subcut_progress)
                    
                    # Puntuación final
                    scores = scores + (temporal_weights * 0.35)
                    
                    best_score = torch.max(scores).item()
                    best_scene_idx = torch.argmax(scores).item()
                    
                    # Actualizar historial
                    last_used_indices.append(best_scene_idx)
                    if len(last_used_indices) > 40: # Memoria extendida para videos largos
                        last_used_indices.pop(0)

                results.append({

                    "segment": {
                        "start": cut_start,
                        "end": cut_end,
                        "text": seg['text']
                    },
                    "scene": scenes[best_scene_idx],
                    "score": best_score
                })
            
            if progress_callback:
                progress_callback(40.0 + (i / len(segments)) * 10.0)
                
        return results

    def get_image_embedding(self, image: Image):
        model = self.get_clip()
        return model.encode(image, convert_to_tensor=True)

    def get_text_embedding(self, text: str):
        model = self.get_clip()
        return model.encode(text, convert_to_tensor=True)

ai_service = AIService.get_instance()
