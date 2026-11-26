"""
Falhas passageiras do Word durante a conversão para PDF.

O Word é substituído por um dublê: não há como provocar essas falhas
de propósito no programa real.
"""
import sys
import types

import pytest

import pdf


class _WordFalso:
    def __init__(self, roteiro):
        self.roteiro = roteiro
        self.Documents = self
        self.Visible = True

    def Open(self, caminho):
        if self.roteiro.get("abrir_falha", 0) > 0:
            self.roteiro["abrir_falha"] -= 1
            raise AttributeError("Open.SaveAs")
        return self

    def SaveAs(self, destino, FileFormat):
        with open(destino, "wb") as f:
            f.write(b"%PDF-1.7")

    def Close(self, salvar):
        if self.roteiro.get("fechar_falha"):
            raise AttributeError("Open.Close")

    def Quit(self):
        self.roteiro["encerramentos"] = self.roteiro.get("encerramentos", 0) + 1
        if self.roteiro.get("sair_falha"):
            raise AttributeError("Word.Application.Quit")


@pytest.fixture
def word(monkeypatch, tmp_path):
    roteiro = {}
    cliente = types.ModuleType("win32com.client")
    cliente.DispatchEx = lambda nome: _WordFalso(roteiro)
    pacote = types.ModuleType("win32com")
    pacote.client = cliente
    monkeypatch.setitem(sys.modules, "win32com", pacote)
    monkeypatch.setitem(sys.modules, "win32com.client", cliente)
    monkeypatch.setattr(pdf, "ESPERA_ENTRE_TENTATIVAS", 0, raising=False)
    docx = tmp_path / "contrato.docx"
    docx.write_bytes(b"x")
    return roteiro, str(docx)


def test_falha_passageira_e_tentada_de_novo(word):
    roteiro, docx = word
    roteiro["abrir_falha"] = 1
    assert pdf.converter_para_pdf(docx).endswith("contrato.pdf")
    assert roteiro["encerramentos"] == 2


def test_falha_ao_fechar_o_word_nao_descarta_pdf_pronto(word):
    roteiro, docx = word
    roteiro["fechar_falha"] = roteiro["sair_falha"] = True
    assert pdf.converter_para_pdf(docx).endswith("contrato.pdf")
    assert roteiro["encerramentos"] == 1


def test_falha_persistente_e_informada(word):
    roteiro, docx = word
    roteiro["abrir_falha"] = 99
    roteiro["sair_falha"] = True
    with pytest.raises(RuntimeError, match="Open.SaveAs"):
        pdf.converter_para_pdf(docx)
    assert roteiro["encerramentos"] == 3
