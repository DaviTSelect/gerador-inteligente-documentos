# Release v1.0.0 — Gerador Inteligente de Documentos

## GitHub Release Info

| Campo          | Valor                                      |
|----------------|--------------------------------------------|
| **Tag**        | `v1.0.0`                                   |
| **Target**     | `master`                                   |
| **Título**     | Gerador Inteligente de Documentos v1.0.0   |
| **Tipo**       | Latest release                             |
| **Anexo**      | `GeradorDocumentos.exe`                    |

---

## Release Notes (cole no campo "Release description")

### 🚀 Primeira versão — Gerador Inteligente de Documentos

Aplicativo desktop para **preencher templates Word automaticamente** com dados de planilhas Excel/CSV ou preenchimento manual, com suporte a exportação em Word e PDF.

---

### ✨ Funcionalidades

#### Fluxo de trabalho em 5 etapas
1. **Template** — Selecione o arquivo `.docx` com as variáveis `{{NOME_DA_VARIAVEL}}`; o app detecta e lista todas as variáveis automaticamente.
2. **Modo de preenchimento** — Escolha entre **Planilha** (Excel/CSV) ou **Manual** (formulário).
3. **Configuração dos dados** — Mapeie colunas da planilha às variáveis do template, com visualização de prévia dos valores.
4. **Destino dos arquivos** — Defina pasta de saída e padrão de nome de arquivo com **pills clicáveis** para inserir variáveis (ex: `Documento_{{NOME}}.docx`).
5. **Geração** — Barra de progresso em tempo real, log de atividade e resumo de erros.

#### Formatos de saída
- **Word** (`.docx`) — gerado diretamente pelo python-docx.
- **PDF** — conversão automática via Microsoft Word COM; o `.docx` intermediário é removido.

#### Preservação de formatação
- Cores, negrito, itálico e tamanho de fonte do template são preservados.
- Cor de marcação de placeholders (`{{VAR}}` em vermelho, por exemplo) é removida automaticamente no documento final.

#### Atualização automática
- Ao abrir, o app verifica silenciosamente a última release no GitHub.
- Status exibido no rodapé da sidebar com ponto colorido (🟡 verificando · 🟢 atualizado · ⚫ sem conexão).
- Se houver nova versão: download automático em background com progresso e reinício automático.

#### Interface
- Sidebar escura com indicadores de etapa (pendente / ativo / concluído).
- Cards com rolagem para mapeamento de muitas variáveis.
- Suporte a logo/ícone na janela, barra de tarefas e executável compilado.
- Botão laranja "Selecionar pasta" com abertura correta de pastas no Windows.

---

### 📋 Requisitos

- **Windows 10/11**
- **Microsoft Word** instalado (necessário para conversão em PDF)
- Sem instalação adicional necessária ao usar o `.exe`

---

### 📦 Como instalar

1. Baixe o arquivo `GeradorDocumentos.exe` abaixo.
2. Execute diretamente — não é necessário instalar.
3. Para geração de PDF, o Microsoft Word precisa estar instalado na máquina.

---

### 🛠 Stack técnica

| Componente    | Biblioteca          |
|---------------|---------------------|
| Interface     | PySide6             |
| Templates     | python-docx         |
| Planilhas     | openpyxl + pandas   |
| Encoding CSV  | chardet             |
| PDF           | win32com (pywin32)  |
| Auto-update   | GitHub Releases API |
| Compilação    | PyInstaller         |

---

### 🐛 Correções incluídas nesta versão

- Nome de arquivo gerado não produz mais extensão dupla `.pdf.docx` ao usar modo PDF.
- Cor explícita de placeholders no template não contamina o texto final.
- Abertura de pasta de destino usa `os.startfile` — funciona corretamente em caminhos com espaços e acentos.
- Conversão PDF usa `win32com.client` diretamente, eliminando o erro `NoneType has no attribute 'write'` do `docx2pdf`.
