# Gerador Inteligente de Documentos

Aplicação desktop que preenche automaticamente documentos Word a partir de planilhas Excel/CSV ou preenchimento manual.

---

## O que o sistema faz

- Lê um arquivo Word (`.docx`) com variáveis no formato `{{NOME}}`
- Detecta automaticamente todas as variáveis no documento
- Preenche as variáveis com dados de uma planilha Excel (`.xlsx`) ou CSV (`.csv`)
- Gera um documento Word separado por linha da planilha
- Ou gera um único documento com dados digitados manualmente
- Converte os documentos gerados para PDF (requer Microsoft Word instalado)

---

## Requisitos

- **Python 3.10 ou superior** — [download em python.org](https://python.org)
- **Microsoft Word** — necessário apenas para a conversão em PDF

---

## Instalação passo a passo

### 1. Instalar Python

Acesse [python.org](https://python.org) e baixe o instalador para Windows.

**Importante:** na tela de instalação, marque a opção **"Add Python to PATH"** antes de clicar em Install.

Para confirmar que Python foi instalado:
```
python --version
```
Deve aparecer algo como `Python 3.12.0`.

### 2. Baixar o projeto

Coloque a pasta `gerador_documentos` em qualquer local do seu computador.

### 3. Instalar as dependências

Abra o **Prompt de Comando** (Windows), navegue até a pasta do projeto e execute:

```cmd
cd C:\caminho\para\gerador_documentos
pip install -r requirements.txt
```

Aguarde a instalação terminar. Pode levar alguns minutos.

---

## Como executar

Na pasta do projeto, execute:

```cmd
python main.py
```

A janela do programa abrirá automaticamente.

---

## Como usar — passo a passo

### Modo Planilha

1. **Etapa 1 — Documento template**
   - Clique em "Selecionar arquivo .docx"
   - Escolha o arquivo Word com as variáveis `{{NOME_DA_VARIAVEL}}`
   - As variáveis detectadas aparecem como pílulas coloridas

2. **Etapa 2 — Modo de preenchimento**
   - Clique no card "Planilha Excel"

3. **Etapa 3 — Configuração dos dados**
   - Clique em "Selecionar planilha"
   - Para cada variável do template, escolha a coluna correspondente na planilha
   - Clique no botão **[Tipo ▾]** para definir como o dado será formatado (CPF, Data, Moeda, etc.)
   - A coluna "Prévia" mostra como o dado ficará no documento

4. **Etapa 4 — Destino**
   - Escolha a pasta onde os documentos serão salvos
   - Defina o padrão de nome (ex: `Contrato_{{NOME}}_{{DATA}}.docx`)
   - Marque "Modo teste" para gerar apenas o primeiro documento antes de processar tudo
   - Clique em **"Iniciar geração →"**

5. **Etapa 5 — Acompanhe a geração**
   - A barra de progresso mostra quantos documentos foram gerados
   - A lista mostra cada arquivo concluído em tempo real
   - Ao final, clique em "Abrir pasta de destino"

### Modo Manual

No passo 2, selecione "Preenchimento manual". Um campo de texto aparecerá para cada variável. Preencha e clique em "Próximo →". Será gerado exatamente 1 documento.

---

## Tipos de formatação disponíveis

Ao clicar em **[Tipo ▾]** na tabela de mapeamento, você escolhe como o dado será formatado:

| Tipo | Exemplo de entrada | Resultado no documento |
|---|---|---|
| Texto | Ana Silva | Ana Silva |
| Número inteiro | 42.0 | 42 |
| Número decimal | 1234.56 | 1.234,56 |
| Moeda (R$) | 1234.56 | R$ 1.234,56 |
| CPF | 12345678900 | 123.456.789-00 |
| CNPJ | 12345678000195 | 12.345.678/0001-95 |
| Telefone | 11999998888 | (11) 99999-8888 |
| CEP | 1310100 | 01310-100 |
| Data | 2026-11-04 | 04/11/2026 |
| Data por extenso | 2026-11-04 | 04 de novembro de 2026 |
| Percentual | 0.15 | 15% |
| Código (zeros) | 00123 | 00123 |
| Booleano | True | Sim |

---

## Gerar executável (.exe)

Para distribuir o programa sem precisar instalar Python:

1. Instale o PyInstaller:
   ```
   pip install pyinstaller
   ```

2. Gere o executável:
   ```
   pyinstaller --onefile --windowed main.py
   ```

3. O arquivo `.exe` estará na pasta `dist/`.

---

## Dúvidas

Consulte os arquivos:
- `GUIA_DO_PROJETO.md` — como o código está organizado
- `GUIA_DE_ERROS.md` — soluções para os erros mais comuns
