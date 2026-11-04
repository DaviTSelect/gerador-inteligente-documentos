@echo off
chcp 65001 >nul
echo ===================================================
echo  Build — Gerador Inteligente de Documentos
echo ===================================================

set /p VERSION=<version.txt
set VERSION=%VERSION: =%
echo Versao: %VERSION%

REM Cria o venv se não existir
if not exist "venv\Scripts\python.exe" (
    echo Criando ambiente virtual...
    python -m venv venv
)

REM Instala/atualiza dependências no venv
echo Instalando dependencias...
venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
venv\Scripts\python.exe -m pip install pyinstaller --quiet

REM Limpa builds anteriores
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist GeradorDocumentos.spec del GeradorDocumentos.spec

REM Detecta logo.ico
set ICO_FLAG=
set ICO_DATA=
if exist "..\logo.ico" (
    set ICO_FLAG=--icon=..\logo.ico
    set ICO_DATA=--add-data=..\logo.ico;.
) else if exist "logo.ico" (
    set ICO_FLAG=--icon=logo.ico
    set ICO_DATA=--add-data=logo.ico;.
)

echo.
echo Gerando executavel v%VERSION%...
echo.

venv\Scripts\python.exe -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name=GeradorDocumentos ^
    --add-data=version.txt;. ^
    --collect-all=chardet ^
    --collect-all=docx2pdf ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.cell._writer ^
    --hidden-import=pandas ^
    --hidden-import=docx ^
    --hidden-import=win32com ^
    --hidden-import=win32com.client ^
    --hidden-import=win32com.server ^
    --hidden-import=win32api ^
    --hidden-import=win32con ^
    --hidden-import=pywintypes ^
    %ICO_FLAG% ^
    %ICO_DATA% ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou. Verifique os erros acima.
    pause
    exit /b 1
)

copy version.txt dist\version.txt >nul 2>&1

echo.
echo ===================================================
echo  Build concluido!
echo  Executavel : dist\GeradorDocumentos.exe
echo  Versao     : %VERSION%
echo ===================================================
pause
