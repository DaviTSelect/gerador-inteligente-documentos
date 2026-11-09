# Gerador Inteligente de Documentos

Aplicação desktop que preenche automaticamente documentos Word a partir de planilhas Excel/CSV ou preenchimento manual, e converte para PDF.

## Repositório GitHub

[github.com/DaviTSelect/gerador-inteligente-documentos](https://github.com/DaviTSelect/gerador-inteligente-documentos)

## Código-Fonte

O código-fonte principal está em [`gerador_documentos/`](gerador_documentos/).

Consulte o [README do projeto](gerador_documentos/README.md) para instruções completas de instalação e uso.

## Tecnologias

- Python 3.10+
- PySide6 (interface gráfica)
- python-docx (documentos Word)
- openpyxl (planilhas Excel)
- PyInstaller (distribuição como executável)

## Início Rápido

```powershell
cd gerador_documentos
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Publicar nova versão

> **Fluxo completo:** altere `gerador_documentos/version.txt` → commite → rode `release.bat`

**1. Atualize a versão** em [gerador_documentos/version.txt](gerador_documentos/version.txt):

```
1.1.0
```

**2. Atualize `CHANGELOG.md`** com as entradas da versão.

**3. Commite e envie:**

```bat
git add gerador_documentos\version.txt CHANGELOG.md
git commit -m "release: v1.1.0"
git push origin main
```

**4. Execute `release.bat`** na pasta `gerador_documentos/` (duplo clique):

O script verifica testes, compila `GeradorDocumentos.exe` via PyInstaller, calcula SHA-256,
cria a tag, publica a release no GitHub com o `.exe` e o `.sha256` anexados.

Pré-requisito único: `gh auth login` (uma vez por máquina).

## Build local (sem publicar)

```powershell
cd gerador_documentos
.\build.bat
# Resultado em: gerador_documentos/dist/GeradorDocumentos.exe
```

## Releases

Ver pasta [`releases/`](releases/) para histórico de versões e notas.

## Padrão Corporativo

Este projeto segue o [Padrão de Engenharia da Empresa](../PADRAO_EMPRESA/specs/00_PADRAO_GERAL.spec.md).
Categoria: **DESKTOP** (app GUI, distribuído como executável Windows).
