# Gerador Inteligente de Documentos — Design Spec

**Data:** 2026-11-04  
**Status:** Aprovado

---

## 1. Objetivo

Aplicação desktop Windows em Python que:
- Lê um template Word (.docx) com variáveis no formato `{{NOME}}`
- Preenche as variáveis a partir de uma planilha (.xlsx ou .csv) ou entrada manual
- Gera um documento Word por linha da planilha (ou 1 documento no modo manual)
- Opcionalmente converte os documentos gerados para PDF via Microsoft Word

---

## 2. Estrutura de Arquivos

```
gerador_documentos/
├── main.py          # Ponto de entrada — cria QApplication e abre MainWindow
├── app.py           # Janela principal + todas as 5 etapas da interface
├── documentos.py    # Leitura do .docx, extração de variáveis, substituição, salvamento
├── planilhas.py     # Leitura e tratamento de .xlsx e .csv (13 tipos de dados)
├── pdf.py           # Conversão de .docx para PDF via docx2pdf
├── requirements.txt # Dependências Python
├── README.md
├── GUIA_DO_PROJETO.md
└── GUIA_DE_ERROS.md
```

---

## 3. Dependências

```
PySide6>=6.6.0
python-docx>=1.1.0
openpyxl>=3.1.0
pandas>=2.1.0
docx2pdf>=0.1.8
chardet>=5.0.0
```

---

## 4. Interface (app.py)

### Layout geral
- Janela: 1200×800px, não redimensionável
- Duas colunas: **sidebar esquerda 280px** + **área de conteúdo**

### Sidebar (fundo #0F172A)
- Logo + "Gerador Inteligente de Documentos" no topo
- 5 indicadores de etapa com:
  - Círculo numerado (pendente: #CBD5E1 / ativo: #F97316 / concluído: #22C55E com ✓)
  - Nome da etapa e subtítulo breve
- Rodapé: "Seus dados, protegidos. Processamento local."

### Paleta de cores
| Token | Valor |
|---|---|
| Fundo página | #F8FAFC |
| Card | #FFFFFF |
| Sidebar | #0F172A |
| Acento laranja | #F97316 |
| Verde sucesso | #22C55E |
| Vermelho erro | #EF4444 |
| Borda | #E2E8F0 |
| Texto primário | #1E293B |
| Texto secundário | #64748B |

### Etapa 1 — Documento template
- Botão "Selecionar arquivo .docx"
- Card: nome do arquivo, tamanho, número de variáveis detectadas
- Badge verde "Template validado" quando válido
- Pílulas com cada variável encontrada (ex: `{{NOME}}` `{{CPF}}`)

### Etapa 2 — Modo de preenchimento
- Dois cards clicáveis lado a lado:
  - "Planilha Excel" (ícone verde, xlsx/csv)
  - "Preenchimento manual" (ícone laranja)
- Card selecionado: borda laranja

### Etapa 3A — Planilha
- Botão selecionar .xlsx ou .csv
- Card: nome do arquivo, número de linhas válidas, número de colunas
- **Tabela de mapeamento** (1 linha por variável):
  - Coluna 1: nome da variável (ex: `{{NOME}}`)
  - Seta →
  - Coluna 2: QComboBox com colunas da planilha
  - Coluna 3: QPushButton `[Tipo ▾]` (ver seção 6)
  - Coluna 4: QLabel com prévia do primeiro valor formatado

### Etapa 3B — Manual
- 1 QLineEdit por variável detectada
- Label acima de cada campo
- Contador "X de Y campos preenchidos"
- Nota: "Será gerado 1 documento."

### Etapa 4 — Destino
- Campo pasta de saída (QLineEdit + botão "...")
- Campo padrão de nome (ex: `Contrato_{{NOME}}_{{DATA}}.docx`)
- Prévia do nome do primeiro arquivo
- Checkbox "Converter para PDF (requer Microsoft Word)"
- Checkbox "Modo teste: gerar apenas 1 documento"
- Sumário: "X variáveis mapeadas • Y linhas válidas • Saída em DOCX [+ PDF]"

### Etapa 5 — Gerar
**Durante geração:**
- Barra de progresso laranja com `X de Y documentos`
- Texto: nome do arquivo sendo gerado
- Log em tempo real: lista de arquivos concluídos/erros
- Botão "Cancelar geração"

**Após conclusão:**
- Contadores: documentos gerados / erros / tempo total
- Lista de arquivos gerados
- Botão "Abrir pasta de destino" (laranja)
- Botão "+ Nova geração"

---

## 5. Lógica de negócio

### documentos.py

```
extrair_variaveis(caminho_docx) -> list[str]
  - Abre o .docx com python-docx
  - Busca padrão {{[A-Z_0-9]+}} em:
    - Todos os parágrafos do corpo
    - Todas as células de tabelas
    - Cabeçalhos e rodapés
  - Problema: variável pode estar dividida em múltiplos runs XML
    - Solução: reconstituir texto completo do parágrafo, buscar variáveis,
      e ao substituir, colapsar os runs afetados em um único run

gerar_documento(caminho_template, dados, caminho_saida) -> None
  - Faz cópia do template (nunca modifica o original)
  - Chama substituir_no_documento(doc, dados)
  - Salva como caminho_saida
  - Se arquivo já existe: adiciona sufixo _2, _3...

substituir_no_documento(doc, dados) -> None
  - Substitui em parágrafos do corpo
  - Substitui em células de tabelas
  - Substitui em cabeçalhos e rodapés

_substituir_em_paragrafos(paragrafos, dados) -> None
  - Para cada parágrafo: reconstituir texto, checar se tem {{VAR}}
  - Se sim: colapsar runs intermediários, substituir no run consolidado
  - Preservar formatação do primeiro run
```

### planilhas.py

```
ler_excel(caminho) -> (headers: list[str], linhas: list[dict])
  - Usa openpyxl com data_only=True
  - Lê todas as linhas não vazias
  - Preserva tipo original de cada célula

ler_csv(caminho) -> (headers: list[str], linhas: list[dict])
  - Detecta encoding: tenta utf-8-sig → utf-8 → latin-1
  - Detecta separador: testa ',' e ';', usa o que tiver mais colunas
  - Retorna linhas como dicts

detectar_tipo(nome_coluna, primeiro_valor) -> str
  - Heurística por nome + tipo do valor Python

formatar_valor(valor, tipo) -> str
  - Dispatcher para os 13 formatadores
  - Se valor é None/NaN/NaT/vazio → retorna ""
```

### planilhas.py — 13 tipos de formatação

| Tipo | Entrada | Saída |
|---|---|---|
| `texto` | qualquer | str(valor).strip() |
| `inteiro` | 42.0 | "42" |
| `decimal` | 1234.56 | "1.234,56" |
| `moeda` | 1234.56 | "R$ 1.234,56" |
| `cpf` | 12345678900 | "123.456.789-00" |
| `cnpj` | 12345678000195 | "12.345.678/0001-95" |
| `telefone` | 11999998888 | "(11) 99999-8888" |
| `cep` | 1310100 | "01310-100" |
| `data` | datetime/str/serial | "04/11/2026" |
| `data_extenso` | datetime/str | "04 de novembro de 2026" |
| `percentual` | 0.15 ou 15 | "15%" |
| `codigo` | "00123" | "00123" (preserva) |
| `booleano` | True/1 | "Sim" / "Não" |

### pdf.py

```
converter_para_pdf(caminho_docx) -> str (caminho PDF gerado)
  - Usa docx2pdf.convert()
  - Se Word não instalado: lança erro claro

converter_em_lote(lista_caminhos, callback) -> list[str]
  - Converte cada arquivo, chama callback(i, total, nome)
```

---

## 6. Sistema de tipos (botão [Tipo ▾])

### Estado do mapeamento
Cada linha da tabela armazena:
```python
{
  "variavel": "{{NOME}}",
  "coluna": "Nome completo",
  "tipo_auto": "texto",        # detectado automaticamente
  "tipo_manual": None,         # None = usar auto; str = usuário sobrescreveu
}
```

### Botão [Tipo ▾]
- Exibe `tipo_auto` em cinza se `tipo_manual` is None
- Exibe `tipo_manual` com borda laranja se sobrescrito
- Ao clicar: QMenu com 14 opções:
  1. Auto (detectar) ← volta ao automático
  2. Texto
  3. Número inteiro
  4. Número decimal
  5. Moeda (R$)
  6. CPF
  7. CNPJ
  8. Telefone
  9. CEP
  10. Data (dd/mm/aaaa)
  11. Data por extenso
  12. Percentual
  13. Código (preservar zeros)
  14. Booleano (Sim/Não)
- Após seleção: atualiza prévia imediatamente

---

## 7. Thread de geração

```python
class ThreadGeracao(QThread):
    progresso = Signal(int, int, str)   # atual, total, nome_arquivo
    erro = Signal(str, str)             # nome_arquivo, mensagem_erro
    concluido = Signal(list)            # lista de ResultadoGeracao
```

- Roda em background (nunca trava a UI)
- `cancelar()` seta flag que o loop verifica
- Relatório final: lista de `{"arquivo": str, "sucesso": bool, "erro": str|None}`

---

## 8. Tratamento de erros

- Erro em 1 linha da planilha: loga e continua para a próxima
- Variável não mapeada: substitui por string vazia (não deixa `{{VAR}}` no documento)
- Arquivo de saída já existe: adiciona `_2`, `_3`...
- Template inválido (sem variáveis): avisa mas permite continuar
- PDF falhou: informa qual arquivo mas mantém o DOCX gerado
- Mensagens de erro: "Linha 5 (João Silva): CPF com formato inválido"

---

## 9. Detecção automática de tipo (heurística)

```python
def detectar_tipo(nome_coluna: str, valor) -> str:
    nome = nome_coluna.lower()
    if "cpf" in nome: return "cpf"
    if "cnpj" in nome: return "cnpj"
    if "cep" in nome: return "cep"
    if any(x in nome for x in ["tel", "fone", "celular"]): return "telefone"
    if any(x in nome for x in ["data", "dt_", "_dt", "nascimento"]): return "data"
    if any(x in nome for x in ["valor", "salario", "preco", "custo", "total"]): return "moeda"
    if "%" in nome or "perc" in nome: return "percentual"
    if isinstance(valor, bool): return "booleano"
    if isinstance(valor, (int, float)):
        if isinstance(valor, float) and valor == int(valor): return "inteiro"
        return "decimal"
    return "texto"
```
