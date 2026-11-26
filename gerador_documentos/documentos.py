"""
documentos.py — Leitura de templates Word e geração de documentos preenchidos.

Responsabilidade: abrir um .docx template, encontrar variáveis {{VAR}},
substituí-las pelos valores fornecidos e salvar o resultado sem modificar
o template original.

Regra de formatação: o valor herda a formatação do marcador no template.
Nenhum run é criado, fundido, removido ou reformatado — apenas o texto dos
elementos <w:t> que contêm o marcador é alterado.

O Word costuma dividir "{{NOME}}" em vários runs (ex.: "{{", "NOM", "E}}").
Nesse caso o valor é escrito no run onde começa o NOME da variável (é a
formatação dele que vale) e os demais pedaços do marcador são apagados.
"""
import copy
import os
import re

from docx import Document
from docx.opc.oxml import serialize_part_xml
from docx.oxml import parse_xml
from docx.oxml.ns import qn

# {{NOME}}, {{ Nome do Aluno }}, {{ENDEREÇO}}… O grupo 1 é o nome sem espaços
# nas pontas. Tabulações e quebras de linha nunca fazem parte de um marcador.
PADRAO_VARIAVEL = re.compile(
    r"\{\{[  ]*([^{}\t\n\r  ](?:[^{}\t\n\r]*?[^{}\t\n\r  ])?)[  ]*\}\}"
)

# Caracteres que o XML não aceita (podem vir de células do Excel)
_ILEGAIS_XML = re.compile("[\x00-\x08\x0c\x0e-\x1f\ud800-\udfff￾￿]")

# Elementos de um run que separam texto: um marcador não pode atravessá-los
_SEPARADORES = {qn("w:tab"), qn("w:br"), qn("w:cr")}

# Partes do pacote que têm texto visível, na ordem de coleta das variáveis
_PARTES_COM_TEXTO = ("document.main", "header", "footer", "footnotes", "endnotes")

_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


# ── Funções internas ─────────────────────────────────────────────────────────

def _partes_com_texto(doc):
    """
    Gera (parte, elemento_raiz) de cada parte do .docx que contém texto.

    Percorrer as partes do pacote (em vez de doc.sections) alcança cabeçalhos
    de primeira página e páginas pares, e não cria cabeçalhos vazios.
    """
    partes = list(doc.part.package.iter_parts())
    for tipo in _PARTES_COM_TEXTO:
        sufixo = f"wordprocessingml.{tipo}+xml"
        for parte in sorted(partes, key=lambda p: str(p.partname)):
            if not parte.content_type.endswith(sufixo):
                continue
            raiz = getattr(parte, "element", None)
            if raiz is None:  # notas de rodapé são carregadas como bytes
                raiz = parse_xml(parte.blob)
            yield parte, raiz


def _nos_do_paragrafo(paragrafo):
    """
    Retorna [(elemento, texto)] do parágrafo na ordem de leitura.

    Inclui texto dentro de hyperlinks, controles de conteúdo e revisões.
    Ignora parágrafos aninhados (caixas de texto), que são tratados à parte.
    Separadores entram com elemento None.
    """
    nos = []

    def visitar(elemento):
        for filho in elemento:
            if filho.tag == qn("w:p"):
                continue
            if filho.tag == qn("w:t"):
                nos.append((filho, filho.text or ""))
            elif filho.tag in _SEPARADORES and elemento.tag == qn("w:r"):
                nos.append((None, "\n"))
            else:
                visitar(filho)

    visitar(paragrafo)
    return nos


def _definir_texto(t, texto: str) -> None:
    t.text = texto
    t.set(_XML_SPACE, "preserve")


def _expandir_quebras(t) -> None:
    """Converte \\n e \\t do valor em <w:br/> e <w:tab/> dentro do mesmo run."""
    texto = t.text or ""
    if "\n" not in texto and "\t" not in texto:
        return

    pedacos = re.split(r"([\n\t])", texto)
    _definir_texto(t, pedacos[0])
    anterior = t
    for pedaco in pedacos[1:]:
        if not pedaco:
            continue
        if pedaco == "\n":
            novo = t.makeelement(qn("w:br"), {})
        elif pedaco == "\t":
            novo = t.makeelement(qn("w:tab"), {})
        else:
            novo = copy.copy(t)
            _definir_texto(novo, pedaco)
        anterior.addnext(novo)
        anterior = novo


def _limpar_valor(valor) -> str:
    texto = str(valor).replace("\r\n", "\n").replace("\r", "\n").replace("\x0b", "\n")
    return _ILEGAIS_XML.sub("", texto)


def _substituir_no_paragrafo(paragrafo, dados: dict) -> None:
    """Substitui os marcadores de um parágrafo sem mexer em nenhuma formatação."""
    nos = _nos_do_paragrafo(paragrafo)
    completo = "".join(texto for _, texto in nos)
    marcadores = list(PADRAO_VARIAVEL.finditer(completo))
    if not marcadores:
        return

    inicios = []
    posicao = 0
    for _, texto in nos:
        inicios.append(posicao)
        posicao += len(texto)

    textos = [texto for _, texto in nos]
    alterados = set()

    # De trás para frente: as posições dos marcadores anteriores não mudam
    for marcador in reversed(marcadores):
        inicio, fim = marcador.span()
        inicio_nome = marcador.start(1)
        valor = _limpar_valor(dados.get(marcador.group(1), ""))

        for i in reversed(range(len(nos))):
            base = inicios[i]
            tamanho = len(nos[i][1])
            if nos[i][0] is None or base >= fim or base + tamanho <= inicio:
                continue
            corte_ini = max(inicio - base, 0)
            corte_fim = min(fim - base, tamanho)
            # O valor vai para o nó onde o nome da variável começa
            novo = valor if base <= inicio_nome < base + tamanho else ""
            textos[i] = textos[i][:corte_ini] + novo + textos[i][corte_fim:]
            alterados.add(i)

    for i in alterados:
        t = nos[i][0]
        _definir_texto(t, textos[i])
        _expandir_quebras(t)


# ── Utilitário de nome de arquivo ────────────────────────────────────────────

def _caminho_sem_colisao(caminho: str, reservar_pdf: bool = False) -> str:
    """
    Se o arquivo não existe, retorna o caminho original.
    Se existir, adiciona sufixo _2, _3... até encontrar um nome livre.
    Com reservar_pdf, o .pdf de mesmo nome também precisa estar livre.
    """
    base, ext = os.path.splitext(caminho)
    candidato, contador = base, 2
    while os.path.exists(candidato + ext) or (
        reservar_pdf and os.path.exists(candidato + ".pdf")
    ):
        candidato = f"{base}_{contador}"
        contador += 1
    return candidato + ext


# ── API pública ──────────────────────────────────────────────────────────────

def extrair_variaveis(caminho_docx: str) -> list[str]:
    """
    Abre um arquivo .docx e retorna a lista de variáveis encontradas.

    Busca o padrão {{NOME}} no corpo, tabelas, caixas de texto, cabeçalhos,
    rodapés e notas. Retorna lista sem duplicatas, na ordem de aparição.
    """
    doc = Document(caminho_docx)
    encontradas = {}

    for _, raiz in _partes_com_texto(doc):
        for paragrafo in raiz.iter(qn("w:p")):
            completo = "".join(texto for _, texto in _nos_do_paragrafo(paragrafo))
            for marcador in PADRAO_VARIAVEL.finditer(completo):
                encontradas.setdefault(marcador.group(1), None)

    return list(encontradas)


def gerar_documento(caminho_template: str, dados: dict, caminho_saida: str,
                    reservar_pdf: bool = False) -> str:
    """
    Gera um documento Word preenchido a partir de um template.

    - Nunca modifica o arquivo template original
    - Se caminho_saida já existir, adiciona sufixo _2, _3...
    - Retorna o caminho real do arquivo gerado

    Parâmetros:
        caminho_template: caminho para o arquivo .docx template
        dados: dict {NOME_VARIAVEL: valor_string}
        caminho_saida: caminho desejado para o arquivo gerado
        reservar_pdf: True quando o .docx será convertido (evita sobrescrever PDF)
    """
    # Resolve colisão de nome antes de qualquer operação
    caminho_real = _caminho_sem_colisao(caminho_saida, reservar_pdf)

    doc = Document(caminho_template)
    for parte, raiz in _partes_com_texto(doc):
        for paragrafo in list(raiz.iter(qn("w:p"))):
            _substituir_no_paragrafo(paragrafo, dados)
        if getattr(parte, "element", None) is None:
            parte._blob = serialize_part_xml(raiz)

    doc.save(caminho_real)

    return caminho_real
