# 🐳 Opções de Dockerfile - Comparação

## 📊 Tabela Comparativa

| Aspecto | Alpine (Dockerfile) | Selenium (Dockerfile.selenium) |
|---------|-------------------|-------------------------------|
| **Tamanho** | ~400MB | ~700MB |
| **Build Time** | ⚡ 2-3 min | ⚡ 2-3 min (1ª vez) |
| **Runtime** | ✅ Rápido | ✅ Muito rápido |
| **Memória** | 📉 Menor | 📈 Mais (Chrome otimizado) |
| **Confiabilidade** | ✅ Boa | ⭐ Excelente |
| **Recomendação** | **Melhor para CI/CD** | **Melhor para Produção** |

---

## 🚀 OPÇÃO 1: Alpine (Atual - Recomendado para Começar)

```bash
docker-compose up --build
```

**Vantagens:**
- ✅ Menor tamanho
- ✅ Build mais rápido
- ✅ Executa bem

**Desvantagens:**
- ⚠️ Às vezes tem problemas com Chrome em Alpine

---

## ⭐ OPÇÃO 2: Selenium Standalone (Mais Robusto)

```bash
# Build
docker build -f Dockerfile.selenium -t webscraping-grex .

# Ou via compose
docker-compose -f docker-compose.selenium.yml up --build
```

**Vantagens:**
- ✅ Chrome já otimizado
- ✅ Mais estável
- ✅ Menos problemas de compatibilidade
- ✅ Melhor para produção

**Desvantagens:**
- ⚠️ Tamanho um pouco maior

---

## 🎯 Qual Usar?

### Se quer RÁPIDO E LEVE:
```bash
docker-compose up --build
# (usa Dockerfile com Alpine)
```

### Se quer MAIS CONFIÁVEL:
```bash
docker build -f Dockerfile.selenium -t webscraping-grex .
docker run -it \
  -e GREX_EMAIL="quaiattibruno@gmail.com" \
  -e GREX_PASSWORD="Temp#2032435@" \
  -v $(pwd)/data:/app/data \
  webscraping-grex
```

---

## 📈 Tamanhos de Imagem

```
Alpine    : ~400MB
Selenium  : ~700MB
Debian    : ~1.2GB (evitar!)
```

**Alpine é o melhor balanço!** ✅

---

## ⚡ Tempos de Build

```
Primeira build:
- Alpine    : 2-3 min
- Selenium  : 2-3 min

Rebuilds:
- Alpine    : 30 seg
- Selenium  : 30 seg
```

---

## 🔧 Como Mudar se Tiver Problema

Se o Alpine der problema ao rodar, use o Selenium:

```bash
# Limpar
docker-compose down -v
docker image rm webscraping-grex

# Usar Selenium
docker build -f Dockerfile.selenium -t webscraping-grex .
docker run -it \
  -e GREX_EMAIL="quaiattibruno@gmail.com" \
  -e GREX_PASSWORD="Temp#2032435@" \
  -v $(pwd)/data:/app/data \
  webscraping-grex
```

---

## 💡 Recomendação Final

**COMECE COM ALPINE** (atual Dockerfile):
```bash
docker-compose up --build
```

Se não funcionar, **MUDE PARA SELENIUM**:
```bash
docker build -f Dockerfile.selenium -t webscraping-grex .
```

---

## 📝 Exemplo Dockerfile.selenium no docker-compose

Se quiser usar Selenium via compose, crie `docker-compose.selenium.yml`:

```yaml
version: '3.8'

services:
  webscraping-grex:
    build:
      context: .
      dockerfile: Dockerfile.selenium
    
    container_name: webscraping-grex
    
    environment:
      GREX_EMAIL: ${GREX_EMAIL:-quaiattibruno@gmail.com}
      GREX_PASSWORD: ${GREX_PASSWORD:-Temp#2032435@}
    
    volumes:
      - ./data:/app/data
    
    restart: no
```

Execute com:
```bash
docker-compose -f docker-compose.selenium.yml up --build
```

---

## 🎯 TL;DR (Resumo)

| Situação | Comando |
|----------|---------|
| Primeiro teste | `docker-compose up --build` |
| Tiver erro | `docker build -f Dockerfile.selenium -t webscraping-grex .` |
| Quer o menor | `docker-compose up --build` (Alpine) |
| Quer o mais estável | `docker build -f Dockerfile.selenium -t webscraping-grex .` |

