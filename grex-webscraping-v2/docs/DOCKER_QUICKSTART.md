# 🐳 Docker - Início Rápido

## ⚡ 30 Segundos para Começar

```bash
# 1. Configure credenciais (Windows PowerShell)
$env:GREX_EMAIL="quaiattibruno@gmail.com"
$env:GREX_PASSWORD="Temp#2032435@"

# 2. Execute
docker-compose up --build

# 3. Arquivo em: data/encontro.xlsx ✅
```

---

## 📝 Alternativa: Arquivo .env

Mais simples e reutilizável!

```bash
# 1. Crie arquivo .env na raiz do projeto
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@

# 2. Execute (Docker Compose lê .env automaticamente)
docker-compose up --build

# 3. Pronto! ✅
```

---

## 🖥️ Sistemas Operacionais

### Windows
```bash
# Duplo-clique em: docker-run.bat
# ou no PowerShell:
docker-compose up --build
```

### Linux/Mac
```bash
# Ou execute o script helper:
chmod +x docker-run.sh
./docker-run.sh

# ou direto:
docker-compose up --build
```

---

## 🐳 O que Acontece

1. **Build** - Cria imagem Docker (primeira vez)
2. **Setup** - Instala Chrome, Python, dependências
3. **Login** - Acessa GREX e faz login
4. **Download** - Baixa arquivo de participantes
5. **Salva** - Coloca em `data/encontro.xlsx`
6. **Finaliza** - Container encerra

---

## ✅ Verificar Resultado

```bash
# Arquivo gerado em:
data/encontro.xlsx

# Verificar
ls data/
```

---

## 🛑 Parar/Limpar

```bash
# Parar container
docker-compose down

# Limpar tudo
docker-compose down -v
docker image rm webscraping-grex
```

---

## 🔍 Ver Logs

```bash
docker-compose logs -f
```

---

## 📚 Mais Informações

- **Documentação completa**: Veja `DOCKER.md`
- **Customizações**: Leia `README_WEBSCRAPING.md`
- **Problemas**: Veja seção de troubleshooting em `DOCKER.md`

---

## 💡 Dicas

| Dica | Benefício |
|------|-----------|
| Use `.env` em vez de variáveis | Mais fácil e seguro |
| Docker Compose > Docker run | Menos comandos, mais organizado |
| Agende com cron/Task Scheduler | Automação automática |

---

## ⚠️ Requisitos Mínimos

- [x] Docker instalado
- [x] Docker Compose instalado
- [x] 2GB de RAM disponível
- [x] Conexão de internet

---

**Pronto?** Execute: `docker-compose up --build` 🚀
