"""
Testes para planilhas.py
Rodados com: pytest tests/test_planilhas.py -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import date, datetime
from planilhas import formatar_valor, detectar_tipo, TIPOS_DISPONIVEIS


# ── formatar_valor ──────────────────────────────────────────────────────────

class TestFormatarInteiro:
    def test_float_vira_inteiro(self):
        assert formatar_valor(42.0, "inteiro") == "42"

    def test_numero_grande(self):
        assert formatar_valor(1000.0, "inteiro") == "1000"

    def test_zero(self):
        assert formatar_valor(0.0, "inteiro") == "0"


class TestFormatarDecimal:
    def test_formato_br(self):
        assert formatar_valor(1234.56, "decimal") == "1.234,56"

    def test_sem_separador_milhar(self):
        assert formatar_valor(99.5, "decimal") == "99,50"


class TestFormatarMoeda:
    def test_formato_br(self):
        assert formatar_valor(1234.56, "moeda") == "R$ 1.234,56"

    def test_centavos(self):
        assert formatar_valor(0.5, "moeda") == "R$ 0,50"


class TestFormatarCPF:
    def test_cpf_11_digitos(self):
        assert formatar_valor(12345678900, "cpf") == "123.456.789-00"

    def test_cpf_zero_a_esquerda(self):
        # 9 dígitos: zfill(11) → 00123456789 → 001.234.567-89
        assert formatar_valor(123456789, "cpf") == "001.234.567-89"

    def test_cpf_string(self):
        assert formatar_valor("12345678900", "cpf") == "123.456.789-00"


class TestFormatarCNPJ:
    def test_cnpj_14_digitos(self):
        assert formatar_valor(12345678000195, "cnpj") == "12.345.678/0001-95"

    def test_cnpj_string(self):
        assert formatar_valor("12345678000195", "cnpj") == "12.345.678/0001-95"


class TestFormatarTelefone:
    def test_celular_11_digitos(self):
        assert formatar_valor(11999998888, "telefone") == "(11) 99999-8888"

    def test_fixo_10_digitos(self):
        assert formatar_valor(1133334444, "telefone") == "(11) 3333-4444"

    def test_string(self):
        assert formatar_valor("11999998888", "telefone") == "(11) 99999-8888"


class TestFormatarCEP:
    def test_cep_zero_a_esquerda(self):
        assert formatar_valor(1310100, "cep") == "01310-100"

    def test_cep_8_digitos(self):
        assert formatar_valor(12345678, "cep") == "12345-678"

    def test_cep_string(self):
        assert formatar_valor("01310100", "cep") == "01310-100"


class TestFormatarData:
    def test_date_object(self):
        assert formatar_valor(date(2026, 11, 4), "data") == "04/11/2026"

    def test_datetime_object(self):
        assert formatar_valor(datetime(2026, 11, 4, 10, 0), "data") == "04/11/2026"

    def test_string_br_passthrough(self):
        assert formatar_valor("04/11/2026", "data") == "04/11/2026"

    def test_string_iso(self):
        assert formatar_valor("2026-11-04", "data") == "04/11/2026"


class TestFormatarDataExtenso:
    def test_date_extenso(self):
        assert formatar_valor(date(2026, 11, 4), "data_extenso") == "04 de novembro de 2026"

    def test_mes_janeiro(self):
        assert formatar_valor(date(2026, 1, 15), "data_extenso") == "15 de janeiro de 2026"


class TestFormatarPercentual:
    def test_fracao_excel(self):
        # 0.15 no Excel representa 15%
        assert formatar_valor(0.15, "percentual") == "15%"

    def test_inteiro_ja_percentual(self):
        assert formatar_valor(15, "percentual") == "15%"

    def test_zero(self):
        assert formatar_valor(0, "percentual") == "0%"


class TestFormatarCodigo:
    def test_preserva_zeros(self):
        assert formatar_valor("00123", "codigo") == "00123"

    def test_numero_sem_zeros(self):
        assert formatar_valor(123, "codigo") == "123"


class TestFormatarBooleano:
    def test_true_vira_sim(self):
        assert formatar_valor(True, "booleano") == "Sim"

    def test_false_vira_nao(self):
        assert formatar_valor(False, "booleano") == "Não"

    def test_um_vira_sim(self):
        assert formatar_valor(1, "booleano") == "Sim"

    def test_zero_vira_nao(self):
        assert formatar_valor(0, "booleano") == "Não"


class TestValoresVazios:
    """Células vazias nunca devem gerar None, nan, NaT no documento."""
    def test_none_retorna_vazio(self):
        assert formatar_valor(None, "texto") == ""

    def test_nan_retorna_vazio(self):
        import math
        assert formatar_valor(float("nan"), "texto") == ""

    def test_string_vazia_retorna_vazio(self):
        assert formatar_valor("", "texto") == ""

    def test_none_em_tipo_cpf(self):
        assert formatar_valor(None, "cpf") == ""

    def test_none_em_tipo_data(self):
        assert formatar_valor(None, "data") == ""


class TestFormatarTexto:
    def test_preserva_acentos(self):
        assert formatar_valor("João Müller", "texto") == "João Müller"

    def test_remove_espacos_laterais(self):
        assert formatar_valor("  Ana Silva  ", "texto") == "Ana Silva"

    def test_numero_vira_string(self):
        assert formatar_valor(42, "texto") == "42"


# ── detectar_tipo ───────────────────────────────────────────────────────────

class TestDetectarTipo:
    def test_cpf_no_nome(self):
        assert detectar_tipo("CPF do colaborador", 12345678900) == "cpf"

    def test_cnpj_no_nome(self):
        assert detectar_tipo("cnpj_empresa", 12345678000195) == "cnpj"

    def test_cep_no_nome(self):
        assert detectar_tipo("cep", "01310100") == "cep"

    def test_telefone_no_nome(self):
        assert detectar_tipo("telefone_celular", 11999998888) == "telefone"

    def test_data_por_nome(self):
        assert detectar_tipo("data_admissao", date(2026, 1, 1)) == "data"

    def test_data_datetime_value(self):
        assert detectar_tipo("coluna_qualquer", datetime(2026, 1, 1)) == "data"

    def test_moeda_no_nome(self):
        assert detectar_tipo("salario_base", 4500.0) == "moeda"

    def test_percentual_no_nome(self):
        assert detectar_tipo("percentual_desconto", 0.15) == "percentual"

    def test_booleano_por_tipo(self):
        assert detectar_tipo("coluna", True) == "booleano"

    def test_float_inteiro_no_nome_generico(self):
        assert detectar_tipo("quantidade", 5.0) == "inteiro"

    def test_texto_default(self):
        assert detectar_tipo("nome_completo", "Ana") == "texto"


# ── TIPOS_DISPONIVEIS ────────────────────────────────────────────────────────

def test_tipos_disponiveis_contem_13():
    assert len(TIPOS_DISPONIVEIS) == 13

def test_tipos_disponiveis_contem_cpf():
    assert "cpf" in TIPOS_DISPONIVEIS
