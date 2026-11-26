# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versões seguem [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

---

## [1.2.1] - 2026-11-26

### Corrigido
- Verificação de atualização em outros computadores: o certificado do GitHub passa a ser validado pelo próprio Windows, que obtém certificados raiz ausentes e aceita os cadastrados pela rede da empresa.
- Mensagens de falha do atualizador indicam o motivo (certificado, endereço não encontrado, tempo esgotado, proxy, bloqueio por firewall ou antivírus).
- Mapeamento automático liga variáveis a colunas com as mesmas palavras em outra ordem (`{{Valor_PSU}}` → `PSU_VALOR`), ignora acentos e prefere o nome idêntico.
- Conversão para PDF tenta até 3 vezes quando o Word recusa uma chamada, e uma falha ao fechar o Word não descarta mais um PDF já gerado.

---

## [1.2.0] - 2026-11-26

### Corrigido
- **Formatação perdida no preenchimento**: o gerador juntava o parágrafo inteiro no primeiro run, aplicando a formatação dele a todo o texto (negrito sumia ou aparecia onde não devia). Agora só o texto do marcador é alterado e o valor herda a formatação do marcador. A cor do marcador também passa a ser preservada.
- Marcadores em hyperlinks, caixas de texto, tabelas aninhadas, cabeçalhos de primeira página/páginas pares e notas de rodapé agora são preenchidos.
- **Atualizador**: validação de tamanho, SHA-256 e formato antes de instalar; autoverificação do novo executável; troca por rename sem script `.bat` (funciona em pastas com acentos); backup do executável anterior.
- **"Failed to load Python DLL" após atualizar**: o novo processo herdava o ambiente do PyInstaller do processo antigo.
- Conversão para PDF não fecha mais um Word que o usuário já tenha aberto.
- `release.bat` permite publicar a Release de uma tag que foi enviada sem Release.
- Atualização não reinicia mais o programa no meio do trabalho: oferece "Instalar e reiniciar".
- Executável cuja versão difere da Release é rejeitado (evita atualização em loop).
- PDFs de mesmo nome não se sobrescrevem; quebras de linha não quebram o nome do arquivo.
- `release.bat` recusa publicar com alterações sem commit ou sem SHA-256.
- A Release é publicada sem a marca "Latest" para não prender a v1.1.1 em loop de reinício; quem usa 1.1.x precisa baixar a 1.2.0 manualmente uma vez.

### Adicionado
- Mensagens de erro de atualização com botão "Tentar novamente" e log em `%LOCALAPPDATA%\GeradorDocumentos\atualizador.log`.
- Nomes de variáveis com espaços e acentos (`{{ENDEREÇO}}`, `{{ Nome do Aluno }}`).

---

## [1.1.9] - 2026-11-23

### Corrigido
- **"Failed to load Python DLL" ao reiniciar após update**: o PyInstaller reutilizava um diretório `_MEI*` antigo/corrompido no `%TEMP%`, onde `python312.dll` estava ausente. Corrigido com `runtime_tmpdir='.'` no spec (extração ao lado do exe, não em `%TEMP%`) e limpeza dos `_MEI*` antigos no bat antes de iniciar o novo exe.

## [1.1.8] - 2026-11-23

### Teste
- Versão de validação do fluxo de atualização automática após correção do rename (v1.1.7)

## [1.1.7] - 2026-11-23

### Corrigido
- **Substituição do exe bloqueada pelo Windows Defender**: `move` e `copy` falham com "Acesso negado" porque o Defender mantém um handle no exe recém-executado. No NTFS, `ren` funciona mesmo com o arquivo bloqueado (altera apenas a entrada de diretório). Novo fluxo: `ren exe → exe.old` | `ren exe.new → exe` | `start exe`. O `.old` é apagado ao final (ou descartado silenciosamente se ainda bloqueado).

## [1.1.6] - 2026-11-23

### Corrigido
- **Segunda janela ao atualizar**: `QTimer.singleShot` chamado de thread de background não é thread-safe no Qt — o timer nunca disparava, o app não fechava, e o bat abria uma segunda instância. Corrigido usando sempre o sinal `_sinal_restart` (emitido cross-thread via Qt) + flag `_exe_update` para distinguir "fechar" de "reiniciar".
- **Bat sem retry**: se o `move` falhasse (exe ainda em uso), o bat iniciava o exe antigo sem tentar novamente. Agora tenta a cada 2 s até o `move` ter sucesso.

## [1.1.5] - 2026-11-23

### Teste
- Versão de validação do fluxo de atualização automática após correções da v1.1.4

## [1.1.4] - 2026-11-23

### Corrigido
- **Loop de atualização infinita**: `reiniciar()` era chamado mesmo em atualizações via `.exe`, relançando o executável antigo antes do bat conseguir substituí-lo. Agora `aplicar_atualizacao` retorna `False` para `.exe` e o app apenas fecha — o bat cuida do restart.
- **Bat criado em `_MEIPASS`**: o script de substituição era salvo dentro da pasta temporária do PyInstaller, que é deletada ao encerrar. Corrigido para salvar na pasta do executável.
- **Timeout do bat insuficiente**: aumentado de 2 s para 5 s para garantir que o processo encerrou antes de substituir o exe.
- **lxml.etree ausente no bundle**: `collect_all('lxml')` não captura os `.pyd` no lxml 6.x. Substituído por coleta explícita dos binários.

## [1.1.3] - 2026-11-23

### Teste
- Versão de validação do fluxo de atualização automática após correção do crash chardet/lxml (v1.1.2)

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
