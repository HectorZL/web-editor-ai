# VideoFlow AI - Advanced Automated Video Editor

[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-v15.0+-black.svg)](https://nextjs.org/)
[![CUDA](https://img.shields.io/badge/CUDA-Enabled-76B900.svg)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**VideoFlow AI** is a professional-grade monorepo designed for automated video editing, leveraging state-of-the-art AI models for transcription, semantic scene matching, and advanced audio processing. Optimized for NVIDIA hardware with a focus on high performance and memory efficiency.

---

## 🛠 Technical Architecture

This project follows a monorepo structure separating the logic into two core layers:

- **Backend (`/backend`)**: A FastAPI high-performance server managing the AI pipeline, orchestrating GPU tasks, and handling FFmpeg-based video manipulation.
- **Frontend (`/frontend`)**: A modern Next.js 15 interface for real-time video previewing, queue management, and editing control.

## 🧠 AI Features & Models

### 1. Smart Subtitling (Faster Whisper)
Integrated with the **Faster Whisper** engine, the system achieves near-instant transcription speeds by using CTranslate2.
- **Precision**: Word-level timestamps for dynamic styling.
- **Viral Styles**: Automated generation of `.ass` (Advanced Substation Alpha) files for "Shorts/TikTok" style highlighting.
- **Performance**: Up to 4x faster than standard Whisper while consuming less VRAM.

### 2. Semantic Scene Matching (CLIP)
Uses **SentenceTransformer (CLIP)** to align script text with video footage.
- **Iterative Processing**: Analyzes video frames in optimized batches to prevent OOM errors.
- **Dime-Scale Sampling**: Resizes frames to 224x224 (CLIP's native resolution) before processing, reducing memory usage by up to 40x compared to 1080p frame analysis.
- **Temporal Variety**: Implements a diversity penalty to prevent repetitive scene selection.

### 3. Advanced Audio Engineering
The `VideoEngine` module leverages specialized FFmpeg filters:
- **Denoising**: FFT-based reductions (`afftdn`) targets background static without distorting human speech.
- **Sidechain Ducking**: Automated dynamic volume compression for background music when voice is detected.
- **Standardization**: High-pass and low-pass filtering to optimize audio for Whisper's 16kHz requirement.

---

## 🖥 Hardware Recommendations & VRAM Management

Specifically optimized for **NVIDIA RTX 3060 (8GB VRAM)**.

### Optimizations for 8GB VRAM:
- **FP16 Precision**: All CLIP and Whisper calculations are performed in FP16 to halve memory footprint and increase throughput.
- **Sequential Unloading**: Models are loaded/unloaded on-demand using `torch.cuda.empty_cache()` and garbage collection to ensure the GPU doesn't saturate.
- **NVENC Acceleration**: Uses NVIDIA's hardware encoder (`h264_nvenc`) with the `p1` (Performance) preset for ultra-fast exports with minimal CPU overhead.

> [!WARNING]
> **OOM Protection**: If you have 8GB of VRAM, we recommend closing hardware-accelerated browsers (like Chrome or Brave) during heavy rendering tasks to avoid "Out of Memory" errors.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- NVIDIA GPU with CUDA 11.8+
- FFmpeg installed in system PATH

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate
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

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
