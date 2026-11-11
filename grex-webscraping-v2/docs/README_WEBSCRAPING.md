# Web Scraping GREX - Guia de Uso

## 📋 Requisitos

### Instalação de Dependências

```bash
pip install selenium webdriver-manager
```

### Estrutura de Pastas

O script criará automaticamente a pasta `data/` onde o arquivo será salvo como `encontro.xlsx`.

## 🚀 Como Usar

### Opção 1: Execução Direta (Simples)

```bash
python webscraping_grex.py
```

O script executará todos os passos automaticamente:
1. Login no portal GREX
2. Navegação para página de participantes
3. Click no botão de exportação
4. Seleção do tipo de exportação
5. Confirmação e download
6. Renomeação do arquivo para `encontro.xlsx`

### Opção 2: Com Variáveis de Ambiente (MAIS SEGURO ⭐)

#### Windows (PowerShell):
```powershell
$env:GREX_EMAIL="quaiattibruno@gmail.com"
$env:GREX_PASSWORD="Temp#2032435@"
python webscraping_grex.py
```

#### Windows (CMD):
```cmd
set GREX_EMAIL=quaiattibruno@gmail.com
set GREX_PASSWORD=Temp#2032435@
python webscraping_grex.py
```

#### Linux/Mac:
```bash
export GREX_EMAIL="quaiattibruno@gmail.com"
export GREX_PASSWORD="Temp#2032435@"
python webscraping_grex.py
```

**Para usar essa abordagem, descomente as linhas no script:**

```python
# CREDENCIAIS - Use variáveis de ambiente
email = os.getenv("GREX_EMAIL")
password = os.getenv("GREX_PASSWORD")

if not email or not password:
    print("❌ Erro: Configure as variáveis de ambiente GREX_EMAIL e GREX_PASSWORD")
    exit(1)
```

### Opção 3: Arquivo .env (Recomendado para Desenvolvimento)

Crie um arquivo `.env` na mesma pasta:

```
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
```

Depois instale python-dotenv:
```bash
pip install python-dotenv
```

E modifique o início do `main()`:
```python
from dotenv import load_dotenv

def main():
    load_dotenv()
    email = os.getenv("GREX_EMAIL")
    password = os.getenv("GREX_PASSWORD")
    # ... resto do código
```

## ⚙️ Configurações Opcionais

### Modo Headless (sem janela visível)

No arquivo `webscraping_grex.py`, na função `setup_driver()`, descomente:

```python
chrome_options.add_argument("--headless")
```

### Timeout Customizado

Mude o valor de timeout (segundos) em `WebDriverWait()`:

```python
wait = WebDriverWait(driver, 20)  # 20 segundos em vez de 10
```

## 🔍 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Module not found: selenium" | Execute: `pip install selenium webdriver-manager` |
| "Chrome driver não encontrado" | O `webdriver-manager` baixará automaticamente |
| Arquivo não baixa | Aumente o `time.sleep()` na função `confirm_export()` |
| Seletor não funciona | O HTML pode ter mudado; inspecione a página (F12) |
| Timeout ao logar | Verifique credenciais e conexão de internet |

## 📊 Output Esperado

```
============================================================
🚀 INICIANDO AUTOMAÇÃO GREX
============================================================
🔐 Acessando página de login...
📧 Preenchendo email...
🔑 Preenchendo senha...
🖱️  Clicando no botão de login...
✅ Login realizado com sucesso!
🔗 Navegando para página de participantes...
✅ Página de participantes carregada!
📤 Clicando no botão de exportação...
✅ Botão clicado! Modal abrindo...
📋 Selecionando tipo de exportação...
✅ Opção selecionada!
✔️  Confirmando exportação...
✅ Exportação iniciada!
📁 Processando arquivo baixado...
✅ Arquivo salvo em: C:\...\data\encontro.xlsx

============================================================
✨ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!
============================================================
```

## ⚠️ Notas de Segurança

1. **Nunca commite credenciais no Git**: Adicione `.env` ao `.gitignore`
2. **Use variáveis de ambiente** em produção
3. **Credenciais no código** devem ser apenas para testes locais
4. **Senhas fortes**: A senha fornecida deve estar protegida
5. **MFA**: Se a conta tiver autenticação de dois fatores, será necessário ajuste manual

## 📝 Customizações Futuras

O script pode ser facilmente expandido para:
- [ ] Salvar dados em banco de dados
- [ ] Enviar email com o arquivo
- [ ] Agendar execução automática
- [ ] Extrair dados do Excel e processar
- [ ] Adicionar logs em arquivo

## 💡 Exemplos de Uso Avançado

### Executar múltiplas vezes:
```python
for i in range(5):
    main()
    time.sleep(60)  # Aguardar 1 minuto entre execuções
```

### Integrar com agendador:
```bash
# Windows Task Scheduler
# Linux crontab
# 0 9 * * * /usr/bin/python3 /path/to/webscraping_grex.py
```

## 📞 Suporte

Se encontrar erros, verifique:
- ✅ Credenciais corretas
- ✅ Conexão de internet
- ✅ Chrome instalado e atualizado
- ✅ Permissões de pasta `data/`
- ✅ Selectors ainda são válidos (conteúdo HTML pode mudar)
