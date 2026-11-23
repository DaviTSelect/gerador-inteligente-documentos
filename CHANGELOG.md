# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

---

## [1.1.2] - 2026-11-23

### Corrigido
- `gerador_documentos/requirements.txt`: pin `chardet<5.0` — chardet 5.x usa extensões `_mypyc` compiladas que o PyInstaller não coleta, causando crash "No module named 'chardet.pipeline.confusion_mypyc'"
- `gerador_documentos/GeradorDocumentos.spec`: `collect_all('lxml')` restaurado — havia sido removido acidentalmente; a ausência causaria crash "cannot import name 'etree' from 'lxml'"

## [1.1.1] - 2026-11-12

### Corrigido
- `GeradorDocumentos.spec`: `collect_all('lxml')` adicionado — `lxml.etree` não era incluído no executável, causando crash ao abrir com "cannot import name 'etree' from 'lxml'"

## [1.0.0] - 2026-11-04

### Adicionado
- Versão inicial: preenchimento de documentos Word com variáveis `{{CAMPO}}`
- Leitura de planilha Excel/CSV para geração em lote
- Preenchimento manual para documento único
- Conversão para PDF via Microsoft Word
- Interface PySide6
- Atualização automática via GitHub Releases
- Build com PyInstaller
