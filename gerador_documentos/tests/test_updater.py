"""
Testes do atualizador contra um servidor HTTP local (respostas controladas).
Servem para os cenários de falha; a consulta ao GitHub real é verificada à parte.
"""
import hashlib
import json
import os
import struct
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import updater
from updater import ErroAtualizacao


def _pe(maquina=0x8664, extra=b"x" * 4000) -> bytes:
    """Cabeçalho PE mínimo (não executável), suficiente para a validação."""
    cab = bytearray(b"MZ" + b"\0" * 126)
    struct.pack_into("<I", cab, 0x3C, 128)
    return bytes(cab) + b"PE\0\0" + struct.pack("<H", maquina) + extra


class Servidor:
    def __init__(self):
        self.rotas = {}  # caminho → (status, corpo, cabeçalhos)
        servidor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                status, corpo, cab = servidor.rotas.get(
                    self.path.split("?")[0], (404, b"{}", {})
                )
                self.send_response(status)
                cab = {"Content-Length": str(len(corpo)), **cab}
                for nome, valor in cab.items():
                    self.send_header(nome, valor)
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(self, *args):
                pass

        self.http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.http.server_address[1]}"
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def asset(self, nome, conteudo, digest=True):
        self.rotas[f"/dl/{nome}"] = (200, conteudo, {})
        dados = {"name": nome, "size": len(conteudo), "state": "uploaded",
                 "browser_download_url": f"{self.base}/dl/{nome}"}
        if digest:
            dados["digest"] = "sha256:" + hashlib.sha256(conteudo).hexdigest()
        return dados

    def releases(self, *lista):
        self.rotas["/releases"] = (200, json.dumps(list(lista)).encode(), {})


def _release(tag, assets, **extra):
    return {"tag_name": tag, "assets": assets, "draft": False,
            "prerelease": False, "body": "", **extra}


@pytest.fixture
def servidor(monkeypatch):
    s = Servidor()
    monkeypatch.setattr(updater, "API_RELEASES_URL", f"{s.base}/releases")
    monkeypatch.setattr(updater, "ler_versao_local", lambda: "1.9.0")
    yield s
    s.http.shutdown()


@pytest.fixture
def instalado(tmp_path, monkeypatch):
    """Simula o app compilado, instalado numa pasta com espaço e acentos."""
    pasta = tmp_path / "Área de Trabalho (cópia) %teste%"
    pasta.mkdir()
    exe = pasta / "GeradorDocumentos.exe"
    exe.write_bytes(b"VERSAO ANTIGA")
    monkeypatch.setattr(updater, "exe_atual", lambda: str(exe))
    monkeypatch.setattr(updater, "_verificar_executavel", lambda caminho, versao: None)
    return exe


def test_comparacao_numerica_de_versoes():
    assert updater.eh_mais_nova("1.10.0", "1.9.0")
    assert not updater.eh_mais_nova("1.9.0", "1.10.0")
    assert not updater.eh_mais_nova("v1.2", "1.2.0")
    assert updater.eh_mais_nova("1.2.0.1", "1.2")
    assert updater.versao_para_tupla("nightly") is None


def test_programa_atualizado(servidor, instalado):
    servidor.releases(_release("v1.9.0", [servidor.asset("A.exe", _pe())]))
    info = updater.verificar_atualizacao()
    assert info["disponivel"] is False and info["erro"] == ""
    assert info["versao_nova"] == "1.9.0"


def test_escolhe_maior_versao_ignorando_draft_prerelease_e_ordem(servidor, instalado):
    exe = servidor.asset("GeradorDocumentos.exe", _pe())
    servidor.releases(
        _release("v1.9.1", [exe]),
        _release("v3.0.0", [exe], draft=True),
        _release("v2.0.0", [exe], prerelease=True),
        _release("v1.10.0", [exe]),
        _release("lixo", [exe]),
    )
    info = updater.verificar_atualizacao()
    assert info["disponivel"] and info["versao_nova"] == "1.10.0"


def test_asset_com_nome_diferente_e_varios_exes(servidor, instalado):
    servidor.releases(_release("v2.0.0", [
        servidor.asset("Setup-GeradorDocumentos.exe", _pe()),
        servidor.asset("GeradorDocumentos-arm64.exe", _pe(0xAA64)),
        servidor.asset("GeradorDocumentos-2.0.0-win64.exe", _pe()),
        servidor.asset("notas.zip", b"zip"),
    ]))
    info = updater.verificar_atualizacao()
    assert info["nome_asset"] == "GeradorDocumentos-2.0.0-win64.exe"


def test_release_sem_executavel_usa_a_anterior_que_tem(servidor, instalado):
    servidor.releases(
        _release("v2.1.0", []),
        _release("v2.0.0", [servidor.asset("GeradorDocumentos.exe", _pe())]),
    )
    assert updater.verificar_atualizacao()["versao_nova"] == "2.0.0"


def test_asset_inexistente_gera_mensagem(servidor, instalado):
    servidor.releases(_release("v2.0.0", []))
    info = updater.verificar_atualizacao()
    assert info["disponivel"] is False
    assert "sem executável" in info["erro"]


@pytest.mark.parametrize("status,cab,trecho", [
    (403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1900000000"}, "Limite"),
    (404, {}, "não encontrado"),
    (500, {}, "HTTP 500"),
])
def test_erros_da_api(servidor, instalado, status, cab, trecho):
    servidor.rotas["/releases"] = (status, b"{}", cab)
    assert trecho in updater.verificar_atualizacao()["erro"]


def test_resposta_inesperada(servidor, instalado):
    servidor.rotas["/releases"] = (200, b"<html>proxy</html>", {})
    assert "inesperada" in updater.verificar_atualizacao()["erro"]


def test_falha_de_conexao_e_nova_tentativa(servidor, instalado, monkeypatch):
    url_boa = updater.API_RELEASES_URL
    monkeypatch.setattr(updater, "API_RELEASES_URL", "http://127.0.0.1:1/releases")
    assert "conectar" in updater.verificar_atualizacao()["erro"]

    monkeypatch.setattr(updater, "API_RELEASES_URL", url_boa)
    servidor.releases(_release("v2.0.0", [servidor.asset("G.exe", _pe())]))
    assert updater.verificar_atualizacao()["disponivel"]


def _info_para(servidor, conteudo, **kw):
    servidor.releases(_release("v2.0.0", [servidor.asset("GeradorDocumentos.exe", conteudo, **kw)]))
    return updater.verificar_atualizacao()


def _assert_intacto(exe):
    assert exe.read_bytes() == b"VERSAO ANTIGA"
    assert os.listdir(exe.parent) == [exe.name]


def test_atualizacao_completa_substitui_e_guarda_backup(servidor, instalado):
    novo = _pe()
    updater.aplicar_atualizacao(_info_para(servidor, novo))
    assert instalado.read_bytes() == novo
    backups = [n for n in os.listdir(instalado.parent) if n.endswith(".old")]
    assert len(backups) == 1
    updater.limpar_residuos()
    assert os.listdir(instalado.parent) == [instalado.name]


def test_download_interrompido_nao_toca_no_exe(servidor, instalado):
    info = _info_para(servidor, _pe())
    corpo = _pe()
    servidor.rotas["/dl/GeradorDocumentos.exe"] = (
        200, corpo[:1000], {"Content-Length": str(len(corpo))}
    )
    with pytest.raises(ErroAtualizacao, match="incompleto"):
        updater.aplicar_atualizacao(info)
    _assert_intacto(instalado)

    # nova tentativa com o servidor normalizado
    servidor.rotas["/dl/GeradorDocumentos.exe"] = (200, corpo, {})
    updater.aplicar_atualizacao(info)
    assert instalado.read_bytes() == corpo


def test_hash_divergente(servidor, instalado):
    info = _info_para(servidor, _pe())
    servidor.rotas["/dl/GeradorDocumentos.exe"] = (200, _pe(extra=b"y" * 4000), {})
    with pytest.raises(ErroAtualizacao, match="SHA-256"):
        updater.aplicar_atualizacao(info)
    _assert_intacto(instalado)


def test_hash_publicado_em_arquivo_sha256(servidor, instalado):
    exe = servidor.asset("GeradorDocumentos.exe", _pe(), digest=False)
    sha = servidor.asset("GeradorDocumentos.exe.sha256",
                         b"0" * 64 + b"  GeradorDocumentos.exe\r\n", digest=False)
    servidor.releases(_release("v2.0.0", [exe, sha]))
    with pytest.raises(ErroAtualizacao, match="SHA-256"):
        updater.aplicar_atualizacao(updater.verificar_atualizacao())
    _assert_intacto(instalado)


@pytest.mark.parametrize("conteudo", [b"<html>erro</html>", _pe(0xAA64)])
def test_arquivo_invalido_ou_arquitetura_errada(servidor, instalado, conteudo, monkeypatch):
    monkeypatch.setattr(updater.platform, "machine", lambda: "AMD64")
    with pytest.raises(ErroAtualizacao):
        updater.aplicar_atualizacao(_info_para(servidor, conteudo))
    _assert_intacto(instalado)


def test_falha_na_substituicao_restaura_o_original(servidor, instalado, monkeypatch):
    info = _info_para(servidor, _pe())
    real = os.replace

    def falha_ao_promover(origem, destino):
        if ".novo-" in str(origem):
            raise PermissionError("bloqueado")
        real(origem, destino)

    monkeypatch.setattr(updater.os, "replace", falha_ao_promover)
    monkeypatch.setattr(updater.time, "sleep", lambda s: None)
    with pytest.raises(ErroAtualizacao, match="substituir"):
        updater.aplicar_atualizacao(info)
    _assert_intacto(instalado)


def test_executavel_que_nao_inicia_e_rejeitado(servidor, instalado, monkeypatch):
    def falha(caminho, versao):
        raise ErroAtualizacao("A nova versão não abre")

    info = _info_para(servidor, _pe())
    monkeypatch.setattr(updater, "_verificar_executavel", falha)
    with pytest.raises(ErroAtualizacao, match="não abre"):
        updater.aplicar_atualizacao(info)
    _assert_intacto(instalado)


def test_url_http_externa_e_recusada(tmp_path):
    with pytest.raises(ErroAtualizacao, match="HTTPS"):
        updater._baixar_arquivo("http://exemplo.invalid/a.exe", str(tmp_path / "a"))


def test_reinicio_limpa_ambiente_do_pyinstaller():
    assert updater._ambiente_limpo()["PYINSTALLER_RESET_ENVIRONMENT"] == "1"


def test_falha_dupla_na_troca_ainda_deixa_um_exe(servidor, instalado, monkeypatch):
    info = _info_para(servidor, _pe())
    real = os.replace

    def so_o_primeiro_rename(origem, destino):
        if str(origem) != str(instalado):
            raise PermissionError("bloqueado")
        real(origem, destino)

    monkeypatch.setattr(updater.os, "replace", so_o_primeiro_rename)
    monkeypatch.setattr(updater.time, "sleep", lambda s: None)
    with pytest.raises(ErroAtualizacao):
        updater.aplicar_atualizacao(info)
    assert instalado.read_bytes() == b"VERSAO ANTIGA"


def test_preparar_nao_altera_o_programa(servidor, instalado):
    novo = _pe()
    info = _info_para(servidor, novo)
    preparado = updater.preparar_atualizacao(info)
    assert instalado.read_bytes() == b"VERSAO ANTIGA"
    updater.instalar_atualizacao(info, preparado)
    assert instalado.read_bytes() == novo


def test_autoverificacao_rejeita_versao_diferente_da_release():
    import main
    from PySide6.QtWidgets import QApplication

    original = main.QApplication
    main.QApplication = lambda argv: QApplication.instance() or original([])
    try:
        local = updater.ler_versao_local()
        assert main._verificar_instalacao(local) == 0
        assert main._verificar_instalacao("99.0.0") == 1
    finally:
        main.QApplication = original
