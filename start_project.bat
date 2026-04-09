@echo off
echo --- Limpiando procesos previos ---
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 /nobreak >nul

echo --- Iniciando VideoFlow AI ---

echo [1/2] Iniciando Backend (FastAPI)...
start "Backend VideoFlow AI" cmd /k "cd backend && call ..\.venv\Scripts\activate && python -m app.main"

echo [2/2] Iniciando Frontend (Next.js)...
start "Frontend VideoFlow AI" cmd /k "cd frontend && npm run dev"

echo ------------------------------------
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo ------------------------------------
echo Presiona cualquier tecla para cerrar este asistente...
pause
