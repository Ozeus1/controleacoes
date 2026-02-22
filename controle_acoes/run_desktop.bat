@echo off
title Controle de Acoes - Desktop
cd /d "%~dp0"

REM Ativa o ambiente virtual
call venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo.
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute primeiro:  python -m venv venv
    echo                    venv\Scripts\activate
    echo                    pip install -r requirements.txt
    echo                    pip install -r requirements_desktop.txt
    echo.
    pause
    exit /b 1
)

REM Inicia o app desktop
python desktop_app.py

if errorlevel 1 (
    echo.
    echo [ERRO] O app encerrou com erro. Verifique as mensagens acima.
    pause
)
