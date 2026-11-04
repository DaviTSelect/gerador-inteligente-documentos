# Gerador Inteligente de Documentos — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar uma aplicação desktop Python (PySide6) que preenche templates Word com variáveis a partir de planilhas ou entrada manual, com conversão para PDF.

**Architecture:** Interface em 5 etapas lineares (sidebar esquerda + área de conteúdo). Lógica de negócio separada da GUI em 3 módulos independentes (planilhas, documentos, pdf). Thread separada para geração sem travar a UI.

**Tech Stack:** PySide6 6.6+, python-docx 1.1+, openpyxl 3.1+, pandas 2.1+, docx2pdf 0.1.8+, chardet 5.0+, pytest

**Spec:** `docs/superpowers/specs/2026-11-04-gerador-documentos-design.md`

## Global Constraints

- Python 3.10+, Windows 11
- Nenhum arquivo modifica o template original
- Células vazias (None, NaN, NaT) → string vazia `""` nos documentos
- PDF via docx2pdf (requer Microsoft Word instalado)
- Interface fiel à imagem de referência: paleta, layout, tipografia
- Comentários no código em português
- Zero arquiteturas complexas: funções pequenas, classes apenas quando necessário

## Review Focus

- CPF/CNPJ com menos de 11/14 dígitos (ex: 9999999 sem zeros) → `formatar_cpf` deve zero-preencher à esquerda antes de formatar
- Variável `{{DATA}}` dividida em 3 runs XML (`{{`, `DAT`, `A}}`) → `substituir_no_documento` deve reconhecer e colapsar runs
- Planilha com coluna de data armazenada como número serial do Excel (ex: 46400) → `formatar_valor` tipo `data` deve converter corretamente
- CSV com encoding latin-1 e separador `;` → `ler_csv` deve detectar ambos automaticamente
- Arquivo de saída já existente no destino → `gerar_documento` deve incrementar sufixo sem sobrescrever

---

### Task 1: Estrutura do projeto + dependências

**Files:**
- Create: `gerador_documentos/requirements.txt`
- Create: `gerador_documentos/tests/__init__.py` (vazio)

**Interfaces:**
- Produces: ambiente instalado; pasta `gerador_documentos/` pronta para os demais tasks

- [ ] **Step 1: Criar pasta do projeto**

```
mkdir gerador_documentos
mkdir gerador_documentos\tests
```

- [ ] **Step 2: Criar `gerador_documentos/requirements.txt`**

```
PySide6>=6.6.0
python-docx>=1.1.0
openpyxl>=3.1.0
pandas>=2.1.0
docx2pdf>=0.1.8
chardet>=5.0.0
pytest>=7.4.0
```

- [ ] **Step 3: Instalar dependências**

```
pip install -r gerador_documentos/requirements.txt
```
Esperado: instalação sem erros críticos; docx2pdf pode avisar sobre Word.

- [ ] **Step 4: Criar `gerador_documentos/tests/__init__.py`** (arquivo vazio)

---

### Task 2: planilhas.py — leitura e formatação de dados

**Files:**
- Create: `gerador_documentos/planilhas.py`
- Create: `gerador_documentos/tests/test_planilhas.py`

**Interfaces:**
- Produces:
  - `ler_excel(caminho: str) -> tuple[list[str], list[dict]]`
  - `ler_csv(caminho: str) -> tuple[list[str], list[dict]]`
  - `detectar_tipo(nome_coluna: str, valor: object) -> str`
  - `formatar_valor(valor: object, tipo: str) -> str`
  - Constante: `TIPOS_DISPONIVEIS: list[str]` com os 13 nomes de tipo

- [ ] **Step 1: Escrever testes para `formatar_valor`**

```python
# tests/test_planilhas.py
import pytest
from planilhas import formatar_valor

def test_inteiro_remove_decimal():
    assert formatar_valor(42.0, "inteiro") == "42"

def test_moeda_formato_br():
    assert formatar_valor(1234.56, "moeda") == "R$ 1.234,56"

def test_cpf_zero_a_esquerda():
    # 9 dígitos: deve zero-preencher para 11 antes de formatar
    assert formatar_valor(123456789, "cpf") == "001.234.567-89"

def test_cpf_11_digitos():
    assert formatar_valor(12345678900, "cpf") == "123.456.789-00"

def test_data_datetime():
    from datetime import date
    assert formatar_valor(date(2026, 11, 4), "data") == "04/11/2026"

def test_data_string_br():
    assert formatar_valor("04/11/2026", "data") == "04/11/2026"

def test_cep_zero_a_esquerda():
    assert formatar_valor(1310100, "cep") == "01310-100"

def test_percentual_fracao():
    # 0.15 vindo do Excel (célula formatada como %) → "15%"
    assert formatar_valor(0.15, "percentual") == "15%"

def test_vazio_retorna_string_vazia():
    import math
    assert formatar_valor(None, "texto") == ""
    assert formatar_valor(float("nan"), "texto") == ""

def test_booleano():
    assert formatar_valor(True, "booleano") == "Sim"
    assert formatar_valor(False, "booleano") == "Não"

def test_codigo_preserva_zeros():
    assert formatar_valor("00123", "codigo") == "00123"
    assert formatar_valor(123, "codigo") == "123"
```

- [ ] **Step 2: Rodar testes para confirmar falha**

```
cd gerador_documentos && pytest tests/test_planilhas.py -v
```
Esperado: ImportError ou falhas — `planilhas.py` não existe ainda.

- [ ] **Step 3: Implementar `planilhas.py`**

Criar `gerador_documentos/planilhas.py` com:

```python
# Constante com todos os tipos disponíveis (usada no QMenu da UI)
TIPOS_DISPONIVEIS = [
    "texto", "inteiro", "decimal", "moeda", "cpf", "cnpj",
    "telefone", "cep", "data", "data_extenso", "percentual",
    "codigo", "booleano"
]

def _e_vazio(valor) -> bool: ...
# Retorna True para None, NaN, NaT, string vazia

def formatar_valor(valor, tipo: str) -> str: ...
# Dispatcher: chama _fmt_<tipo>(valor) conforme o tipo
# Se _e_vazio(valor): retorna ""

def _fmt_texto(valor) -> str: ...
def _fmt_inteiro(valor) -> str: ...  # float → int → str
def _fmt_decimal(valor) -> str: ...  # "1.234,56"
def _fmt_moeda(valor) -> str: ...    # "R$ 1.234,56"
def _fmt_cpf(valor) -> str: ...      # zfill(11), formata "XXX.XXX.XXX-XX"
def _fmt_cnpj(valor) -> str: ...     # zfill(14), formata
def _fmt_telefone(valor) -> str: ... # 10 dígitos: (XX) XXXX-XXXX; 11: (XX) XXXXX-XXXX
def _fmt_cep(valor) -> str: ...      # zfill(8), formata "XXXXX-XXX"
def _fmt_data(valor) -> str: ...     # aceita date, datetime, str, serial Excel
def _fmt_data_extenso(valor) -> str: ...  # "04 de novembro de 2026"
def _fmt_percentual(valor) -> str: ...    # <1: multiplica por 100; adiciona "%"
def _fmt_codigo(valor) -> str: ...        # str(valor) sem conversão numérica
def _fmt_booleano(valor) -> str: ...      # "Sim"/"Não"

def detectar_tipo(nome_coluna: str, valor) -> str: ...
# Heurística por nome_coluna.lower() e type(valor)
# Retorna um dos 13 tipos (default: "texto")

def ler_excel(caminho: str) -> tuple[list[str], list[dict]]: ...
# openpyxl, data_only=True; pula linhas onde todas as células são vazias
# Retorna (headers, lista_de_dicts)

def ler_csv(caminho: str) -> tuple[list[str], list[dict]]: ...
# Tenta encodings: utf-8-sig → utf-8 → latin-1
# Detecta separador: lê 1ª linha, compara count(',') vs count(';')
```

- [ ] **Step 4: Rodar testes**

```
cd gerador_documentos && pytest tests/test_planilhas.py -v
```
Esperado: 11 testes PASS.

- [ ] **Step 5: Adicionar testes de `detectar_tipo`**

```python
def test_detectar_tipo_cpf():
    assert detectar_tipo("CPF do colaborador", 12345678900) == "cpf"

def test_detectar_tipo_data():
    from datetime import date
    assert detectar_tipo("data_admissao", date(2026,1,1)) == "data"

def test_detectar_tipo_moeda():
    assert detectar_tipo("salario_base", 4500.0) == "moeda"

def test_detectar_tipo_texto_default():
    assert detectar_tipo("nome_completo", "Ana") == "texto"
```

- [ ] **Step 6: Rodar todos os testes**

```
cd gerador_documentos && pytest tests/test_planilhas.py -v
```
Esperado: 15 testes PASS.

---

### Task 3: documentos.py — extração de variáveis e substituição no DOCX

**Files:**
- Create: `gerador_documentos/documentos.py`
- Create: `gerador_documentos/tests/test_documentos.py`
- Create: `gerador_documentos/tests/fixtures/template_simples.docx` (criado pelo próprio teste)

**Interfaces:**
- Produces:
  - `extrair_variaveis(caminho_docx: str) -> list[str]`
  - `gerar_documento(caminho_template: str, dados: dict[str,str], caminho_saida: str) -> str`
    - Retorna o caminho real do arquivo salvo (pode ter sufixo _2 etc.)

- [ ] **Step 1: Escrever testes**

```python
# tests/test_documentos.py
import os, shutil, pytest
from docx import Document
from documentos import extrair_variaveis, gerar_documento

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture(scope="module", autouse=True)
def criar_template():
    """Cria template de teste antes dos testes."""
    os.makedirs(FIXTURES, exist_ok=True)
    doc = Document()
    doc.add_paragraph("Contrato de {{NOME}}, CPF {{CPF}}, admitido em {{DATA}}.")
    tabela = doc.add_table(rows=1, cols=2)
    tabela.cell(0,0).text = "Cargo: {{CARGO}}"
    tabela.cell(0,1).text = "Salário: {{SALARIO}}"
    doc.save(os.path.join(FIXTURES, "template_simples.docx"))
    yield
    shutil.rmtree(FIXTURES, ignore_errors=True)

def test_extrair_variaveis_paragrafo():
    caminho = os.path.join(FIXTURES, "template_simples.docx")
    variaveis = extrair_variaveis(caminho)
    assert "NOME" in variaveis
    assert "CPF" in variaveis
    assert "DATA" in variaveis

def test_extrair_variaveis_tabela():
    caminho = os.path.join(FIXTURES, "template_simples.docx")
    variaveis = extrair_variaveis(caminho)
    assert "CARGO" in variaveis
    assert "SALARIO" in variaveis

def test_gerar_documento_substitui_valores():
    template = os.path.join(FIXTURES, "template_simples.docx")
    saida = os.path.join(FIXTURES, "saida_teste.docx")
    dados = {"NOME": "Ana Silva", "CPF": "123.456.789-00",
             "DATA": "04/11/2026", "CARGO": "Analista", "SALARIO": "R$ 4.500,00"}
    gerar_documento(template, dados, saida)
    doc = Document(saida)
    texto = " ".join(p.text for p in doc.paragraphs)
    assert "Ana Silva" in texto
    assert "{{NOME}}" not in texto

def test_nao_modifica_template():
    template = os.path.join(FIXTURES, "template_simples.docx")
    mtime_antes = os.path.getmtime(template)
    saida = os.path.join(FIXTURES, "saida_mtime.docx")
    gerar_documento(template, {"NOME": "X"}, saida)
    assert os.path.getmtime(template) == mtime_antes

def test_sufixo_quando_arquivo_existe():
    template = os.path.join(FIXTURES, "template_simples.docx")
    saida = os.path.join(FIXTURES, "saida_sufixo.docx")
    # Cria o arquivo primeiro
    gerar_documento(template, {"NOME": "X"}, saida)
    # Chama de novo com mesmo destino
    saida2 = gerar_documento(template, {"NOME": "Y"}, saida)
    assert saida2 != saida
    assert os.path.exists(saida2)
```

- [ ] **Step 2: Rodar testes para confirmar falha**

```
cd gerador_documentos && pytest tests/test_documentos.py -v
```
Esperado: ImportError — `documentos.py` não existe ainda.

- [ ] **Step 3: Implementar `documentos.py`**

```python
import re, shutil, os
from docx import Document

PADRAO_VARIAVEL = re.compile(r'\{\{([A-Z_0-9]+)\}\}')

def extrair_variaveis(caminho_docx: str) -> list[str]: ...
# Abre com Document(caminho_docx)
# Coleta em todos os parágrafos + células de tabela + header/footer
# Usa _texto_completo_paragrafo() para lidar com runs fragmentados
# Retorna lista única (sem duplicatas), ordem de aparição

def _texto_completo_paragrafo(paragrafo) -> str: ...
# "".join(run.text for run in paragrafo.runs)

def gerar_documento(caminho_template: str, dados: dict, caminho_saida: str) -> str: ...
# Resolve colisões: se caminho_saida existe, tenta _2, _3...
# Copia template para caminho_saida resolvido (nunca abre o original)
# Abre a cópia com Document(), chama substituir_no_documento(), salva
# Retorna o caminho real salvo

def substituir_no_documento(doc, dados: dict) -> None: ...
# Chama _substituir_em_paragrafos(doc.paragraphs, dados)
# Chama _substituir_em_tabelas(doc.tables, dados)
# Para cada secao em doc.sections: header e footer também

def _substituir_em_paragrafos(paragrafos, dados: dict) -> None: ...
# Para cada parágrafo: se PADRAO_VARIAVEL acha match no texto completo:
#   _colapsar_runs(paragrafo) → consolida todos os runs em 1
#   substitui no run[0].text usando re.sub

def _colapsar_runs(paragrafo) -> None: ...
# Junta texto de todos os runs no primeiro, apaga os demais
# Preserva formatação (bold, font) do primeiro run

def _substituir_em_tabelas(tabelas, dados: dict) -> None: ...
# Para cada tabela → cada linha → cada célula → _substituir_em_paragrafos

def _caminho_sem_colisao(caminho: str) -> str: ...
# Se não existe: retorna caminho
# Se existe: testa _2, _3... até achar livre
```

- [ ] **Step 4: Rodar testes**

```
cd gerador_documentos && pytest tests/test_documentos.py -v
```
Esperado: 5 testes PASS.

---

### Task 4: pdf.py — conversão para PDF

**Files:**
- Create: `gerador_documentos/pdf.py`
- Create: `gerador_documentos/tests/test_pdf.py`

**Interfaces:**
- Consumes: `gerar_documento` de `documentos.py` (para criar DOCX de teste)
- Produces:
  - `converter_para_pdf(caminho_docx: str) -> str` — retorna caminho do PDF
  - `converter_em_lote(lista: list[str], callback: callable) -> list[str]`
    - `callback(atual: int, total: int, nome: str)` chamado a cada arquivo

- [ ] **Step 1: Escrever teste**

```python
# tests/test_pdf.py
import os, pytest
from docx import Document
from pdf import converter_para_pdf

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures_pdf")

@pytest.fixture(scope="module", autouse=True)
def preparar():
    os.makedirs(FIXTURES, exist_ok=True)
    doc = Document()
    doc.add_paragraph("Documento de teste PDF.")
    doc.save(os.path.join(FIXTURES, "teste.docx"))
    yield
    import shutil; shutil.rmtree(FIXTURES, ignore_errors=True)

@pytest.mark.skipif(
    not __import__("shutil").which("WINWORD.EXE"),
    reason="Microsoft Word não instalado"
)
def test_converte_para_pdf():
    caminho_docx = os.path.join(FIXTURES, "teste.docx")
    caminho_pdf = converter_para_pdf(caminho_docx)
    assert caminho_pdf.endswith(".pdf")
    assert os.path.exists(caminho_pdf)
```

- [ ] **Step 2: Implementar `pdf.py`**

```python
from docx2pdf import convert
import os

def converter_para_pdf(caminho_docx: str) -> str: ...
# Chama convert(caminho_docx)
# Retorna caminho_docx.replace(".docx", ".pdf")
# Se falhar: lança RuntimeError com mensagem clara em português

def converter_em_lote(lista_caminhos: list, callback=None) -> list[str]: ...
# Para cada caminho: converter_para_pdf(); callback(i+1, total, nome)
# Se um falhar: adiciona a lista de erros, continua os demais
# Retorna lista dos PDFs gerados com sucesso
```

- [ ] **Step 3: Rodar teste**

```
cd gerador_documentos && pytest tests/test_pdf.py -v
```
Esperado: PASS (ou skip se Word não estiver instalado).

---

### Task 5: app.py — interface gráfica completa

**Files:**
- Create: `gerador_documentos/app.py`

**Interfaces:**
- Consumes:
  - `extrair_variaveis(caminho_docx)` de `documentos.py`
  - `gerar_documento(template, dados, saida)` de `documentos.py`
  - `ler_excel(caminho)`, `ler_csv(caminho)`, `detectar_tipo(col, val)`, `formatar_valor(val, tipo)`, `TIPOS_DISPONIVEIS` de `planilhas.py`
  - `converter_em_lote(lista, callback)` de `pdf.py`
- Produces: `MainWindow` (QMainWindow)

- [ ] **Step 1: Implementar estrutura base + sidebar**

Criar `gerador_documentos/app.py` com:

```python
# Paleta de cores (definida como constantes no topo do arquivo)
COR_SIDEBAR = "#0F172A"
COR_ACENTO  = "#F97316"
COR_VERDE   = "#22C55E"
COR_ERRO    = "#EF4444"
COR_FUNDO   = "#F8FAFC"
COR_CARD    = "#FFFFFF"
COR_BORDA   = "#E2E8F0"
COR_TEXTO   = "#1E293B"
COR_CINZA   = "#64748B"

class MainWindow(QMainWindow):
    # Janela 1200x800, não redimensionável
    # Layout: QHBoxLayout com sidebar (280px) + area_conteudo
    # self.etapa_atual: int (1-5)
    # self.dados_sessao: dict (armazena seleções entre etapas)
    # ir_para_etapa(n): atualiza sidebar + mostra widget correto

class Sidebar(QWidget):
    # Lista de 5 EtapaIndicador
    # atualizar(etapa_ativa, etapas_concluidas): redesenha estados

class EtapaIndicador(QWidget):
    # Círculo (número ou ✓) + nome + subtítulo
    # Estado: "pendente" | "ativo" | "concluido"
```

- [ ] **Step 2: Implementar Etapa 1 (Template)**

```python
class PaginaTemplate(QWidget):
    # Botão selecionar .docx
    # Card: nome, tamanho, contagem de variáveis
    # Badge "Template validado"
    # Pílulas das variáveis
    # Botão "Próximo →" (ativo só com template válido)
    # Emite: template_selecionado(caminho, variaveis)
```

- [ ] **Step 3: Implementar Etapa 2 (Modo)**

```python
class PaginaModo(QWidget):
    # Dois cards: "Planilha Excel" e "Preenchimento manual"
    # Card selecionado: borda laranja
    # Botões "← Voltar" e "Próximo →"
```

- [ ] **Step 4: Implementar Etapa 3A (Planilha)**

```python
class PaginaPlanilha(QWidget):
    # Botão selecionar .xlsx/.csv
    # Card: nome arquivo, linhas, colunas
    # Tabela de mapeamento: 1 MapeamentoLinha por variável
    # Botões voltar/próximo

class MapeamentoLinha(QWidget):
    # Label variável + seta + QComboBox colunas + BotaoTipo + Label prévia
    # ao_mudar_coluna(): atualiza tipo auto e prévia
    # ao_mudar_tipo(tipo): marca tipo_manual, atualiza prévia
    # get_mapeamento() -> dict com variavel, coluna, tipo_manual

class BotaoTipo(QPushButton):
    # Exibe tipo atual (cinza=auto, laranja=manual)
    # Ao clicar: QMenu com "Auto (detectar)" + 13 tipos de TIPOS_DISPONIVEIS
    # Emite: tipo_alterado(novo_tipo_ou_None)
```

- [ ] **Step 5: Implementar Etapa 3B (Manual)**

```python
class PaginaManual(QWidget):
    # Para cada variável: QLabel + QLineEdit
    # Contador "X de Y campos preenchidos"
    # get_dados() -> dict[str, str]
```

- [ ] **Step 6: Implementar Etapa 4 (Destino)**

```python
class PaginaDestino(QWidget):
    # Campo pasta: QLineEdit + QPushButton "..."
    # Campo padrão de nome (default: "Documento_{{NOME}}.docx")
    # QLabel prévia do 1º nome
    # QCheckBox "Converter para PDF"
    # QCheckBox "Modo teste: gerar apenas 1 documento"
    # Sumário da configuração
    # Botão "Iniciar geração →" (laranja)
```

- [ ] **Step 7: Implementar Etapa 5 (Geração)**

```python
class ThreadGeracao(QThread):
    progresso = Signal(int, int, str)   # atual, total, nome
    erro      = Signal(str, str)         # arquivo, mensagem
    concluido = Signal(list)             # lista de dicts resultado

class PaginaGeracao(QWidget):
    # Conecta a ThreadGeracao via sinais
    # Barra de progresso QProgressBar
    # QListWidget log em tempo real
    # Botão "Cancelar geração"
    # Após conclusão: contadores, lista de arquivos, "Abrir pasta", "Nova geração"
```

- [ ] **Step 8: Integrar navegação entre etapas**

`MainWindow.ir_para_etapa(n)`: lê `dados_sessao`, instancia a página correta, substitui no QStackedWidget, atualiza sidebar.

- [ ] **Step 9: Testar manualmente a UI**

```
cd gerador_documentos && python main.py
```
Verificar:
1. Janela abre 1200×800
2. Sidebar mostra 5 etapas, etapa 1 ativa (laranja)
3. Selecionar um .docx → variáveis aparecem como pílulas
4. Navegar até etapa 5 no modo manual
5. Gerar 1 documento → verificar conteúdo do .docx gerado
6. Testar modo planilha com .xlsx
7. Testar opção PDF (se Word instalado)
8. Testar botão Cancelar durante geração

---

### Task 6: main.py — ponto de entrada

**Files:**
- Create: `gerador_documentos/main.py`

**Interfaces:**
- Consumes: `MainWindow` de `app.py`
- Produces: executável `python main.py`

- [ ] **Step 1: Criar `main.py`**

```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    janela = MainWindow()
    janela.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar execução**

```
cd gerador_documentos && python main.py
```
Esperado: janela abre sem erros no terminal.

---

### Task 7: Documentação

**Files:**
- Create: `gerador_documentos/README.md`
- Create: `gerador_documentos/GUIA_DO_PROJETO.md`
- Create: `gerador_documentos/GUIA_DE_ERROS.md`

**Interfaces:**
- Produces: documentação completa em português para iniciantes

- [ ] **Step 1: Escrever `README.md`**

Seções: O que faz · Requisitos (Python 3.10+, Word) · Instalação passo a passo · Como executar · Como usar (com capturas de tela descritas) · Como gerar executável com PyInstaller

- [ ] **Step 2: Escrever `GUIA_DO_PROJETO.md`**

Seções: Mapa dos arquivos · planilhas.py em detalhe · documentos.py em detalhe · pdf.py em detalhe · app.py em detalhe · Como adicionar um novo tipo de formatação · Como adicionar uma nova etapa na UI

- [ ] **Step 3: Escrever `GUIA_DE_ERROS.md`**

Seções: Erros na instalação · Erros ao abrir o template · Erros na planilha (encoding, separador, tipos) · Erros na geração (variável não substituída, arquivo bloqueado) · Erros no PDF (Word não instalado, arquivo aberto) · Tabela de mensagens de erro → causa → solução
