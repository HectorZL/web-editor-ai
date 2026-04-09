import torch
import sys

def check_gpu():
    print("--- VideoFlow AI - Verificación de Hardware ---")
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        vram_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"GPU Detectada: {device_name}")
        print(f"VRAM Total: {vram_total:.2f} GB")
        
        if vram_total < 5.8:
            print("AVISO: Tienes cerca de 6GB de VRAM. Asegúrate de cerrar Chrome u otras apps pesadas para evitar errores de memoria.")
        else:
            print("VRAM OK: Tienes suficiente memoria para los modelos 'medium' y CLIP.")
    else:
        print("ERROR: No se detectó una GPU compatible con CUDA. El proceso será LENTO (usará CPU).")

if __name__ == "__main__":
    check_gpu()
