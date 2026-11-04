@echo off
chcp 65001 >nul
echo ===================================================
echo  Build — Gerador Inteligente de Documentos
echo ===================================================

REM Lê a versão atual
set /p VERSION=<version.txt
set VERSION=%VERSION: =%
echo Versão: %VERSION%

REM Verifica dependências de build
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo.
echo Gerando executável...
echo.

pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=logo.ico ^
  --name="GeradorDocumentos" ^
  --add-data="version.txt;." ^
  --add-data="logo.ico;." ^
  --hidden-import=docx2pdf ^
  --hidden-import=chardet ^
  --hidden-import=openpyxl ^
  main.py

if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou. Verifique os erros acima.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  Build concluído com sucesso!
echo  Executável: dist\GeradorDocumentos.exe
echo  Versão:     %VERSION%
echo ===================================================
echo.

REM Copia version.txt para dist/ junto com o exe
copy version.txt dist\version.txt >nul 2>&1

pause
