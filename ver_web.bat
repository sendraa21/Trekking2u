@echo off
rem Trekking2u: abre la web en este PC (http://127.0.0.1:8000) para verla antes de publicar.
rem Cierra esta ventana para pararla.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m trekking servir
