# Guia do Projeto — Gerador Inteligente de Documentos

Este guia explica como o código está organizado e onde encontrar cada funcionalidade.

---

## Mapa dos arquivos

```
gerador_documentos/
├── main.py          ← Ponto de entrada: inicia a aplicação
├── app.py           ← Interface gráfica completa (PySide6)
├── documentos.py    ← Leitura e preenchimento de arquivos Word
├── planilhas.py     ← Leitura de Excel/CSV e formatação de dados
├── pdf.py           ← Conversão de Word para PDF
├── requirements.txt ← Lista de dependências Python
├── tests/           ← Testes automáticos
│   ├── test_planilhas.py
│   ├── test_documentos.py
│   └── test_pdf.py
└── docs/            ← Documentação técnica interna
```

---

## main.py — Ponto de entrada

Arquivo mais simples do projeto. Faz três coisas:
1. Cria a aplicação PySide6 (`QApplication`)
2. Instancia a janela principal (`MainWindow`)
3. Exibe a janela e aguarda o usuário fechar

**Quando modificar:** somente se precisar de configurações globais da aplicação (tema, fonte padrão, etc.)

---

## app.py — Interface gráfica

É o maior arquivo, mas está organizado por etapas. Cada etapa é uma classe separada.

### Classes principais

| Classe | Responsabilidade |
|---|---|
| `MainWindow` | Janela principal; coordena sidebar + navegação |
| `Sidebar` | Barra lateral esquerda com indicadores de etapa |
| `EtapaIndicador` | Um item na sidebar (círculo + nome + estado) |
| `PaginaTemplate` | Etapa 1: selecionar o .docx |
| `PaginaModo` | Etapa 2: escolher planilha ou manual |
| `PaginaPlanilha` | Etapa 3A: mapear colunas da planilha |
| `PaginaManual` | Etapa 3B: digitar valores manualmente |
| `PaginaDestino` | Etapa 4: pasta de saída e opções |
| `PaginaGeracao` | Etapa 5: barra de progresso e resultado |
| `MapeamentoLinha` | Uma linha da tabela de mapeamento |
| `BotaoTipo` | Botão [Tipo ▾] com menu de tipos de dado |
| `ThreadGeracao` | Thread que gera os documentos em background |

### Como a navegação funciona

`MainWindow.ir_para_etapa(numero)` é o coração da navegação:
1. Remove o widget atual do `QStackedWidget`
2. Instancia o widget da nova etapa
3. Conecta os botões "Voltar" e "Próximo"
4. Atualiza a sidebar

Todos os dados selecionados pelo usuário ficam em `self.dados_sessao` (um dict). Cada etapa lê e escreve nesse dicionário.

### Como adicionar uma nova etapa

1. Crie uma nova classe `PaginaMinhaEtapa(QWidget)` em `app.py`
2. Adicione um `elif numero == 6:` no método `ir_para_etapa`
3. Atualize a constante `ETAPAS` na classe `Sidebar`

---

## documentos.py — Leitura e preenchimento do Word

### Como funciona a leitura do DOCX

A biblioteca `python-docx` representa um arquivo Word como uma árvore de objetos:
- `Document` → tem `paragraphs` e `tables`
- Cada parágrafo tem `runs` (fragmentos de texto com formatação)
- O texto visível de um parágrafo = junção de todos os runs

### Como as variáveis são identificadas

A função `extrair_variaveis(caminho_docx)` usa uma expressão regular para buscar `{{NOME}}` em:
- Todos os parágrafos do corpo
- Células de tabelas
- Cabeçalhos e rodapés

### O problema dos runs fragmentados

**Problema:** o Word frequentemente divide uma variável em múltiplos fragmentos XML:
```
Run 1: "{{"
Run 2: "NOM"
Run 3: "E}}"
```

Isso acontece porque o Word salva formatação intermediária (negrito parcial, etc.).

**Solução:** a função `_colapsar_runs(paragrafo)` junta todos os runs em um único, preservando a formatação do primeiro. Isso é feito antes de qualquer substituição.

### Como funciona a geração

1. Faz uma **cópia** do template com `shutil.copy2` (nunca modifica o original)
2. Abre a cópia com `Document()`
3. Chama `_substituir_no_documento()` que percorre parágrafos, tabelas, header e footer
4. Para cada variável encontrada, substitui pelo valor do dict `dados`
5. Variáveis não mapeadas viram string vazia `""`
6. Salva e retorna o caminho

---

## planilhas.py — Leitura e tratamento de dados

### Como funciona a leitura do Excel

Usa `openpyxl` com `data_only=True` para obter os valores calculados (não as fórmulas).

A primeira linha da planilha é sempre tratada como cabeçalho.

### Como funciona a leitura do CSV

1. Lê os bytes do arquivo com `chardet` para detectar o encoding
2. Tenta decodificar com `utf-8-sig` → `utf-8` → `latin-1`
3. Detecta o separador comparando a contagem de `,` e `;` na primeira linha
4. Lê com `pandas.read_csv`

### Como funciona a formatação

A função principal é `formatar_valor(valor, tipo)`:
- Se o valor for vazio (`None`, `NaN`, `NaT`, `""`), retorna `""`
- Caso contrário, chama o formatador específico do tipo

Cada tipo tem uma função privada `_fmt_<tipo>`:
- `_fmt_cpf`: extrai dígitos, zfill(11), aplica máscara `XXX.XXX.XXX-XX`
- `_fmt_data`: converte para objeto `date` via `_para_date()`, formata
- `_fmt_moeda`: formata com separador de milhar e 2 casas decimais

### Como adicionar um novo tipo

1. Crie uma função `_fmt_meunovo(valor) -> str` em `planilhas.py`
2. Adicione `"meunovo": _fmt_meunovo` no dict `_FORMATADORES`
3. Adicione `"meunovo"` na lista `TIPOS_DISPONIVEIS`
4. Adicione o nome amigável em `BotaoTipo.NOMES_AMIGAVEIS` em `app.py`
5. Escreva um teste em `tests/test_planilhas.py`

---

## pdf.py — Conversão para PDF

### Como funciona

Usa a biblioteca `docx2pdf` que aciona o Microsoft Word via automação COM (Windows):
1. `converter_para_pdf(caminho_docx)` chama `docx2pdf.convert()`
2. O Word abre o arquivo silenciosamente, exporta para PDF e fecha
3. O PDF é salvo na mesma pasta com o mesmo nome, extensão `.pdf`

### Requisitos

**Microsoft Word precisa estar instalado.** Sem Word, a conversão falha com uma mensagem clara.

A conversão funciona mesmo com Word fechado — `docx2pdf` abre e fecha o Word automaticamente.

### Aviso no terminal

Durante a conversão, pode aparecer uma mensagem `Windows fatal exception: code 0x800706be`. Isso é um comportamento normal da lib `tqdm` interagindo com COM — não afeta a geração dos arquivos.

---

## Como rodar os testes

```cmd
cd gerador_documentos
python -m pytest tests/ -v
```

Os testes de PDF são ignorados automaticamente se Word não estiver disponível.
