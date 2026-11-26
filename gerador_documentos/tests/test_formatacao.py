"""
Testes de preservação de formatação: o valor deve herdar exatamente a
formatação do marcador {{CAMPO}} e o restante do parágrafo não pode mudar.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from lxml import etree

from documentos import extrair_variaveis, gerar_documento


def _gerar(tmp_path, doc, dados):
    template = str(tmp_path / "template.docx")
    doc.save(template)
    return Document(gerar_documento(template, dados, str(tmp_path / "saida.docx")))


def _formatacao_por_caractere(paragrafo):
    """[(caractere, rPr em XML)] — compara formatação independente da divisão em runs."""
    resultado = []
    for r in paragrafo._p.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        chave = b"" if rpr is None else etree.tostring(rpr, method="c14n")
        for t in r.findall(qn("w:t")):
            resultado.extend((c, chave) for c in (t.text or ""))
    return resultado


def _run_com(paragrafo, texto):
    return next(r for r in paragrafo.runs if texto in r.text)


def test_marcador_negrito_continua_negrito_e_vizinhos_nao_mudam(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Contratado: ")
    p.add_run("{{NOME}}").bold = True
    p.add_run(", residente.")
    saida = _gerar(tmp_path, doc, {"NOME": "João da Silva"}).paragraphs[0]

    assert saida.text == "Contratado: João da Silva, residente."
    assert _run_com(saida, "João da Silva").bold is True
    assert not _run_com(saida, "Contratado").bold
    assert not _run_com(saida, "residente").bold


def test_valor_nao_herda_negrito_do_inicio_do_paragrafo(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Valor total: ").bold = True
    p.add_run("{{VALOR}}")
    saida = _gerar(tmp_path, doc, {"VALOR": "R$ 1.500,00"}).paragraphs[0]

    assert not _run_com(saida, "R$ 1.500,00").bold
    assert _run_com(saida, "Valor total").bold is True


def test_marcador_dividido_em_varios_runs(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("Eu, ")
    for parte in ["{", "{NO", "ME", "}", "}"]:
        p.add_run(parte).italic = True
    p.add_run(" declaro ")
    p.add_run("CONTRATADO").bold = True
    saida = _gerar(tmp_path, doc, {"NOME": "Maria"}).paragraphs[0]

    assert saida.text == "Eu, Maria declaro CONTRATADO"
    assert _run_com(saida, "Maria").italic is True
    assert not _run_com(saida, "Eu, ").italic
    assert _run_com(saida, "CONTRATADO").bold is True


def test_chaves_sem_formatacao_usam_a_formatacao_do_nome(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("{{")
    p.add_run("NOME").bold = True
    p.add_run("}}")
    saida = _gerar(tmp_path, doc, {"NOME": "Ana"}).paragraphs[0]

    assert _run_com(saida, "Ana").bold is True


def test_preserva_fonte_tamanho_cor_sublinhado_e_alinhamento(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("{{CPF}}")
    r.font.name = "Courier New"
    r.font.size = Pt(17)
    r.font.color.rgb = RGBColor(0x12, 0x34, 0x56)
    r.underline = True
    saida = _gerar(tmp_path, doc, {"CPF": "123.456.789-00"}).paragraphs[0]

    run = _run_com(saida, "123.456.789-00")
    assert run.font.name == "Courier New"
    assert run.font.size == Pt(17)
    assert run.font.color.rgb == RGBColor(0x12, 0x34, 0x56)
    assert run.underline is True
    assert saida.alignment == WD_ALIGN_PARAGRAPH.CENTER


def test_marcador_repetido_e_varios_no_mesmo_paragrafo(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("{{NOME}}").bold = True
    p.add_run(" e {{NOME}} paga {{VALOR}}")
    doc.add_paragraph("Assina: {{NOME}}")
    saida = _gerar(tmp_path, doc, {"NOME": "Ana", "VALOR": "R$ 1,00"})

    assert saida.paragraphs[0].text == "Ana e Ana paga R$ 1,00"
    assert saida.paragraphs[1].text == "Assina: Ana"
    assert saida.paragraphs[0].runs[0].bold is True
    assert not saida.paragraphs[0].runs[1].bold


def test_marcador_em_tabela_aninhada_cabecalho_e_rodape(tmp_path):
    doc = Document()
    celula = doc.add_table(rows=1, cols=1).cell(0, 0)
    celula.paragraphs[0].add_run("{{NOME}}").bold = True
    interna = celula.add_table(rows=1, cols=1)
    interna.cell(0, 0).text = "{{CPF}}"
    secao = doc.sections[0]
    secao.header.paragraphs[0].add_run("{{EMPRESA}}").italic = True
    secao.different_first_page_header_footer = True
    secao.first_page_footer.paragraphs[0].text = "{{RODAPE}}"
    dados = {"NOME": "Ana", "CPF": "111", "EMPRESA": "Facto", "RODAPE": "fim"}

    template = str(tmp_path / "t.docx")
    doc.save(template)
    assert set(extrair_variaveis(template)) == set(dados)

    saida = Document(gerar_documento(template, dados, str(tmp_path / "s.docx")))
    celula = saida.tables[0].cell(0, 0)
    assert celula.paragraphs[0].runs[0].text == "Ana"
    assert celula.paragraphs[0].runs[0].bold is True
    assert celula.tables[0].cell(0, 0).text == "111"
    assert saida.sections[0].header.paragraphs[0].runs[0].italic is True
    assert saida.sections[0].header.paragraphs[0].text == "Facto"
    assert saida.sections[0].first_page_footer.paragraphs[0].text == "fim"


def test_marcador_dentro_de_hyperlink(tmp_path):
    doc = Document()
    p = doc.add_paragraph("Site: ")
    link = etree.SubElement(p._p, qn("w:hyperlink"))
    link.set(qn("w:anchor"), "x")
    r = etree.SubElement(link, qn("w:r"))
    etree.SubElement(r, qn("w:t")).text = "{{SITE}}"
    saida = _gerar(tmp_path, doc, {"SITE": "facto.org.br"})

    textos = [t.text for t in saida.element.body.iter(qn("w:t"))]
    assert "facto.org.br" in textos


def test_nomes_com_espacos_e_acentos(tmp_path):
    doc = Document()
    doc.add_paragraph("{{ ENDEREÇO }} / {{Nome do Aluno}}")
    template = str(tmp_path / "t.docx")
    doc.save(template)
    assert extrair_variaveis(template) == ["ENDEREÇO", "Nome do Aluno"]

    saida = gerar_documento(
        template, {"ENDEREÇO": "Rua A", "Nome do Aluno": "Bia"}, str(tmp_path / "s.docx")
    )
    assert Document(saida).paragraphs[0].text == "Rua A / Bia"


def test_valor_com_quebra_de_linha_e_caractere_invalido(tmp_path):
    doc = Document()
    doc.add_paragraph().add_run("a {{X}} b").bold = True
    saida = _gerar(tmp_path, doc, {"X": "linha1\nlinha2\x00"}).paragraphs[0]

    assert saida.text == "a linha1\nlinha2 b"
    assert all(r.bold for r in saida.runs)


def test_template_original_nao_e_alterado_e_restante_fica_identico(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    p.add_run("A ").bold = True
    p.add_run("{{N}}").italic = True
    p.add_run(" B").underline = True
    template = str(tmp_path / "t.docx")
    doc.save(template)
    antes = open(template, "rb").read()

    saida = Document(gerar_documento(template, {"N": "zz"}, str(tmp_path / "s.docx")))

    assert open(template, "rb").read() == antes
    original = _formatacao_por_caractere(Document(template).paragraphs[0])
    gerado = _formatacao_por_caractere(saida.paragraphs[0])
    assert gerado[:2] == original[:2]
    assert gerado[-2:] == original[-2:]
