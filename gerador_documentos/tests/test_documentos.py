"""
Testes para documentos.py
Rodados com: pytest tests/test_documentos.py -v
"""
import os
import shutil
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from docx import Document
from documentos import extrair_variaveis, gerar_documento

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures_docs")


@pytest.fixture(scope="module", autouse=True)
def criar_templates():
    """Cria templates de teste antes dos testes e limpa depois."""
    os.makedirs(FIXTURES, exist_ok=True)

    # Template simples com variáveis em parágrafo e tabela
    doc = Document()
    doc.add_paragraph("Contrato de {{NOME}}, CPF {{CPF}}, admitido em {{DATA}}.")
    tabela = doc.add_table(rows=1, cols=2)
    tabela.cell(0, 0).text = "Cargo: {{CARGO}}"
    tabela.cell(0, 1).text = "Salário: {{SALARIO}}"
    doc.save(os.path.join(FIXTURES, "template_simples.docx"))

    # Template com variável no cabeçalho
    doc2 = Document()
    doc2.add_paragraph("Documento principal {{NOME}}.")
    section = doc2.sections[0]
    header = section.header
    header.paragraphs[0].text = "Empresa {{EMPRESA}} — Confidencial"
    doc2.save(os.path.join(FIXTURES, "template_header.docx"))

    # Template com variável dividida em múltiplos runs (simulando formatação parcial)
    # python-docx não divide automaticamente, mas podemos testar substituição normal
    doc3 = Document()
    p = doc3.add_paragraph()
    p.add_run("Prezado(a) ")
    p.add_run("{{NOME}}")
    p.add_run(", bem-vindo!")
    doc3.save(os.path.join(FIXTURES, "template_runs.docx"))

    yield

    shutil.rmtree(FIXTURES, ignore_errors=True)


# ── extrair_variaveis ────────────────────────────────────────────────────────

class TestExtrairVariaveis:
    def test_variaveis_em_paragrafo(self):
        caminho = os.path.join(FIXTURES, "template_simples.docx")
        variaveis = extrair_variaveis(caminho)
        assert "NOME" in variaveis
        assert "CPF" in variaveis
        assert "DATA" in variaveis

    def test_variaveis_em_tabela(self):
        caminho = os.path.join(FIXTURES, "template_simples.docx")
        variaveis = extrair_variaveis(caminho)
        assert "CARGO" in variaveis
        assert "SALARIO" in variaveis

    def test_variaveis_em_header(self):
        caminho = os.path.join(FIXTURES, "template_header.docx")
        variaveis = extrair_variaveis(caminho)
        assert "EMPRESA" in variaveis

    def test_sem_duplicatas(self):
        caminho = os.path.join(FIXTURES, "template_simples.docx")
        variaveis = extrair_variaveis(caminho)
        assert len(variaveis) == len(set(variaveis))

    def test_retorna_lista(self):
        caminho = os.path.join(FIXTURES, "template_simples.docx")
        resultado = extrair_variaveis(caminho)
        assert isinstance(resultado, list)


# ── gerar_documento ──────────────────────────────────────────────────────────

class TestGerarDocumento:
    def test_substitui_valores_no_paragrafo(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_paragrafo.docx")
        dados = {
            "NOME": "Ana Silva",
            "CPF": "123.456.789-00",
            "DATA": "04/11/2026",
            "CARGO": "Analista",
            "SALARIO": "R$ 4.500,00"
        }
        gerar_documento(template, dados, saida)
        doc = Document(saida)
        texto = " ".join(p.text for p in doc.paragraphs)
        assert "Ana Silva" in texto
        assert "123.456.789-00" in texto

    def test_remove_marcadores_do_template(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_sem_marcadores.docx")
        dados = {"NOME": "João", "CPF": "111", "DATA": "01/01/2026",
                 "CARGO": "Dev", "SALARIO": "5000"}
        gerar_documento(template, dados, saida)
        doc = Document(saida)
        texto = " ".join(p.text for p in doc.paragraphs)
        assert "{{NOME}}" not in texto
        assert "{{CPF}}" not in texto

    def test_substitui_em_tabela(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_tabela.docx")
        dados = {"NOME": "X", "CPF": "X", "DATA": "X",
                 "CARGO": "Gerente", "SALARIO": "R$ 10.000,00"}
        gerar_documento(template, dados, saida)
        doc = Document(saida)
        texto_tabela = ""
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    texto_tabela += cell.text
        assert "Gerente" in texto_tabela

    def test_nao_modifica_template_original(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        mtime_antes = os.path.getmtime(template)
        saida = os.path.join(FIXTURES, "saida_mtime.docx")
        dados = {"NOME": "X", "CPF": "X", "DATA": "X", "CARGO": "X", "SALARIO": "X"}
        gerar_documento(template, dados, saida)
        assert os.path.getmtime(template) == mtime_antes

    def test_sufixo_quando_arquivo_ja_existe(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_sufixo.docx")
        dados = {"NOME": "A", "CPF": "A", "DATA": "A", "CARGO": "A", "SALARIO": "A"}
        # Primeira geração
        saida1 = gerar_documento(template, dados, saida)
        # Segunda geração com mesmo destino
        saida2 = gerar_documento(template, dados, saida)
        assert saida2 != saida1
        assert os.path.exists(saida2)

    def test_substitui_em_runs_separados(self):
        template = os.path.join(FIXTURES, "template_runs.docx")
        saida = os.path.join(FIXTURES, "saida_runs.docx")
        dados = {"NOME": "Carlos"}
        gerar_documento(template, dados, saida)
        doc = Document(saida)
        texto = " ".join(p.text for p in doc.paragraphs)
        assert "Carlos" in texto
        assert "{{NOME}}" not in texto

    def test_variavel_nao_mapeada_vira_vazio(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_vazio.docx")
        # Não mapeia CARGO e SALARIO
        dados = {"NOME": "Ana", "CPF": "123", "DATA": "01/01/2026"}
        gerar_documento(template, dados, saida)
        doc = Document(saida)
        texto_completo = " ".join(p.text for p in doc.paragraphs)
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    texto_completo += cell.text
        # Variáveis não mapeadas viram string vazia, não ficam como {{VAR}}
        assert "{{CARGO}}" not in texto_completo
        assert "{{SALARIO}}" not in texto_completo

    def test_retorna_caminho_do_arquivo_salvo(self):
        template = os.path.join(FIXTURES, "template_simples.docx")
        saida = os.path.join(FIXTURES, "saida_retorno.docx")
        dados = {"NOME": "X", "CPF": "X", "DATA": "X", "CARGO": "X", "SALARIO": "X"}
        resultado = gerar_documento(template, dados, saida)
        assert isinstance(resultado, str)
        assert os.path.exists(resultado)
