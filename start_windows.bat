@echo off
rem Inicia la herramienta FCP en el navegador. Doble clic para ejecutar.
cd /d "%~dp0"
uv run streamlit run app.py
if errorlevel 1 pause
