"""Sugestão automática de coluna para cada variável do modelo."""
import planilhas


def _sugerida(variavel, colunas):
    indice = planilhas.sugerir_coluna(variavel, colunas)
    return None if indice is None else colunas[indice]


def test_mesmas_palavras_em_ordem_trocada():
    colunas = ["NOME", "PSU_VALOR", "SISU_VALOR"]
    assert _sugerida("Valor_PSU", colunas) == "PSU_VALOR"
    assert _sugerida("Valor_SiSU", colunas) == "SISU_VALOR"


def test_nome_identico_vence_coluna_que_apenas_contem():
    assert _sugerida("NOME", ["NOME_MAE", "Nome"]) == "Nome"


def test_acentos_espacos_e_hifens_nao_atrapalham():
    assert _sugerida("ENDERECO", ["CPF", "Endereço"]) == "Endereço"
    assert _sugerida("data_inicio", ["Data-Início"]) == "Data-Início"


def test_correspondencia_parcial_continua_funcionando():
    assert _sugerida("CPF", ["NOME", "Numero CPF"]) == "Numero CPF"


def test_sem_correspondencia_nao_sugere():
    assert _sugerida("Valor_PSU", ["NOME", "", "MATRICULA"]) is None
