"""
Testes para pdf.py
Rodados com: pytest tests/test_pdf.py -v

Nota: o teste de conversão real é ignorado se Word não estiver instalado.
"""
import os
import shutil
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from docx import Document
from pdf import converter_para_pdf, converter_em_lote

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures_pdf")

# Detectar se Word está disponível (docx2pdf requer Word no Windows)
try:
    import docx2pdf
    WORD_DISPONIVEL = True
except Exception:
    WORD_DISPONIVEL = False


@pytest.fixture(scope="module", autouse=True)
def preparar():
    os.makedirs(FIXTURES, exist_ok=True)
    doc = Document()
    doc.add_paragraph("Documento de teste para conversão PDF.")
    doc.save(os.path.join(FIXTURES, "teste.docx"))
    doc2 = Document()
    doc2.add_paragraph("Segundo documento de teste.")
    doc2.save(os.path.join(FIXTURES, "teste2.docx"))
    yield
    shutil.rmtree(FIXTURES, ignore_errors=True)


@pytest.mark.skipif(not WORD_DISPONIVEL, reason="docx2pdf não disponível")
def test_converte_para_pdf_cria_arquivo():
    caminho_docx = os.path.join(FIXTURES, "teste.docx")
    caminho_pdf = converter_para_pdf(caminho_docx)
    assert caminho_pdf.endswith(".pdf")
    assert os.path.exists(caminho_pdf)


@pytest.mark.skipif(not WORD_DISPONIVEL, reason="docx2pdf não disponível")
def test_converter_em_lote_retorna_lista():
    docx1 = os.path.join(FIXTURES, "teste.docx")
    docx2 = os.path.join(FIXTURES, "teste2.docx")
    gerados = converter_em_lote([docx1, docx2])
    assert len(gerados) == 2
    for caminho in gerados:
        assert caminho.endswith(".pdf")
        assert os.path.exists(caminho)


@pytest.mark.skipif(not WORD_DISPONIVEL, reason="docx2pdf não disponível")
def test_converter_em_lote_chama_callback():
    docx1 = os.path.join(FIXTURES, "teste.docx")
    chamadas = []
    converter_em_lote([docx1], callback=lambda atual, total, nome: chamadas.append((atual, total, nome)))
    assert len(chamadas) == 1
    assert chamadas[0][0] == 1
    assert chamadas[0][1] == 1


def test_converter_para_pdf_arquivo_inexistente_levanta_erro():
    """Arquivo que não existe deve levantar erro claro."""
    with pytest.raises(Exception):
        converter_para_pdf("/caminho/que/nao/existe.docx")


def test_modulo_importa_sem_erro():
    """O módulo pdf.py deve importar mesmo sem Word instalado."""
    import pdf  # noqa: F401
    assert hasattr(pdf, "converter_para_pdf")
    assert hasattr(pdf, "converter_em_lote")
