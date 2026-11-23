@echo off
rem Trekking2u: procesa las rutas nuevas de data\raw, regenera la web y la sube a GitHub.
rem Doble clic para ejecutarlo.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno de Python. Mira el README, paso "Preparar el PC".
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m trekking publicar %*
echo.
pause
