# Contexto do Projeto para Agente IA

## O que este projeto faz

Aplicação desktop que preenche documentos Word (`.docx`) automaticamente substituindo variáveis `{{CAMPO}}` com dados de planilhas Excel/CSV. Pode converter para PDF e distribuir em lote. Distribui via GitHub Releases com atualização automática.

## Tecnologias

- Python 3.10+
- PySide6 (interface gráfica)
- python-docx (documentos Word)
- openpyxl (Excel)
- PyInstaller (executável Windows)

## Arquitetura

```
gerador_documentos/      ← pasta raiz do pacote
├── main.py              # ponto de entrada
├── app.py               # janela principal PySide6
├── documentos.py        # preenchimento de Word com variáveis
├── pdf.py               # conversão para PDF via Word COM
├── planilhas.py         # leitura de Excel/CSV
├── updater.py           # atualização automática (GitHub Releases API)
├── version.txt          # versão atual (ex: "1.0.0")
├── requirements.txt
└── tests/
    ├── test_documentos.py
    ├── test_pdf.py
    └── test_planilhas.py
```

## Como executar

```powershell
cd gerador_documentos
.\venv\Scripts\Activate.ps1
python main.py

# Testes
python -m pytest tests -v

# Build
.\build.bat
```

## Padrões do projeto

- Versão em `version.txt` (linha única, ex: `1.0.0`)
- Release notes em `releases/vX.Y.Z/RELEASE.md`
- Atualização automática via ZIP do GitHub Releases

## O que NÃO fazer

- Não commitar arquivos `.docx` de saída gerados pelo app
- Não commitar `dist/`, `build/`
- Não modificar `version.txt` sem criar entrada no CHANGELOG
