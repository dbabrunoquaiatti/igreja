# 🐳 Comandos Docker - Pronto para Copiar e Colar

## 🖥️ WINDOWS (PowerShell)

```powershell
# 1. Navegue até a pasta do projeto
cd "C:\Users\brunoquaiatti\Documents\Claude\Projects\GREX - WEBSCRAPING"

# 2. Crie arquivo .env (copie e cole)
@"
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
"@ | Out-File -Encoding utf8 .env

# 3. Build e execute (COMANDO PRINCIPAL)
docker-compose up --build

# 4. Se quiser modo detached (sem ver logs)
docker-compose up --build -d

# 5. Ver logs depois
docker-compose logs -f

# 6. Parar
docker-compose down

# 7. Limpar tudo
docker-compose down -v
docker image rm webscraping-grex
```

---

## 🐧 LINUX / MAC

```bash
# 1. Navegue até a pasta do projeto
cd ~/Documents/Claude/Projects/GREX\ -\ WEBSCRAPING

# 2. Crie arquivo .env
cat > .env << EOF
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
EOF

# 3. Build e execute (COMANDO PRINCIPAL)
docker-compose up --build

# 4. Se quiser modo detached (sem ver logs)
docker-compose up --build -d

# 5. Ver logs depois
docker-compose logs -f

# 6. Parar
docker-compose down

# 7. Limpar tudo
docker-compose down -v
docker image rm webscraping-grex
```

---

## 🎯 RESUMO - EXECUÇÃO COMPLETA

### Passo 1: Verificar Docker
```bash
docker --version
docker-compose --version
```

### Passo 2: Criar .env
**Windows (PowerShell):**
```powershell
@"
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
"@ | Out-File -Encoding utf8 .env
```

**Linux/Mac:**
```bash
cat > .env << EOF
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
EOF
```

### Passo 3: EXECUTAR (o principal!)
```bash
docker-compose up --build
```

**Aguarde até ver:**
```
✅ Arquivo salvo em: /app/data/encontro.xlsx
✨ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!
```

### Passo 4: Verificar Resultado
```bash
# O arquivo está em:
data/encontro.xlsx
```

---

## ⚡ VARIAÇÕES DE COMANDO

### Executar e não ver logs (background)
```bash
docker-compose up --build -d
```

### Ver logs depois
```bash
docker-compose logs -f
```

### Executar sem reconstruir imagem
```bash
docker-compose up
```

### Parar container
```bash
docker-compose stop
```

### Restart
```bash
docker-compose restart
```

### Remover tudo
```bash
docker-compose down -v
```

### Listar containers
```bash
docker ps -a
```

### Listar imagens
```bash
docker images | grep webscraping
```

### Executar bash dentro do container
```bash
docker exec -it webscraping-grex bash
```

### Ver tamanho da imagem
```bash
docker images webscraping-grex --format "table {{.Repository}}\t{{.Size}}"
```

---

## 🔧 TROUBLESHOOTING

### "Docker daemon is not running"
```bash
# Windows: Abra Docker Desktop
# Linux: sudo systemctl start docker
# Mac: Abra Docker.app
```

### "Permission denied" (Linux)
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Reconstruir do zero
```bash
docker-compose down -v
docker image rm webscraping-grex
docker-compose up --build
```

### Ver o que está acontecendo
```bash
docker-compose logs -f webscraping-grex
```

### Container saiu com erro
```bash
# Ver o que aconteceu
docker-compose logs webscraping-grex

# Tentar novamente
docker-compose up --build
```

---

## 📊 FLUXO COMPLETO

```
┌─────────────────────────────────────────┐
│ 1. docker-compose up --build            │
│    ↓                                    │
│ 2. Docker baixa e constrói imagem       │
│    ↓                                    │
│ 3. Instala Chromium, Python, deps       │
│    ↓                                    │
│ 4. Inicia container                     │
│    ↓                                    │
│ 5. Script executa:                      │
│    - Login GREX                         │
│    - Navega para participantes          │
│    - Clica botão exportar               │
│    - Seleciona tipo                     │
│    - Confirma                           │
│    - Salva em /app/data/encontro.xlsx   │
│    ↓                                    │
│ 6. Arquivo aparece em data/encontro.xlsx│
│    ↓                                    │
│ 7. Container finaliza                   │
└─────────────────────────────────────────┘
```

---

## ✅ CHECKLIST

- [ ] Docker instalado e rodando
- [ ] Docker Compose instalado
- [ ] Está na pasta correta do projeto
- [ ] Criou arquivo .env
- [ ] Executou `docker-compose up --build`
- [ ] Viu "AUTOMAÇÃO CONCLUÍDA COM SUCESSO!"
- [ ] Arquivo `data/encontro.xlsx` existe

---

## 💡 DICAS PRO

### Agendar execução automática

**Windows (Task Scheduler):**
```batch
# Crie arquivo run-docker.bat
cd C:\Users\brunoquaiatti\Documents\Claude\Projects\GREX - WEBSCRAPING
docker-compose up --build --abort-on-container-exit
```

**Linux/Mac (Cron):**
```bash
# crontab -e
0 9 * * * cd /home/usuario/GREX-WEBSCRAPING && docker-compose up --build --abort-on-container-exit
```

### Usar credenciais diferentes

Modifique o `.env`:
```bash
GREX_EMAIL=outro_email@example.com
GREX_PASSWORD=outra_senha
```

Execute novamente:
```bash
docker-compose up --build
```

### Reutilizar container (mais rápido)

Se não mudou código, use:
```bash
docker-compose up
# (sem --build)
```

---

## 🚀 COMANDO MAIS IMPORTANTE

```bash
docker-compose up --build
```

**Copie e cole isso no terminal quando estiver pronto!**

---

## 📞 PROBLEMAS COMUNS

| Erro | Solução |
|------|---------|
| `command not found: docker-compose` | Instale Docker Desktop (vem com Compose) |
| `Cannot connect to Docker daemon` | Abra Docker Desktop ou inicie o daemon |
| `no such file or directory: .env` | Crie o arquivo .env com `GREX_EMAIL` e `GREX_PASSWORD` |
| `timeout on login` | Aumente o sleep em webscraping_grex_secure.py |
| `file not found: data/encontro.xlsx` | Aguarde mais tempo ou veja os logs |

---

**Quando executar, você verá:**

```
====================================================
🚀 INICIANDO AUTOMAÇÃO GREX (VERSÃO SEGURA)
====================================================
✅ Credenciais carregadas (email: quaiattibruno...)
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
✅ Arquivo salvo em: /app/data/encontro.xlsx

====================================================
✨ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!
====================================================
```

**Então é sucesso!** ✅
