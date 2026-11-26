@echo off
setlocal enabledelayedexpansion

echo ============================================
echo  Release - Gerador Inteligente de Documentos
echo ============================================

if exist "venv\Scripts\python.exe" (
    set PY=venv\Scripts\python.exe
    set PIP=venv\Scripts\pip.exe
    set PYINST=venv\Scripts\python.exe -m PyInstaller
) else if exist "..\venv\Scripts\python.exe" (
    set PY=..\venv\Scripts\python.exe
    set PIP=..\venv\Scripts\pip.exe
    set PYINST=..\venv\Scripts\python.exe -m PyInstaller
) else (
    set PY=python
    set PIP=pip
    set PYINST=python -m PyInstaller
)

set /p VERSION=<version.txt
set VERSION=%VERSION: =%
if "%VERSION%"=="" (
    echo ERRO: nao foi possivel ler versao de version.txt
    pause & exit /b 1
)
set TAG=v%VERSION%
echo Versao: %TAG%
echo.

:: O executavel e compilado da pasta atual: ela precisa estar igual ao commit
set SUJO=
for /f "delims=" %%l in ('git status --porcelain --untracked-files^=no -- .') do set SUJO=1
for /f "delims=" %%l in ('git ls-files --others --exclude-standard -- "*.py"') do set SUJO=1
if defined SUJO ( echo ERRO: ha alteracoes sem commit. Faca o commit antes do release. & pause & exit /b 1 )

gh auth status >nul 2>&1
if errorlevel 1 ( echo ERRO: GitHub CLI nao autenticado. Execute: gh auth login & pause & exit /b 1 )

gh release view %TAG% --repo DaviTSelect/gerador-inteligente-documentos >nul 2>&1
if not errorlevel 1 (
    echo ERRO: a release %TAG% ja existe.
    echo Incremente a versao em gerador_documentos\version.txt antes de fazer release.
    pause & exit /b 1
)

:: Tag sem release e permitida, desde que aponte para o commit atual
set TAG_EXISTE=
set TAG_COMMIT=
set HEAD_COMMIT=
git fetch --tags -q 2>nul
for /f %%c in ('git rev-parse HEAD') do set HEAD_COMMIT=%%c
for /f %%c in ('git rev-list -n 1 %TAG% 2^>nul') do set TAG_COMMIT=%%c
if defined TAG_COMMIT (
    set TAG_EXISTE=1
    if not "!TAG_COMMIT!"=="!HEAD_COMMIT!" (
        echo ERRO: a tag %TAG% existe em outro commit. Incremente version.txt.
        pause & exit /b 1
    )
)

echo [1/5] Instalando dependencias de build...
%PIP% install -r requirements.txt -q
if errorlevel 1 ( echo ERRO ao instalar dependencias & pause & exit /b 1 )
%PIP% install pyinstaller -q
if %ERRORLEVEL% neq 0 ( echo ERRO ao instalar dependencias & pause & exit /b 1 )

echo [2/5] Executando testes...
%PY% -m pytest tests -q
if errorlevel 1 ( echo ERRO nos testes & pause & exit /b 1 )

echo [3/5] Compilando executavel...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
%PYINST% GeradorDocumentos.spec --noconfirm
if %ERRORLEVEL% neq 0 ( echo ERRO no PyInstaller & pause & exit /b 1 )
if not exist "dist\GeradorDocumentos.exe" (
    echo ERRO: dist\GeradorDocumentos.exe nao encontrado
    pause & exit /b 1
)

echo [4/5] Calculando SHA-256...
set "SHA256="
for /f "usebackq delims=" %%h in (`powershell -NoProfile -Command "(Get-FileHash 'dist\GeradorDocumentos.exe' -Algorithm SHA256).Hash.ToLower()"`) do set SHA256=%%h
if not defined SHA256 ( echo ERRO ao calcular o SHA-256 & pause & exit /b 1 )
echo %SHA256%  GeradorDocumentos.exe > dist\GeradorDocumentos.exe.sha256
echo SHA-256: %SHA256%

echo [5/5] Publicando release %TAG% no GitHub...
if not defined TAG_EXISTE git tag %TAG%
git push origin %TAG%
if errorlevel 1 (
    if not defined TAG_EXISTE git tag -d %TAG% >nul 2>&1
    echo ERRO ao enviar tag para o GitHub
    pause & exit /b 1
)

set NOTES_FILE=%TEMP%\release_notes_%VERSION%.md
(
    echo ## Instalacao
    echo.
    echo 1. Baixe GeradorDocumentos.exe
    echo 2. Coloque na pasta desejada
    echo 3. Execute GeradorDocumentos.exe
    echo.
    echo **SHA-256:** %SHA256%
) > "%NOTES_FILE%"

:: --latest=false: o atualizador ate a v1.1.1 entra em loop se enxergar versao nova em /latest.
:: O atualizador atual compara todas as releases e nao depende dessa marca.
gh release create %TAG% ^
    "dist\GeradorDocumentos.exe" ^
    "dist\GeradorDocumentos.exe.sha256" ^
    --title "Gerador Inteligente de Documentos %TAG%" ^
    --notes-file "%NOTES_FILE%" ^
    --latest=false ^
    --repo DaviTSelect/gerador-inteligente-documentos

if %ERRORLEVEL% neq 0 (
    echo ERRO ao criar release no GitHub
    del "%NOTES_FILE%" >nul 2>&1
    pause & exit /b 1
)
del "%NOTES_FILE%" >nul 2>&1

echo.
echo ============================================
echo  Release %TAG% publicada com sucesso!
echo  https://github.com/DaviTSelect/gerador-inteligente-documentos/releases/tag/%TAG%
echo ============================================
pause
