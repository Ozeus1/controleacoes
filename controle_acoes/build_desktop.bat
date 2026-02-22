@echo off
title Build - Controle de Acoes Desktop
cd /d "%~dp0"

echo.
echo ============================================================
echo  BUILD: Controle de Acoes - Versao Desktop
echo ============================================================
echo.

REM Ativa o venv
call venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo [ERRO] Ambiente virtual nao encontrado.
    echo Execute:  python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause & exit /b 1
)

REM Instala dependências de build se necessário
echo [1/4] Verificando dependencias de build...
pip install pyinstaller pywebview --quiet

REM Limpa builds anteriores
echo [2/4] Limpando builds anteriores...
if exist build\ControleAcoes  rmdir /s /q build\ControleAcoes
if exist dist\ControleAcoes   rmdir /s /q dist\ControleAcoes

REM Executa PyInstaller
echo [3/4] Compilando com PyInstaller (pode demorar 2-5 minutos)...
pyinstaller desktop_app.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou. Veja as mensagens acima.
    pause & exit /b 1
)

REM Copia arquivos externos que o usuario deve editar
echo [4/4] Copiando arquivos de configuracao externos...

REM mt5_feeder/config.py (o usuario edita este arquivo)
if not exist dist\ControleAcoes\mt5_feeder mkdir dist\ControleAcoes\mt5_feeder
if exist mt5_feeder\config.py (
    copy /y mt5_feeder\config.py dist\ControleAcoes\mt5_feeder\config.py > nul
    echo      mt5_feeder\config.py copiado.
) else (
    copy /y mt5_feeder\config_example.py dist\ControleAcoes\mt5_feeder\config.py > nul
    echo      ATENCAO: config_example.py copiado como config.py - edite antes de usar!
)

REM Banco de dados inicial (se existir)
if not exist dist\ControleAcoes\instance mkdir dist\ControleAcoes\instance
if exist instance\investments.db (
    copy /y instance\investments.db dist\ControleAcoes\instance\investments.db > nul
    echo      instance\investments.db copiado com dados atuais.
) else (
    echo      ATENCAO: Nenhum banco de dados encontrado.
    echo      Copie o arquivo investments.db para:
    echo        dist\ControleAcoes\instance\investments.db
)

echo.
echo ============================================================
echo  BUILD CONCLUIDO!
echo ============================================================
echo.
echo  Executavel: dist\ControleAcoes\ControleAcoes.exe
echo.
echo  Para rodar: dist\ControleAcoes\ControleAcoes.exe
echo  (ou copie a pasta ControleAcoes para qualquer PC Windows 10/11)
echo.
echo  ANTES DE DISTRIBUIR:
echo    1. Edite dist\ControleAcoes\mt5_feeder\config.py
echo       com seu TICKER_MAP e OPTION_MAP
echo    2. Copie o banco investments.db para
echo       dist\ControleAcoes\instance\investments.db
echo.
pause
