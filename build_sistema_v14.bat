@echo off
echo ========================================
echo  COMPILANDO SISTEMA FINANCEIRO V14
echo ========================================
echo.

REM Fechar processos que podem estar usando o executável
echo Encerrando processos anteriores...
taskkill /F /IM sistema_financeiro_v14.exe 2>nul

REM Aguardar um momento
timeout /t 2 /nobreak >nul

REM Limpar builds anteriores
echo Limpando builds anteriores...
if exist "build" (
    rmdir /s /q "build"
)
if exist "dist" (
    rmdir /s /q "dist"
)

REM Recompilar
echo.
echo Compilando...
echo.
python -m PyInstaller sistema_financeiro_v14.spec

echo.
if exist "dist\sistema_financeiro_v14.exe" (
    echo ========================================
    echo  COMPILACAO CONCLUIDA COM SUCESSO!
    echo ========================================
    echo.
    echo Executavel: dist\sistema_financeiro_v14.exe
) else (
    echo ========================================
    echo  ERRO NA COMPILACAO!
    echo ========================================
)

echo.
pause
