"""
Conexão do atualizador: certificados validados pelo Windows e mensagens que
dizem o motivo da falha. As falhas de rede são provocadas substituindo
urlopen, porque não há como reproduzi-las de propósito.
"""
import socket
import ssl
import urllib.error

import pytest
import truststore

import updater

URL = "https://api.github.com/repos/x/y/releases"


def _mensagem(monkeypatch, erro) -> str:
    def falhar(*args, **kwargs):
        raise erro

    monkeypatch.setattr(updater.urllib.request, "urlopen", falhar)
    with pytest.raises(updater.ErroAtualizacao) as capturado:
        updater._abrir(URL, 5)
    return str(capturado.value)


def test_https_usa_a_validacao_do_windows_sem_desligar_a_verificacao(monkeypatch):
    usados = {}

    class Resposta:
        def geturl(self):
            return URL

    def urlopen(req, timeout, context=None):
        usados["contexto"] = context
        return Resposta()

    monkeypatch.setattr(updater.urllib.request, "urlopen", urlopen)
    updater._abrir(URL, 5)

    contexto = usados["contexto"]
    assert isinstance(contexto, truststore.SSLContext)
    assert contexto.verify_mode == ssl.CERT_REQUIRED
    assert contexto.check_hostname is True


@pytest.mark.parametrize("erro, trecho", [
    (urllib.error.URLError(ssl.SSLCertVerificationError("unable to get local issuer")),
     "certificado"),
    (urllib.error.URLError(socket.gaierror(11001, "getaddrinfo failed")), "api.github.com"),
    (urllib.error.URLError(TimeoutError("timed out")), "demorou"),
    (TimeoutError("timed out"), "demorou"),
    (urllib.error.URLError(ConnectionRefusedError(10061, "recusada")), "firewall"),
    (urllib.error.URLError(OSError("Tunnel connection failed: 407 Proxy Auth")), "proxy"),
    (urllib.error.HTTPError(URL, 407, "Proxy Authentication Required", {}, None), "proxy"),
])
def test_mensagem_diz_o_motivo(monkeypatch, erro, trecho):
    assert trecho in _mensagem(monkeypatch, erro).lower()
