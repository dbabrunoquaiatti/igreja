# 🚀 Início Rápido

## 1️⃣ Instalar Dependências

### Windows
```bash
# Duplo-clique em setup.bat
# ou execute no cmd/PowerShell:
pip install -r requirements.txt
```

### Linux/Mac
```bash
chmod +x setup.sh
./setup.sh
# ou
pip3 install -r requirements.txt
```

## 2️⃣ Executar o Script

### Opção A: Versão Simples (com credenciais no código)
```bash
python webscraping_grex.py
```

### Opção B: Versão Segura (com variáveis de ambiente) ⭐ RECOMENDADO

#### Windows (PowerShell):
```powershell
$env:GREX_EMAIL="quaiattibruno@gmail.com"
$env:GREX_PASSWORD="Temp#2032435@"
python webscraping_grex_secure.py
```

#### Windows (CMD):
```cmd
set GREX_EMAIL=quaiattibruno@gmail.com
set GREX_PASSWORD=Temp#2032435@
python webscraping_grex_secure.py
```

#### Linux/Mac:
```bash
export GREX_EMAIL="quaiattibruno@gmail.com"
export GREX_PASSWORD="Temp#2032435@"
python3 webscraping_grex_secure.py
```

## 3️⃣ Verificar Resultado

O arquivo será salvo em:
```
data/encontro.xlsx
```

## ⚡ Solução Rápida de Problemas

| Erro | Solução |
|------|---------|
| `ModuleNotFoundError` | Execute: `pip install -r requirements.txt` |
| Chrome não abre | Feche todas as abas/janelas do Chrome primeiro |
| Login falha | Verifique credenciais e conexão de internet |
| Arquivo não baixa | Aguarde 5-10 segundos após confirmação |

## 📚 Documentação Completa

Veja `README_WEBSCRAPING.md` para:
- Configurações avançadas
- Troubleshooting detalhado
- Integração com agendadores de tarefas
- Customizações

---

**Dúvidas?** Leia o README_WEBSCRAPING.md para documentação completa.
