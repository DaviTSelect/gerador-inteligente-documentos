# Como Contribuir

## Configurar Ambiente

```powershell
git clone https://github.com/DaviTSelect/gerador-inteligente-documentos.git
cd gerador-inteligente-documentos/gerador_documentos

python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Executar

```powershell
python main.py
```

## Executar Testes

```powershell
python -m pytest tests -v
```

## Build

```powershell
.\build.bat
# Resultado em: dist/GeradorDocumentos.exe
```

## Processo de Release

1. Atualizar `gerador_documentos/version.txt` com o novo número
2. Atualizar `CHANGELOG.md` (mover `[Não lançado]` para `[x.y.z] - YYYY-MM-DD`)
3. Criar pasta `releases/vX.Y.Z/` com `RELEASE.md`
4. Commitar e enviar para o GitHub (`git push`)
5. Na pasta `gerador_documentos`, executar `.\release.bat`

O `release.bat` roda os testes, compila, cria a tag `vX.Y.Z` e publica a
Release com o executável e o `.sha256`. Requer o GitHub CLI autenticado
(`gh auth login`). Não há publicação automática: **uma tag sem Release não
atualiza ninguém.**

As Releases são publicadas sem a marca "Latest" (`--latest=false`), que deve
permanecer na v1.1.1 enquanto houver instalações 1.1.x: o atualizador antigo
entra em loop de reinício se enxergar uma versão nova nessa marca. Não marque
"Set as the latest release" no site do GitHub.

## Convenção de Commits

| Prefixo | Uso |
|---------|-----|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `docs:` | Documentação |
| `release:` | Preparação de release |
