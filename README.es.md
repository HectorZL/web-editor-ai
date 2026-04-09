# VideoFlow AI - Editor de Video Automatizado Avanzado

[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-v15.0+-black.svg)](https://nextjs.org/)
[![CUDA](https://img.shields.io/badge/CUDA-Enabled-76B900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**VideoFlow AI** es un monorepo de nivel profesional diseñado para la edición de video automatizada, utilizando modelos de IA de última generación para la transcripción, el emparejamiento semántico de escenas y el procesamiento de audio avanzado. Optimizado para hardware NVIDIA con un enfoque en alto rendimiento y eficiencia de memoria.

---

## 🛠 Arquitectura Técnica

Este proyecto sigue una estructura de monorepo separando la lógica en dos capas principales:

- **Backend (`/backend`)**: Un servidor de alto rendimiento basado en FastAPI que gestiona el pipeline de IA, orquesta las tareas de la GPU y maneja la manipulación de video a través de FFmpeg.
- **Frontend (`/frontend`)**: Una interfaz moderna en Next.js 15 para la previsualización de video en tiempo real, gestión de colas y control de edición.

## 🧠 Características de IA y Modelos

### 1. Subtitulado Inteligente (Faster Whisper)
Integrado con el motor **Faster Whisper**, el sistema logra velocidades de transcripción casi instantáneas mediante el uso de CTranslate2.
- **Precisión**: Timestamps a nivel de palabra para estilos dinámicos.
- **Estilos Virales**: Generación automatizada de archivos `.ass` (Advanced Substation Alpha) para resaltado estilo "Shorts/TikTok".
- **Rendimiento**: Hasta 4 veces más rápido que Whisper estándar consumiendo menos VRAM.

### 2. Emparejamiento Semántico de Escenas (CLIP)
Utiliza **SentenceTransformer (CLIP)** para alinear el texto del guion con el metraje de video.
- **Procesamiento Iterativo**: Analiza fotogramas de video en lotes optimizados para evitar errores de memoria (OOM).
- **Muestreo Optimizado**: Redimensiona los frames a 224x224 (resolución nativa de CLIP) antes del procesamiento, reduciendo el uso de memoria hasta 40 veces en comparación con el análisis en 1080p.
- **Variedad Temporal**: Implementa una penalización de diversidad para evitar la selección repetitiva de escenas.

### 3. Ingeniería de Audio Avanzada
El módulo `VideoEngine` aprovecha filtros especializados de FFmpeg:
- **Reducción de Ruido (Denoising)**: Reducciones basadas en FFT (`afftdn`) que eliminan el ruido de fondo sin distorsionar la voz humana.
- **Sidechain Ducking**: Compresión dinámica de volumen automatizada para la música de fondo cuando se detecta voz.
- **Estandarización**: Filtros de paso alto y paso bajo para optimizar el audio según el requisito de 16kHz de Whisper.

---

## 🖥 Recomendaciones de Hardware y Gestión de VRAM

Optimizado específicamente para **NVIDIA RTX 3060 (8GB VRAM)**.

### Optimizaciones para 8GB de VRAM:
- **Precisión FP16**: Todos los cálculos de CLIP y Whisper se realizan en FP16 para reducir a la mitad la huella de memoria y aumentar el rendimiento.
- **Descarga Secuencial**: Los modelos se cargan y descargan bajo demanda utilizando `torch.cuda.empty_cache()` y recolección de basura para asegurar que la GPU no se sature.
- **Aceleración NVENC**: Utiliza el codificador de hardware de NVIDIA (`h264_nvenc`) con el ajuste `p1` (Performance) para exportaciones ultra rápidas con mínima carga en la CPU.

> [!WARNING]
> **Protección contra OOM**: Si tienes 8GB de VRAM, recomendamos cerrar navegadores con aceleración de hardware (como Chrome o Brave) durante tareas de renderizado pesado para evitar errores de "Out of Memory".

---

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.9+
- Node.js 18+
- GPU NVIDIA con CUDA 11.8+
- FFmpeg instalado en el PATH del sistema

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # O .venv\Scripts\activate
pip install -r requirements.txt
python app/main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 📄 Licencia

Distribuido bajo la **Licencia MIT**. Mira el archivo `LICENSE` para más información.
