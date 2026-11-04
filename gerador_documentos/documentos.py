"""
documentos.py — Leitura de templates Word e geração de documentos preenchidos.

Responsabilidade: abrir um .docx template, encontrar variáveis {{VAR}},
substituí-las pelos valores fornecidos e salvar o resultado sem modificar
o template original.

Problema importante: o Word frequentemente divide o texto de uma variável
em múltiplos "runs" (fragmentos XML) por causa da formatação. Por exemplo,
"{{NOME}}" pode estar armazenado como ["{{", "NOM", "E}}"] em três runs
separados. A função _colapsar_runs resolve isso antes de substituir.
"""
import os
import re
import shutil

from docx import Document
from docx.oxml.ns import qn

# Padrão que detecta variáveis no formato {{NOME_DA_VARIAVEL}}
PADRAO_VARIAVEL = re.compile(r"\{\{([A-Za-z_0-9]+)\}\}")


# ── Funções internas ─────────────────────────────────────────────────────────

def _texto_do_paragrafo(paragrafo) -> str:
    """Junta todos os runs de um parágrafo em uma string única."""
    return "".join(run.text for run in paragrafo.runs)


def _colapsar_runs(paragrafo) -> None:
    """
    Consolida todos os runs de um parágrafo em um único run.

    Necessário porque o Word pode dividir "{{NOME}}" em vários runs:
    ["{{", "NOME", "}}"] — o que impede a substituição direta.
    Após colapsar, paragrafo.runs[0] contém o texto completo.
    Preserva a formatação (negrito, fonte) do primeiro run.
    """
    runs = paragrafo.runs
    if len(runs) <= 1:
        return

    # Junta todo o texto no primeiro run
    texto_total = "".join(r.text for r in runs)
    runs[0].text = texto_total

    # Remove os runs extras do XML (mantém apenas o primeiro)
    # Precisamos remover os elementos XML diretamente
    primeiro_r = runs[0]._r
    for run in runs[1:]:
        r_elem = run._r
        r_elem.getparent().remove(r_elem)


def _substituir_em_paragrafos(paragrafos, dados: dict) -> None:
    """
    Substitui variáveis em uma lista de parágrafos.

    Para cada parágrafo que contém ao menos uma variável:
    1. Colapsa os runs para garantir que a variável está num único fragmento
    2. Faz a substituição via regex no texto do primeiro run
    """
    for para in paragrafos:
        texto = _texto_do_paragrafo(para)
        if not PADRAO_VARIAVEL.search(texto):
            continue

        # Colapsa os runs para facilitar a substituição
        _colapsar_runs(para)

        if not para.runs:
            continue

        # Substitui todas as variáveis no texto do primeiro run
        def substituir(match):
            nome_var = match.group(1)
            # Variável não mapeada → string vazia (não deixa {{VAR}} no doc)
            return dados.get(nome_var, "")

        para.runs[0].text = PADRAO_VARIAVEL.sub(substituir, para.runs[0].text)


def _substituir_em_tabelas(tabelas, dados: dict) -> None:
    """Substitui variáveis em todas as células de todas as tabelas."""
    for tabela in tabelas:
        for linha in tabela.rows:
            for celula in linha.cells:
                _substituir_em_paragrafos(celula.paragraphs, dados)


def _substituir_no_documento(doc, dados: dict) -> None:
    """
    Substitui variáveis em todo o documento:
    - Parágrafos do corpo principal
    - Células de tabelas
    - Cabeçalhos e rodapés de cada seção
    """
    # Corpo principal
    _substituir_em_paragrafos(doc.paragraphs, dados)

    # Tabelas
    _substituir_em_tabelas(doc.tables, dados)

    # Cabeçalhos e rodapés de cada seção
    for secao in doc.sections:
        # Cabeçalho
        if secao.header:
            _substituir_em_paragrafos(secao.header.paragraphs, dados)
            _substituir_em_tabelas(secao.header.tables, dados)
        # Rodapé
        if secao.footer:
            _substituir_em_paragrafos(secao.footer.paragraphs, dados)
            _substituir_em_tabelas(secao.footer.tables, dados)


def _caminho_sem_colisao(caminho: str) -> str:
    """
    Se o arquivo não existe, retorna o caminho original.
    Se existir, adiciona sufixo _2, _3... até encontrar um nome livre.
    """
    if not os.path.exists(caminho):
        return caminho

    base, ext = os.path.splitext(caminho)
    contador = 2
    while True:
        novo = f"{base}_{contador}{ext}"
        if not os.path.exists(novo):
            return novo
        contador += 1


# ── API pública ──────────────────────────────────────────────────────────────

def extrair_variaveis(caminho_docx: str) -> list[str]:
    """
    Abre um arquivo .docx e retorna a lista de variáveis encontradas.

    Busca o padrão {{NOME}} em:
    - Parágrafos do corpo
    - Células de tabelas
    - Cabeçalhos e rodapés

    Retorna lista sem duplicatas, na ordem de aparição.
    """
    doc = Document(caminho_docx)
    encontradas = []
    vistas = set()

    def _coletar_de_paragrafos(paragrafos):
        for para in paragrafos:
            texto = _texto_do_paragrafo(para)
            for match in PADRAO_VARIAVEL.finditer(texto):
                nome = match.group(1)
                if nome not in vistas:
                    vistas.add(nome)
                    encontradas.append(nome)

    def _coletar_de_tabelas(tabelas):
        for tabela in tabelas:
            for linha in tabela.rows:
                for celula in linha.cells:
                    _coletar_de_paragrafos(celula.paragraphs)

    # Corpo
    _coletar_de_paragrafos(doc.paragraphs)
    _coletar_de_tabelas(doc.tables)

    # Cabeçalhos e rodapés
    for secao in doc.sections:
        if secao.header:
            _coletar_de_paragrafos(secao.header.paragraphs)
            _coletar_de_tabelas(secao.header.tables)
        if secao.footer:
            _coletar_de_paragrafos(secao.footer.paragraphs)
            _coletar_de_tabelas(secao.footer.tables)

    return encontradas


def gerar_documento(caminho_template: str, dados: dict, caminho_saida: str) -> str:
    """
    Gera um documento Word preenchido a partir de um template.

    - Nunca modifica o arquivo template original
    - Se caminho_saida já existir, adiciona sufixo _2, _3...
    - Retorna o caminho real do arquivo gerado

    Parâmetros:
        caminho_template: caminho para o arquivo .docx template
        dados: dict {NOME_VARIAVEL: valor_string}
        caminho_saida: caminho desejado para o arquivo gerado
    """
    # Resolve colisão de nome antes de qualquer operação
    caminho_real = _caminho_sem_colisao(caminho_saida)

    # Copia o template (nunca abre o original para escrever)
    shutil.copy2(caminho_template, caminho_real)

    # Abre a cópia, substitui e salva
    doc = Document(caminho_real)
    _substituir_no_documento(doc, dados)
    doc.save(caminho_real)

    return caminho_real
