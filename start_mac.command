#!/bin/bash
# Inicia la herramienta FCP en el navegador. Doble clic para ejecutar.
cd "$(dirname "$0")"
uv run streamlit run app.py
