# Guia de Erros — Gerador Inteligente de Documentos

Este guia lista os erros mais comuns, suas causas e como corrigi-los.

---

## Erros na instalação

### `pip` não é reconhecido como comando

**Causa:** Python não foi adicionado ao PATH durante a instalação.

**Solução:**
1. Desinstale o Python
2. Reinstale marcando a opção **"Add Python to PATH"**
3. Feche e reabra o Prompt de Comando

---

### `No module named 'PySide6'` (ou outro módulo)

**Causa:** As dependências não foram instaladas.

**Solução:**
```cmd
pip install -r requirements.txt
```

---

### `ModuleNotFoundError: No module named 'planilhas'`

**Causa:** Você está executando `python` de uma pasta diferente da pasta `gerador_documentos`.

**Solução:** Certifique-se de estar dentro da pasta correta:
```cmd
cd C:\caminho\para\gerador_documentos
python main.py
```

---

## Erros ao abrir o template

### "Não foi possível ler o arquivo"

**Causa:** O arquivo pode estar corrompido, aberto em outro programa, ou não ser um .docx válido.

**Solução:**
1. Feche o arquivo no Word antes de usar o programa
2. Certifique-se que o arquivo tem extensão `.docx` (não `.doc`)
3. Tente salvar uma nova cópia no Word: Arquivo → Salvar Como → `.docx`

---

### As variáveis não aparecem como pílulas

**Causa:** O documento não contém variáveis no formato `{{VARIAVEL}}` (chaves duplas).

**Solução:**
- No Word, as variáveis devem ser escritas exatamente como `{{nome_da_variavel}}`
- Use apenas letras (maiúsculas ou minúsculas), números e underscore
- Exemplos válidos: `{{nome}}`, `{{cpf}}`, `{{DATA_NASCIMENTO}}`, `{{valor}}`
- Exemplos inválidos: `{nome}`, `[[nome]]`

---

### A variável `{{DATA}}` não aparece na lista

**Causa:** O Word dividiu a variável em múltiplos fragmentos XML internos. Por exemplo: `{{`, `DAT`, `A}}`.

**Solução:** O programa trata isso automaticamente. Se ainda assim não aparecer:
1. No Word, selecione o texto `{{DATA}}` inteiro
2. Delete-o e redigite do zero
3. Salve o arquivo

**Onde está no código:** `documentos.py` → funções `_colapsar_runs` e `_texto_do_paragrafo`

---

## Erros na planilha

### "A planilha não contém linhas de dados"

**Causa:** A planilha está vazia ou tem apenas cabeçalho.

**Solução:** Certifique-se que há pelo menos uma linha de dados abaixo do cabeçalho.

---

### CPF aparece como `1.23457e+10` no documento

**Causa:** A coluna CPF está sendo lida como número e o Python está formatando em notação científica.

**Solução:** No botão **[Tipo ▾]** ao lado da variável CPF, selecione o tipo **CPF**. O programa irá formatar corretamente com zeros à esquerda e pontuação.

Ou, na planilha Excel, formate a coluna como **Texto** antes de usar.

---

### Datas aparecem como números (`46400`)

**Causa:** O Excel armazena datas internamente como números. Se a célula não estiver formatada como data no Excel, pode aparecer como número serial.

**Solução:** No botão **[Tipo ▾]**, selecione o tipo **Data (dd/mm/aaaa)**. O programa converte automaticamente.

---

### CSV com caracteres estranhos (`Ã§`, `Ã©`, etc.)

**Causa:** O arquivo CSV está em encoding diferente do esperado (geralmente Latin-1 vs UTF-8).

**Solução:** O programa tenta detectar automaticamente. Se falhar:
1. Abra o CSV no Bloco de Notas
2. Vá em Arquivo → Salvar Como
3. No campo "Codificação", escolha **UTF-8**
4. Salve e use o novo arquivo

---

### CSV com colunas erradas (tudo em uma coluna)

**Causa:** O CSV usa ponto-e-vírgula como separador, mas o programa detectou vírgula (ou vice-versa).

**Solução:** O programa detecta automaticamente comparando vírgulas e pontos-e-vírgula. Se errar, abra o CSV em um editor de texto e verifique qual separador está sendo usado. Se necessário, troque todos os separadores.

**Onde está no código:** `planilhas.py` → função `ler_csv`

---

### Células vazias aparecem como "None" ou "nan" no documento

**Causa:** Isso não deveria acontecer — é um bug.

**Solução:**
- Verifique se o tipo selecionado no **[Tipo ▾]** está correto
- **Onde corrigir no código:** `planilhas.py` → função `_e_vazio`. Adicione o caso específico que está passando.

---

## Erros na geração

### "Variável {{variavel}} não substituída no documento"

**Causa:** A variável no template e o mapeamento não coincidem exatamente.

**Solução:**
1. Verifique se a variável no template usa exatamente o mesmo nome (maiúsculas/minúsculas importam)
2. Verifique se a coluna correta foi selecionada no mapeamento
3. Recarregue o template na etapa 1

---

### "Acesso negado" ao salvar o arquivo

**Causa:** A pasta de destino não existe ou o usuário não tem permissão de escrita.

**Solução:**
- Escolha uma pasta dentro de `Documentos`, `Desktop` ou outro local que você tenha acesso
- Evite pastas do sistema como `C:\Windows` ou `C:\Program Files`

---

### O arquivo de saída está bloqueado / "sendo usado por outro processo"

**Causa:** O arquivo já existe e está aberto no Word.

**Solução:** Feche o arquivo no Word antes de gerar novamente.

O programa nunca sobrescreve arquivos existentes — ele cria `_2`, `_3`, etc. Se um arquivo está aberto, o sistema de arquivos bloqueia qualquer operação nele.

---

## Erros na conversão para PDF

### "A biblioteca docx2pdf não está instalada"

**Solução:**
```cmd
pip install docx2pdf
```

---

### "Falha ao converter para PDF — verifique se o Microsoft Word está instalado"

**Causa:** O `docx2pdf` usa o Word instalado no Windows. Se Word não estiver presente, a conversão falha.

**Solução:**
- Instale o Microsoft Word
- Ou desmarque a opção "Converter para PDF" na etapa 4

**Nota:** Os documentos `.docx` sempre são gerados, independente do PDF.

---

### A conversão para PDF é muito lenta

**Causa:** O `docx2pdf` abre e fecha o Word para cada arquivo. Em lotes grandes, isso pode demorar.

**Solução:**
- Use o "Modo teste" primeiro para verificar o resultado
- Para grandes volumes, considere gerar o DOCX e converter manualmente no Word (Arquivo → Exportar → PDF)

---

## Tabela rápida de erros × solução

| Mensagem de erro | Causa | Solução |
|---|---|---|
| `ModuleNotFoundError` | Dependências não instaladas | `pip install -r requirements.txt` |
| "Arquivo não encontrado" | Caminho inválido | Verifique se o arquivo ainda existe |
| "A planilha está vazia" | Sem dados na planilha | Adicione ao menos uma linha de dados |
| CPF/CNPJ com formato errado | Tipo não selecionado | Clique em [Tipo ▾] e escolha CPF/CNPJ |
| Data como número | Tipo não selecionado | Clique em [Tipo ▾] e escolha Data |
| PDF não gerado | Word não instalado | Instale o Word ou desative o PDF |
| "Acesso negado" ao salvar | Pasta protegida | Use Documentos ou Desktop |
| Variável não substituída | Nome diferente no template | Verifique o nome exato em {{variavel}} |

---

## Como pedir ajuda

Ao reportar um problema, inclua:
1. O que você tentou fazer
2. A mensagem de erro exata (copie do terminal ou da tela)
3. O nome do arquivo que estava sendo processado
4. O número da linha da planilha (se aplicável)
