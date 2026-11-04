"""
updater.py — Verificação e aplicação de atualizações automáticas.

Compara version.txt local com a release mais recente do GitHub.
Se houver versão nova: baixa, aplica os arquivos e reinicia o app.

Configure GITHUB_REPO antes de publicar.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

# ── Configure aqui ───────────────────────────────────────────────────────────
# Formato: "usuario/nome-do-repositorio"
GITHUB_REPO = "DaviTSelect/gerador-inteligente-documentos"
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(_PASTA_BASE, "version.txt")


# ── Versão local ─────────────────────────────────────────────────────────────

def ler_versao_local() -> str:
    """Retorna a versão do arquivo version.txt (ex: '1.0.0')."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip().lstrip("v")
    except FileNotFoundError:
        return "0.0.0"


# ── Versão remota ─────────────────────────────────────────────────────────────

def buscar_release_mais_recente(timeout: int = 6) -> dict:
    """
    Consulta a API do GitHub e retorna o dict da release mais recente.
    Retorna {} se a consulta falhar (sem internet, repo inválido, etc.).
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"User-Agent": "GeradorDocumentos-Updater/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return {}


def _versao_para_tupla(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0, 0, 0)


def verificar_atualizacao() -> dict:
    """
    Verifica se há atualização disponível.

    Retorna dict com:
        disponivel  : bool
        versao_local: str
        versao_nova : str
        url_download: str   (asset .zip ou .exe)
        notas       : str   (body da release)
    """
    local = ler_versao_local()
    release = buscar_release_mais_recente()

    if not release:
        return {"disponivel": False, "versao_local": local,
                "versao_nova": "", "url_download": "", "notas": ""}

    remota = release.get("tag_name", "0.0.0").lstrip("v")
    notas = release.get("body", "")

    # Encontra o melhor asset: prefere .zip (fonte), aceita .exe (compilado)
    url_zip = ""
    url_exe = ""
    for asset in release.get("assets", []):
        nome = asset.get("name", "").lower()
        url = asset.get("browser_download_url", "")
        if nome.endswith(".zip") and not url_zip:
            url_zip = url
        elif nome.endswith(".exe") and not url_exe:
            url_exe = url

    url_download = url_zip or url_exe
    disponivel = bool(url_download) and (
        _versao_para_tupla(remota) > _versao_para_tupla(local)
    )

    return {
        "disponivel": disponivel,
        "versao_local": local,
        "versao_nova": remota,
        "url_download": url_download,
        "notas": notas,
    }


# ── Aplicar atualização ───────────────────────────────────────────────────────

def _baixar_arquivo(url: str, destino: str, callback=None):
    """Baixa url → destino, chamando callback(bytes_baixados, total) se fornecido."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "GeradorDocumentos-Updater/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length", 0))
        baixados = 0
        with open(destino, "wb") as f:
            while True:
                bloco = resp.read(65536)
                if not bloco:
                    break
                f.write(bloco)
                baixados += len(bloco)
                if callback:
                    callback(baixados, total)


def aplicar_atualizacao(url_download: str, versao_nova: str,
                         callback_progresso=None) -> bool:
    """
    Baixa e aplica a atualização.

    callback_progresso(bytes_baixados, total) chamado durante o download.
    Retorna True em caso de sucesso.
    """
    nome_arq = url_download.split("/")[-1].split("?")[0]

    with tempfile.TemporaryDirectory() as tmp:
        caminho_tmp = os.path.join(tmp, nome_arq)
        _baixar_arquivo(url_download, caminho_tmp, callback_progresso)

        if nome_arq.lower().endswith(".zip"):
            _aplicar_zip(caminho_tmp, versao_nova)

        elif nome_arq.lower().endswith(".exe"):
            _aplicar_exe(caminho_tmp)
            return True  # reinício é agendado no _aplicar_exe

    # Atualiza version.txt local
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(versao_nova + "\n")

    return True


def _aplicar_zip(caminho_zip: str, versao_nova: str):
    """Extrai o ZIP sobre a pasta atual e atualiza version.txt."""
    pasta_extracao = caminho_zip + "_extraido"
    with zipfile.ZipFile(caminho_zip, "r") as zf:
        zf.extractall(pasta_extracao)

    # Se o ZIP tem uma subpasta raiz, entra nela
    conteudo = os.listdir(pasta_extracao)
    if len(conteudo) == 1 and os.path.isdir(os.path.join(pasta_extracao, conteudo[0])):
        pasta_extracao = os.path.join(pasta_extracao, conteudo[0])

    # Copia arquivos sobre a pasta atual (preserva pastas que o ZIP não tem)
    for item in os.listdir(pasta_extracao):
        src = os.path.join(pasta_extracao, item)
        dst = os.path.join(_PASTA_BASE, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def _aplicar_exe(caminho_novo_exe: str):
    """
    Substitui o executável compilado (.exe) pelo novo via script .bat temporário.
    O script roda depois que o processo atual encerrar.
    """
    exe_atual = sys.executable if getattr(sys, "frozen", False) else None
    if not exe_atual:
        return

    # Copia o novo .exe para fora do tempdir (que será apagado)
    novo_exe_copia = exe_atual + ".new"
    shutil.copy2(caminho_novo_exe, novo_exe_copia)

    bat = os.path.join(_PASTA_BASE, "_update_replace.bat")
    with open(bat, "w", encoding="ascii") as f:
        f.write("@echo off\n")
        f.write("timeout /t 2 /nobreak >nul\n")
        f.write(f'move /y "{novo_exe_copia}" "{exe_atual}"\n')
        f.write(f'start "" "{exe_atual}"\n')
        f.write('del "%~f0"\n')

    subprocess.Popen(["cmd", "/c", bat], shell=False,
                     creationflags=subprocess.CREATE_NO_WINDOW)


# ── Reinício ──────────────────────────────────────────────────────────────────

def reiniciar():
    """Reinicia o processo atual após atualização via ZIP/fonte."""
    python = sys.executable
    subprocess.Popen([python] + sys.argv)
    sys.exit(0)
