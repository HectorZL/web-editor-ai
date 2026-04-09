import queue
import threading
import time
import logging
from typing import Callable, Any, Dict

# Configurar logging para ver la cola en la consola
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QueueManager")

class QueueManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(QueueManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.job_queue = queue.Queue()
        self.processed_count = 0
        self.active_job = None
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        self._initialized = True
        logger.info("--- QueueManager iniciado y esperando tareas... ---")

    def add_job(self, func: Callable, *args, **kwargs):
        """Añade un trabajo a la cola secuencial."""
        self.job_queue.put((func, args, kwargs))
        logger.info(f"--- Tarea añadida a la cola. Tamaño actual: {self.job_queue.qsize()} ---")

    def _worker(self):
        """Worker que procesa tareas una por una."""
        while True:
            try:
                # Obtener la siguiente tarea (bloqueante)
                func, args, kwargs = self.job_queue.get()
                
                # Extraer metadatos para el monitoreo (según nuestra firma estándar)
                job_id = args[0] if len(args) > 0 else "unknown"
                project_name = args[1] if len(args) > 1 else "unknown"
                
                self.active_job = {
                    "job_id": job_id,
                    "project": project_name,
                    "task": func.__name__,
                    "start_time": time.time()
                }
                
                logger.info(f"--- Iniciando procesamiento de tarea: {func.__name__} (Job: {job_id}) ---")
                
                # Ejecutar la función
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error procesando tarea en la cola: {str(e)}")
                finally:
                    # Limpiar estado activo e incrementar procesados
                    self.active_job = None
                    self.processed_count += 1
                
                logger.info(f"--- Tarea finalizada. Total procesados: {self.processed_count}. Restantes: {self.job_queue.qsize()} ---")
                
                # Marcar tarea como completada para la cola
                self.job_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error crítico en el worker de la cola: {str(e)}")
                time.sleep(1) # Evitar bucle infinito de errores

queue_manager = QueueManager()
