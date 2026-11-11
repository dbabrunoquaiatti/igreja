# 🐳 Docker - Web Scraping GREX

## 📋 Requisitos

- [Docker](https://www.docker.com/products/docker-desktop) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) (opcional, mas recomendado)

## 🚀 Início Rápido

### Opção 1: Docker Compose (Recomendado) ⭐

```bash
# 1. Configure as variáveis de ambiente
# Windows (PowerShell)
$env:GREX_EMAIL="quaiattibruno@gmail.com"
$env:GREX_PASSWORD="Temp#2032435@"

# Linux/Mac
export GREX_EMAIL="quaiattibruno@gmail.com"
export GREX_PASSWORD="Temp#2032435@"

# 2. Execute
docker-compose up --build

# 3. Resultado em data/encontro.xlsx
```

### Opção 2: Build Manual

```bash
# 1. Build da imagem
docker build -t webscraping-grex .

# 2. Execute o container
# Windows (PowerShell)
docker run -it `
  -e GREX_EMAIL="quaiattibruno@gmail.com" `
  -e GREX_PASSWORD="Temp#2032435@" `
  -v ${PWD}/data:/app/data `
  webscraping-grex

# Linux/Mac
docker run -it \
  -e GREX_EMAIL="quaiattibruno@gmail.com" \
  -e GREX_PASSWORD="Temp#2032435@" \
  -v $(pwd)/data:/app/data \
  webscraping-grex
```

## 📝 Arquivo .env para Docker

Crie um arquivo `.env` na raiz do projeto:

```bash
# .env
GREX_EMAIL=quaiattibruno@gmail.com
GREX_PASSWORD=Temp#2032435@
```

Depois execute:
```bash
docker-compose up --build
```

O Docker Compose carregará automaticamente as variáveis do `.env`.

## 🔧 Customizações

### Usar a versão simples (sem variáveis de ambiente)

Edite o `docker-compose.yml`:

```yaml
services:
  webscraping-grex:
    build: .
    # Mude de:
    # CMD ["python", "webscraping_grex_secure.py"]
    # Para:
    # CMD ["python", "webscraping_grex.py"]
```

Ou modifique o `Dockerfile`:

```dockerfile
# Mude a última linha de:
CMD ["python", "webscraping_grex_secure.py"]
# Para:
CMD ["python", "webscraping_grex.py"]
```

### Modo Headless (sem interface gráfica)

O Docker já roda em modo headless por padrão. Se quiser ver o navegador, modifique `webscraping_grex_secure.py`:

```python
# Em setup_driver()
# Remova o comentário:
chrome_options.add_argument("--headless")
```

### Limitar recursos

No `docker-compose.yml`, descomente:

```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
```

## 🔍 Verificar Logs

```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um container específico
docker-compose logs -f webscraping-grex
```

## 🧹 Limpar

```bash
# Parar containers
docker-compose down

# Remover imagem
docker image rm webscraping-grex

# Limpar tudo (volumes, networks, etc)
docker-compose down -v
```

## 📊 Verificar Dados

```bash
# Listar arquivos gerados
ls data/

# No Windows PowerShell
Get-ChildItem data/
```

## 🚀 Agendar com Docker

### Windows - Task Scheduler

```batch
docker-compose up --build --abort-on-container-exit
```

### Linux/Mac - Cron

```bash
# Adicione ao crontab (crontab -e)
0 9 * * * cd /caminho/para/webscraping-grex && docker-compose up --build --abort-on-container-exit
```

## ⚡ Docker Compose vs. Docker run

| Aspecto | Docker Compose | Docker run |
|--------|-----------------|-----------|
| Facilidade | ⭐⭐⭐ Muito fácil | ⭐ Complexo |
| Variáveis de ambiente | ✅ Automático (.env) | ⚠️ Manual |
| Volumes | ✅ Automático | ⚠️ Manual |
| Reutilização | ✅ Config salva | ❌ Precisa escrever tudo |
| Escalabilidade | ✅ Múltiplos serviços | ❌ Um por um |

**Recomendação**: Use `docker-compose` para tudo! 🎯

## 🐛 Troubleshooting

| Problema | Solução |
|----------|---------|
| "Docker daemon is not running" | Abra o Docker Desktop ou reinicie o daemon |
| "Permission denied" (Linux) | Execute: `sudo usermod -aG docker $USER` |
| Chrome não inicia | Verifique: `docker logs webscraping-grex` |
| Arquivo não baixa | Verifique permissões de `/data` |
| Timeout ao logar | Aumente sleep em `webscraping_grex_secure.py` |

## 📚 Comandos Úteis

```bash
# Listar imagens
docker images

# Listar containers rodando
docker ps

# Listar todos os containers
docker ps -a

# Inspecionar imagem
docker inspect webscraping-grex

# Executar comando dentro do container
docker exec -it webscraping-grex bash

# Build sem cache
docker build --no-cache -t webscraping-grex .

# Push para registry (Docker Hub)
docker tag webscraping-grex seu-usuario/webscraping-grex
docker push seu-usuario/webscraping-grex
```

## 🔐 Segurança

⚠️ **IMPORTANTE**: Nunca commite o arquivo `.env` com credenciais reais no Git!

```bash
# .gitignore (já incluído)
.env
.env.local
```

Para compartilhar o projeto:
1. Deixe apenas `.env.example`
2. Cada pessoa copia para `.env` com suas credenciais
3. Nunca commita `.env`

## 🌐 Usar com Selenium Grid (Avançado)

Para ambientes mais robustos com múltiplos browsers:

```bash
# Descomente a seção no docker-compose.yml

docker-compose up --build

# Isso iniciará:
# - Selenium Hub (orquestrador)
# - Node Chrome (browser)
# - Seu script de scraping
```

Modifique `webscraping_grex_secure.py` para usar o Grid:

```python
from selenium.webdriver.remote.webdriver import WebDriver

def setup_driver():
    remote_url = os.getenv("SELENIUM_GRID_URL", "http://localhost:4444")
    options = Options()
    return WebDriver(
        command_executor=remote_url,
        options=options
    )
```

## 📞 Suporte

Se encontrar problemas:
1. Veja a documentação em `README_WEBSCRAPING.md`
2. Verifique logs: `docker-compose logs -f`
3. Tente build sem cache: `docker build --no-cache -t webscraping-grex .`
