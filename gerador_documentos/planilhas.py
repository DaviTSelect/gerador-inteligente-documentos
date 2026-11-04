"""
planilhas.py — Leitura de arquivos Excel/CSV e formatação de dados.

Responsabilidade: ler planilhas e formatar cada valor no tipo correto
para que o documento Word fique com dados legíveis e bem formatados.
"""
import math
import re
from datetime import date, datetime

import chardet
import openpyxl
import pandas as pd


# Todos os tipos disponíveis para o menu de seleção na interface
TIPOS_DISPONIVEIS = [
    "texto",
    "inteiro",
    "decimal",
    "moeda",
    "cpf",
    "cnpj",
    "telefone",
    "cep",
    "data",
    "data_extenso",
    "percentual",
    "codigo",
    "booleano",
]

# Nomes dos meses em português para "data_extenso"
_MESES_PT = [
    "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]


# ── Helpers internos ─────────────────────────────────────────────────────────

def _e_vazio(valor) -> bool:
    """Retorna True para None, NaN, NaT e string vazia."""
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    if isinstance(valor, str) and valor.strip() == "":
        return True
    # pandas NaT
    try:
        import pandas as pd
        if pd.isnull(valor):
            return True
    except (TypeError, ValueError):
        pass
    return False


def _apenas_digitos(valor) -> str:
    """Extrai somente dígitos de um valor (int, float ou str)."""
    if isinstance(valor, float):
        # Ex: 12345678900.0 → "12345678900"
        valor = str(int(valor))
    return re.sub(r"\D", "", str(valor))


def _para_date(valor):
    """Converte valor para objeto date. Retorna None se não conseguir."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        # Formato brasileiro "dd/mm/aaaa"
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", valor.strip())
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        # Formato ISO "aaaa-mm-dd"
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", valor.strip())
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


# ── Formatadores individuais ─────────────────────────────────────────────────

def _fmt_texto(valor) -> str:
    return str(valor).strip()


def _fmt_inteiro(valor) -> str:
    # Remove a parte decimal: 42.0 → "42"
    return str(int(float(str(valor))))


def _fmt_decimal(valor) -> str:
    # Formato brasileiro: 1234.56 → "1.234,56"
    n = float(str(valor))
    # Formata com 2 casas decimais e separa milhar
    inteiro = int(n)
    decimal = round((n - inteiro) * 100)
    inteiro_formatado = f"{inteiro:,}".replace(",", ".")
    return f"{inteiro_formatado},{decimal:02d}"


def _fmt_moeda(valor) -> str:
    return f"R$ {_fmt_decimal(valor)}"


def _fmt_cpf(valor) -> str:
    digitos = _apenas_digitos(valor).zfill(11)
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:11]}"


def _fmt_cnpj(valor) -> str:
    digitos = _apenas_digitos(valor).zfill(14)
    return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:14]}"


def _fmt_telefone(valor) -> str:
    digitos = _apenas_digitos(valor)
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:11]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:10]}"
    # Retorna como está se não reconhece o tamanho
    return str(valor)


def _fmt_cep(valor) -> str:
    digitos = _apenas_digitos(valor).zfill(8)
    return f"{digitos[:5]}-{digitos[5:8]}"


def _fmt_data(valor) -> str:
    d = _para_date(valor)
    if d:
        return d.strftime("%d/%m/%Y")
    return str(valor)


def _fmt_data_extenso(valor) -> str:
    d = _para_date(valor)
    if d:
        mes = _MESES_PT[d.month]
        return f"{d.day:02d} de {mes} de {d.year}"
    return str(valor)


def _fmt_percentual(valor) -> str:
    # Valores vindos do Excel como fração (ex: 0.15 = 15%)
    # Se o valor for < 1 e não for 0, multiplica por 100
    n = float(str(valor))
    if 0 < abs(n) < 1:
        n = n * 100
    return f"{int(round(n))}%"


def _fmt_codigo(valor) -> str:
    # Preserva zeros à esquerda: nunca converte para número
    if isinstance(valor, (int, float)):
        return str(int(float(str(valor))))
    return str(valor)


def _fmt_booleano(valor) -> str:
    # Aceita True/False e 1/0
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    # Tenta int
    try:
        return "Sim" if int(valor) else "Não"
    except (ValueError, TypeError):
        return str(valor)


# Mapeamento tipo → função formatadora
_FORMATADORES = {
    "texto": _fmt_texto,
    "inteiro": _fmt_inteiro,
    "decimal": _fmt_decimal,
    "moeda": _fmt_moeda,
    "cpf": _fmt_cpf,
    "cnpj": _fmt_cnpj,
    "telefone": _fmt_telefone,
    "cep": _fmt_cep,
    "data": _fmt_data,
    "data_extenso": _fmt_data_extenso,
    "percentual": _fmt_percentual,
    "codigo": _fmt_codigo,
    "booleano": _fmt_booleano,
}


# ── API pública ──────────────────────────────────────────────────────────────

def formatar_valor(valor, tipo: str) -> str:
    """
    Converte um valor bruto (vindo de planilha) para string formatada
    conforme o tipo especificado.

    Retorna "" para valores vazios (None, NaN, NaT, string vazia).
    """
    if _e_vazio(valor):
        return ""

    formatador = _FORMATADORES.get(tipo, _fmt_texto)
    try:
        return formatador(valor)
    except Exception:
        # Se a formatação falhar, retorna o valor como texto simples
        return str(valor).strip()


def detectar_tipo(nome_coluna: str, valor) -> str:
    """
    Detecta o tipo mais provável de uma coluna baseado no nome e no valor.

    Heurística: nome da coluna tem prioridade; tipo do valor Python é fallback.
    """
    nome = nome_coluna.lower()

    # Tipos reconhecidos pelo nome da coluna
    if "cpf" in nome:
        return "cpf"
    if "cnpj" in nome:
        return "cnpj"
    if "cep" in nome:
        return "cep"
    if any(x in nome for x in ["tel", "fone", "celular", "phone"]):
        return "telefone"
    if any(x in nome for x in ["data", "dt_", "_dt", "nascimento", "admissao", "vencimento"]):
        return "data"
    if any(x in nome for x in ["valor", "salario", "preco", "custo", "total", "remuner"]):
        return "moeda"
    if "%" in nome or any(x in nome for x in ["perc", "percentual", "taxa"]):
        return "percentual"

    # Fallback por tipo Python do valor
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, (datetime, date)):
        return "data"
    if isinstance(valor, int):
        return "inteiro"
    if isinstance(valor, float):
        # Float que é inteiro (ex: 42.0) → inteiro
        if valor == int(valor):
            return "inteiro"
        return "decimal"

    return "texto"


def ler_excel(caminho: str) -> tuple[list[str], list[dict]]:
    """
    Lê um arquivo .xlsx e retorna (cabeçalhos, lista_de_dicts).

    Usa openpyxl com data_only=True para obter valores calculados
    em vez de fórmulas.
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.active

    linhas = list(ws.iter_rows(values_only=True))
    if not linhas:
        return [], []

    # Primeira linha é o cabeçalho
    headers = [str(c).strip() if c is not None else f"Coluna_{i+1}"
               for i, c in enumerate(linhas[0])]

    resultado = []
    for linha in linhas[1:]:
        # Pula linhas completamente vazias
        if all(c is None for c in linha):
            continue
        registro = {}
        for i, valor in enumerate(linha):
            if i < len(headers):
                registro[headers[i]] = valor
        resultado.append(registro)

    return headers, resultado


def ler_csv(caminho: str) -> tuple[list[str], list[dict]]:
    """
    Lê um arquivo .csv detectando automaticamente encoding e separador.

    Encodings tentados: utf-8-sig → utf-8 → latin-1
    Separadores testados: ',' e ';' (usa o que produzir mais colunas)
    """
    # Detectar encoding lendo os bytes brutos
    with open(caminho, "rb") as f:
        raw = f.read(10000)

    deteccao = chardet.detect(raw)
    encoding_detectado = deteccao.get("encoding", "utf-8") or "utf-8"

    # Tentar encodings em ordem de preferência
    encodings = ["utf-8-sig", "utf-8", "latin-1"]
    # Coloca o detectado em primeiro se não estiver já
    enc_norm = encoding_detectado.lower().replace("-", "")
    if enc_norm not in [e.lower().replace("-", "") for e in encodings]:
        encodings.insert(0, encoding_detectado)

    conteudo = None
    for enc in encodings:
        try:
            with open(caminho, "r", encoding=enc, errors="strict") as f:
                conteudo = f.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if conteudo is None:
        # Último recurso: latin-1 com erros ignorados
        with open(caminho, "r", encoding="latin-1", errors="replace") as f:
            conteudo = f.read()

    # Detectar separador: compara vírgula vs ponto-e-vírgula na 1ª linha
    primeira_linha = conteudo.split("\n")[0] if conteudo else ""
    sep = ";" if primeira_linha.count(";") >= primeira_linha.count(",") else ","

    # Ler com pandas (mais robusto para CSV)
    import io
    df = pd.read_csv(io.StringIO(conteudo), sep=sep, dtype=str, keep_default_na=False)

    headers = list(df.columns)
    resultado = []
    for _, row in df.iterrows():
        # Converte NaN/vazio para None para tratamento uniforme
        registro = {col: (None if pd.isna(val) or val == "" else val)
                    for col, val in row.items()}
        resultado.append(registro)

    return headers, resultado
