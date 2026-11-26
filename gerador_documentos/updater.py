"""
updater.py — Verificação e aplicação de atualizações automáticas.

Fluxo:
  1. Lista as Releases publicadas no GitHub (ignora draft e prerelease).
  2. Escolhe a maior versão que tenha o arquivo certo nos Assets.
  3. Baixa para uma pasta temporária e confere tamanho, SHA-256 e formato PE.
  4. Executa o novo .exe em modo de autoverificação.
  5. Só então troca o executável (rename), guardando o antigo até o próximo
     início. Qualquer falha mantém ou restaura a versão atual.

O repositório é público: nenhum token é necessário.
Log técnico: %LOCALAPPDATA%\\GeradorDocumentos\\atualizador.log
"""
import contextlib
import glob
import hashlib
import http.client
import json
import logging
import logging.handlers
import os
import platform
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

import truststore

# ── Configure aqui ───────────────────────────────────────────────────────────
# Formato: "usuario/nome-do-repositorio"
GITHUB_REPO = "DaviTSelect/gerador-inteligente-documentos"
# ─────────────────────────────────────────────────────────────────────────────

API_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
ARG_VERIFICAR = "--verificar-instalacao"
_USER_AGENT = "GeradorDocumentos-Updater/2.0"
_PASTA_BASE = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(_PASTA_BASE, "version.txt")

# Tipos de máquina do cabeçalho PE aceitos em cada arquitetura do Windows
_MAQUINAS_PE = {
    "AMD64": {0x8664, 0x14C},
    "ARM64": {0xAA64, 0x8664, 0x14C},
    "X86": {0x14C},
}

log = logging.getLogger("atualizador")


class ErroAtualizacao(Exception):
    """Falha com mensagem pronta para ser mostrada ao usuário."""


def caminho_log() -> str:
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return os.path.join(base, "GeradorDocumentos", "atualizador.log")


def configurar_log() -> None:
    if log.handlers:
        return
    try:
        os.makedirs(os.path.dirname(caminho_log()), exist_ok=True)
        saida = logging.handlers.RotatingFileHandler(
            caminho_log(), maxBytes=256 * 1024, backupCount=1, encoding="utf-8"
        )
    except OSError:
        saida = logging.NullHandler()  # sem permissão de escrita: segue sem log
    saida.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(saida)
    log.setLevel(logging.INFO)


# ── Versões ──────────────────────────────────────────────────────────────────

def ler_versao_local() -> str:
    """Retorna a versão do arquivo version.txt (ex: '1.0.0')."""
    try:
        with open(VERSION_FILE, "r", encoding="utf-8-sig") as f:
            return f.read().strip().lstrip("v")
    except FileNotFoundError:
        log.error("version.txt não encontrado em %s", VERSION_FILE)
        return "0.0.0"


def versao_para_tupla(v: str):
    """'v1.10.0' → (1, 10, 0, 0). Retorna None se não for uma versão numérica."""
    m = re.fullmatch(r"[vV]?(\d+(?:\.\d+){0,3})", (v or "").strip())
    if not m:
        return None
    partes = [int(x) for x in m.group(1).split(".")]
    return tuple(partes + [0] * (4 - len(partes)))


def eh_mais_nova(remota: str, local: str) -> bool:
    nova = versao_para_tupla(remota)
    return nova is not None and nova > (versao_para_tupla(local) or (0, 0, 0, 0))


# ── Rede ─────────────────────────────────────────────────────────────────────

def _abrir(url: str, timeout: int, aceitar: str = "*/*"):
    partes = urllib.parse.urlsplit(url)
    local = partes.hostname in ("127.0.0.1", "localhost")
    if partes.scheme != "https" and not local:
        raise ErroAtualizacao("Endereço de download recusado: é obrigatório HTTPS.")

    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Accept": aceitar,
        "Cache-Control": "no-cache",
    })
    try:
        # O Windows valida o certificado: ele busca raízes que ainda não estão
        # instaladas e aceita as que a rede da empresa tiver cadastrado. O
        # OpenSSL sozinho falhava em computadores recém-configurados.
        opcoes = {} if partes.scheme != "https" else {
            "context": truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        }
        resposta = urllib.request.urlopen(req, timeout=timeout, **opcoes)
        if not local and urllib.parse.urlsplit(resposta.geturl()).scheme != "https":
            resposta.close()
            raise ErroAtualizacao("Redirecionamento recusado: é obrigatório HTTPS.")
        return resposta
    except urllib.error.HTTPError as e:
        log.error("HTTP %s em %s", e.code, url)
        if e.code == 429 or (e.code == 403 and e.headers.get("X-RateLimit-Remaining") == "0"):
            reset = e.headers.get("X-RateLimit-Reset")
            quando = time.strftime(" após %H:%M", time.localtime(int(reset))) if reset else " mais tarde"
            raise ErroAtualizacao(f"Limite de consultas do GitHub atingido. Tente{quando}.") from e
        if e.code == 407:
            raise ErroAtualizacao("O proxy da rede exige login (HTTP 407). Fale com o suporte de TI.") from e
        if e.code == 404:
            raise ErroAtualizacao("Repositório ou arquivo não encontrado no GitHub (HTTP 404).") from e
        raise ErroAtualizacao(f"O GitHub respondeu com erro HTTP {e.code}.") from e
    except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
        log.error("Falha de conexão em %s: %r", url, e)
        raise ErroAtualizacao(_motivo_da_falha(e, partes.hostname)) from e


def _motivo_da_falha(erro: Exception, servidor: str) -> str:
    """Traduz a falha de conexão em uma mensagem que indica o que verificar."""
    causa = getattr(erro, "reason", erro)
    texto = str(causa)
    if isinstance(causa, ssl.SSLCertVerificationError):
        return ("O certificado de segurança foi recusado. Confira a data e a hora do "
                "computador; antivírus ou a rede podem estar interceptando a conexão.")
    if isinstance(causa, socket.gaierror):
        return f"O endereço {servidor} não foi encontrado. Verifique a internet."
    if isinstance(causa, TimeoutError) or "timed out" in texto:
        return "A conexão demorou demais. Verifique a internet, o firewall ou o proxy."
    if "Tunnel connection failed" in texto:
        return "O proxy da rede recusou a conexão. Fale com o suporte de TI."
    if isinstance(causa, (ConnectionError, PermissionError)):
        return "Não foi possível conectar. Verifique o firewall e o antivírus deste computador."
    return "Não foi possível conectar ao GitHub. Verifique a internet."


def _baixar_arquivo(url: str, destino: str, callback=None, tamanho_esperado: int = 0):
    """Baixa url → destino e confere se o arquivo chegou inteiro."""
    with _abrir(url, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or tamanho_esperado or 0)
        baixados = 0
        try:
            with open(destino, "wb") as f:
                while True:
                    bloco = resp.read(65536)
                    if not bloco:
                        break
                    f.write(bloco)
                    baixados += len(bloco)
                    if callback:
                        callback(baixados, total)
        except (http.client.HTTPException, ConnectionError, TimeoutError) as e:
            log.error("Download interrompido: %r", e)
            raise ErroAtualizacao("Download incompleto: a conexão caiu.") from e
        except OSError as e:
            log.error("Falha ao gravar o download: %r", e)
            raise ErroAtualizacao("Não foi possível gravar o download (disco cheio?).") from e

    esperado = tamanho_esperado or total
    if esperado and baixados != esperado:
        log.error("Download incompleto: %s de %s bytes", baixados, esperado)
        raise ErroAtualizacao(f"Download incompleto ({baixados} de {esperado} bytes).")


def _listar_releases(timeout: int) -> list:
    url = f"{API_RELEASES_URL}?per_page=100"
    with _abrir(url, timeout, "application/vnd.github+json") as resp:
        try:
            releases = json.loads(resp.read().decode("utf-8"))
        except (ValueError, http.client.HTTPException, OSError) as e:
            log.error("Resposta ilegível da API: %r", e)
            raise ErroAtualizacao("Resposta inesperada do GitHub. Tente novamente.") from e
    if not isinstance(releases, list):
        log.error("Resposta da API não é uma lista: %.200r", releases)
        raise ErroAtualizacao("Resposta inesperada do GitHub. Tente novamente.")
    return releases


# ── Seleção da release e do arquivo ──────────────────────────────────────────

def exe_atual():
    """Caminho do executável em uso, ou None quando rodando pelo código-fonte."""
    return sys.executable if getattr(sys, "frozen", False) else None


def _normalizar(nome: str) -> str:
    return re.sub(r"[^a-z0-9]", "", nome.lower())


def _escolher_asset(assets: list, extensao: str):
    """
    Escolhe o arquivo de atualização sem depender de um nome fixo:
    extensão → descarta instaladores e outras arquiteturas → se sobrar mais
    de um, prefere o nome igual ao do programa instalado.
    """
    candidatos = [
        a for a in assets
        if a.get("name", "").lower().endswith(extensao)
        and a.get("state", "uploaded") == "uploaded"
        and a.get("browser_download_url")
    ]
    if len(candidatos) > 1:
        arm = platform.machine().upper() == "ARM64"
        excluir = r"setup|install|portable-debug" + ("" if arm else r"|arm64|aarch64")
        if sys.maxsize > 2**32:
            excluir += r"|x86(?!_64)|win32|i386"
        candidatos = [a for a in candidatos
                      if not re.search(excluir, a["name"], re.IGNORECASE)] or candidatos
    if len(candidatos) <= 1:
        return candidatos[0] if candidatos else None

    atual = os.path.basename(exe_atual() or "GeradorDocumentos.exe")
    for criterio in (
        lambda n: n.lower() == atual.lower(),
        lambda n: n.lower() == "geradordocumentos.exe",
        lambda n: _normalizar(n).startswith("geradordocumentos"),
    ):
        iguais = [a for a in candidatos if criterio(a["name"])]
        if len(iguais) == 1:
            return iguais[0]
    log.error("Assets ambíguos: %s", [a["name"] for a in candidatos])
    return None


def verificar_atualizacao(timeout: int = 10) -> dict:
    """
    Verifica se há atualização disponível. Nunca levanta exceção.

    Retorna dict com:
        disponivel  : bool
        versao_local: str
        versao_nova : str   (maior versão publicada; "" se não foi possível saber)
        url_download, nome_asset, tamanho, sha256, url_sha256 : dados do arquivo
        notas       : str
        erro        : str   (mensagem para o usuário; "" se deu certo)
    """
    configurar_log()
    info = {"disponivel": False, "versao_local": ler_versao_local(), "versao_nova": "",
            "url_download": "", "nome_asset": "", "tamanho": 0, "sha256": "",
            "url_sha256": "", "notas": "", "erro": ""}
    try:
        _preencher_info(info, timeout)
    except ErroAtualizacao as e:
        info["erro"] = str(e)
    except Exception:
        log.exception("Erro inesperado ao verificar atualização")
        info["erro"] = "Erro inesperado ao verificar atualização (veja o log)."
    log.info("Verificação: local=%s remota=%s disponivel=%s erro=%r",
             info["versao_local"], info["versao_nova"], info["disponivel"], info["erro"])
    return info


def _preencher_info(info: dict, timeout: int) -> None:
    publicadas = []
    for release in _listar_releases(timeout):
        versao = versao_para_tupla(release.get("tag_name", ""))
        if versao and not release.get("draft") and not release.get("prerelease"):
            publicadas.append((versao, release))
    if not publicadas:
        raise ErroAtualizacao("Nenhuma versão publicada foi encontrada no GitHub.")
    publicadas.sort(key=lambda item: item[0], reverse=True)

    maior = publicadas[0][1]["tag_name"].lstrip("vV")
    info["versao_nova"] = maior
    if not eh_mais_nova(maior, info["versao_local"]):
        return

    extensao = ".exe" if exe_atual() else ".zip"
    for _, release in publicadas:
        tag = release["tag_name"].lstrip("vV")
        if not eh_mais_nova(tag, info["versao_local"]):
            break
        assets = release.get("assets") or []
        asset = _escolher_asset(assets, extensao)
        if not asset:
            log.warning("Release %s sem arquivo %s utilizável", tag, extensao)
            continue
        digest = asset.get("digest") or ""
        nome_sha = asset["name"].lower() + ".sha256"
        info.update(
            disponivel=True,
            versao_nova=tag,
            url_download=asset["browser_download_url"],
            nome_asset=asset["name"],
            tamanho=int(asset.get("size") or 0),
            sha256=digest[7:].lower() if digest.startswith("sha256:") else "",
            url_sha256=next((a["browser_download_url"] for a in assets
                             if a.get("name", "").lower() == nome_sha), ""),
            notas=release.get("body") or "",
        )
        return

    if exe_atual():
        raise ErroAtualizacao(f"A versão {maior} foi publicada sem executável compatível.")
    raise ErroAtualizacao(f"Versão {maior} disponível (atualize o código-fonte com git pull).")


# ── Validação ────────────────────────────────────────────────────────────────

def _validar_integridade(caminho: str, info: dict, pasta_tmp: str) -> None:
    """Confere o SHA-256 contra todas as fontes publicadas (API e .sha256)."""
    esperados = [info["sha256"]] if info.get("sha256") else []
    if info.get("url_sha256"):
        arquivo_sha = os.path.join(pasta_tmp, "publicado.sha256")
        _baixar_arquivo(info["url_sha256"], arquivo_sha)
        with open(arquivo_sha, "rb") as f:
            m = re.search(rb"\b[0-9a-fA-F]{64}\b", f.read())
        if not m:
            raise ErroAtualizacao("Arquivo SHA-256 publicado é inválido.")
        esperados.append(m.group(0).decode().lower())

    if not esperados:
        log.warning("Release sem SHA-256 publicado; validado apenas o tamanho")
        return
    soma = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            soma.update(bloco)
    if any(soma.hexdigest() != e for e in esperados):
        log.error("SHA-256 obtido %s, esperado %s", soma.hexdigest(), esperados)
        raise ErroAtualizacao("O arquivo baixado está corrompido (SHA-256 não confere).")


def _validar_pe(caminho: str) -> None:
    """Confere se é um executável Windows compatível com este computador."""
    with open(caminho, "rb") as f:
        inicio = f.read(64)
        if len(inicio) < 64 or inicio[:2] != b"MZ":
            raise ErroAtualizacao("O arquivo baixado não é um executável válido.")
        f.seek(struct.unpack_from("<I", inicio, 0x3C)[0])
        pe = f.read(6)
    if len(pe) < 6 or pe[:4] != b"PE\0\0":
        raise ErroAtualizacao("O arquivo baixado não é um executável válido.")
    maquina = struct.unpack_from("<H", pe, 4)[0]
    if maquina not in _MAQUINAS_PE.get(platform.machine().upper(), {0x8664, 0x14C}):
        raise ErroAtualizacao("O executável baixado é de outra arquitetura.")


def _ambiente_limpo() -> dict:
    """
    Ambiente para iniciar outro .exe do PyInstaller. Sem isto o novo processo
    herda as variáveis do atual, tenta usar a pasta _MEI dele (apagada na
    saída) e falha com "Failed to load Python DLL".
    """
    env = os.environ.copy()
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def _verificar_executavel(caminho: str, versao: str) -> None:
    """Executa o novo .exe em modo de autoverificação (sem abrir janela)."""
    try:
        resultado = subprocess.run(
            [caminho, f"{ARG_VERIFICAR}={versao}"], env=_ambiente_limpo(), timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        log.error("Autoverificação não executou: %r", e)
        raise ErroAtualizacao("A nova versão não pôde ser iniciada (antivírus?).") from e
    if resultado.returncode != 0:
        log.error("Autoverificação retornou %s", resultado.returncode)
        raise ErroAtualizacao("A nova versão falhou na verificação e foi descartada.")


# ── Aplicar atualização ──────────────────────────────────────────────────────

def _renomear(origem: str, destino: str, tentativas: int = 5) -> None:
    """os.replace com novas tentativas (antivírus pode segurar o arquivo)."""
    for tentativa in range(1, tentativas + 1):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa == tentativas:
                raise
            time.sleep(1)


def preparar_atualizacao(info: dict, callback_progresso=None) -> str:
    """
    Baixa e valida a atualização, sem alterar o programa em uso.

    callback_progresso(bytes_baixados, total) chamado durante o download.
    Retorna o caminho do arquivo pronto para instalar_atualizacao().
    """
    configurar_log()
    log.info("Baixando %s (%s)", info["nome_asset"], info["versao_nova"])
    with _erros_amigaveis():
        pasta_tmp = tempfile.mkdtemp(prefix="gerador_update_")
        preparado = ""
        try:
            baixado = os.path.join(pasta_tmp, "download.bin")
            _baixar_arquivo(info["url_download"], baixado, callback_progresso, info["tamanho"])
            _validar_integridade(baixado, info, pasta_tmp)
            if info["nome_asset"].lower().endswith(".zip"):
                preparado = baixado
                return preparado

            _validar_pe(baixado)
            atual = exe_atual()
            if not atual:
                raise ErroAtualizacao("Atualização de .exe só funciona no programa compilado.")
            novo = f"{os.path.splitext(atual)[0]}.novo-{os.getpid()}.exe"
            try:
                shutil.copyfile(baixado, novo)
                _verificar_executavel(novo, info["versao_nova"])
                preparado = novo
            finally:
                if not preparado:
                    _remover(novo)
            return preparado
        finally:
            if os.path.dirname(preparado) != pasta_tmp:
                shutil.rmtree(pasta_tmp, ignore_errors=True)


def instalar_atualizacao(info: dict, preparado: str) -> None:
    """Instala o arquivo de preparar_atualizacao(). Reinicie logo em seguida."""
    with _erros_amigaveis():
        if info["nome_asset"].lower().endswith(".zip"):
            _aplicar_zip(preparado, info["versao_nova"])
            shutil.rmtree(os.path.dirname(preparado), ignore_errors=True)
        else:
            _trocar_exe(preparado)
    log.info("Versão %s instalada", info["versao_nova"])


def aplicar_atualizacao(info: dict, callback_progresso=None) -> None:
    """Baixa, valida e instala. Em caso de erro a versão atual é mantida."""
    instalar_atualizacao(info, preparar_atualizacao(info, callback_progresso))


@contextlib.contextmanager
def _erros_amigaveis():
    try:
        yield
    except ErroAtualizacao as e:
        log.error("Atualização abortada: %s", e)
        raise
    except PermissionError as e:
        log.exception("Sem permissão")
        raise ErroAtualizacao(
            "Sem permissão para substituir o programa. Mova-o para uma pasta "
            "do seu usuário e tente novamente."
        ) from e
    except (OSError, zipfile.BadZipFile) as e:
        log.exception("Falha ao instalar")
        raise ErroAtualizacao(f"Falha ao substituir os arquivos: {e}") from e


def _trocar_exe(novo: str) -> None:
    """
    Troca o executável em uso. O Windows permite renomear um .exe em execução
    (mas não sobrescrevê-lo), então não é preciso script externo.
    """
    atual = exe_atual()
    backup = f"{atual}.{os.getpid()}.old"
    try:
        _renomear(atual, backup)
        try:
            _renomear(novo, atual)
        except OSError:
            log.exception("Falha ao promover o novo executável; restaurando")
            _restaurar(backup, atual)
            raise
    finally:
        if os.path.exists(atual):
            _remover(novo)


def _restaurar(backup: str, atual: str) -> None:
    """Devolve o executável antigo ao nome original (rename ou, em último caso, cópia)."""
    try:
        _renomear(backup, atual)
        return
    except OSError:
        log.exception("Rename de restauração falhou; tentando copiar")
    try:
        shutil.copyfile(backup, atual)
    except OSError as e:
        log.critical("Não foi possível restaurar %s a partir de %s", atual, backup)
        raise ErroAtualizacao(
            f"Falha na atualização. Renomeie '{os.path.basename(backup)}' para "
            f"'{os.path.basename(atual)}' na pasta do programa."
        ) from e


def _aplicar_zip(caminho_zip: str, versao_nova: str) -> None:
    """Extrai o ZIP sobre o código-fonte (modo desenvolvimento)."""
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
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(versao_nova + "\n")


def _remover(caminho: str) -> None:
    try:
        os.remove(caminho)
    except FileNotFoundError:
        pass
    except OSError as e:
        log.info("Não foi possível apagar %s agora: %s", caminho, e)


def limpar_residuos() -> None:
    """Apaga sobras de atualizações anteriores. Chamado na abertura do app."""
    atual = exe_atual()
    if not atual:
        return
    exato = glob.escape(atual)
    base = glob.escape(os.path.splitext(atual)[0])
    for padrao in (exato + ".old", exato + ".*.old", exato + ".new", base + ".novo-*.exe"):
        for sobra in glob.glob(padrao):
            _remover(sobra)


# ── Reinício ──────────────────────────────────────────────────────────────────

def reiniciar() -> None:
    """Inicia a versão recém-instalada. O chamador deve encerrar o app em seguida."""
    comando = [sys.executable] if exe_atual() else [sys.executable] + sys.argv
    log.info("Reiniciando: %s", comando)
    subprocess.Popen(comando, env=_ambiente_limpo())
