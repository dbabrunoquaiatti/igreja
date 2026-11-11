# Usar imagem com Chrome pré-instalado (MUITO mais confiável)
FROM python:3.12-slim

# Metadados
LABEL maintainer="Bruno Quaiatti"
LABEL description="Web Scraping GREX - Com Chrome pré-instalado"

# Definir variáveis de ambiente
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

# Instalar Chrome/Chromium, ChromeDriver e dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    tzdata \
    libnss3 \
    libxss1 \
    fonts-liberation \
    fonts-dejavu-core \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Fix Chromium 156 (Debian trixie): crashpad handler é spawned sem --database → Chrome sai.
# Wrapper que injeta --database=/tmp/crashpad-db quando o argumento está faltando.
RUN set -e; \
    REAL=""; \
    for p in /usr/lib/chromium/chrome_crashpad_handler /usr/lib/chromium-browser/chrome_crashpad_handler; do \
        [ -f "$p" ] && REAL="$p" && break; \
    done; \
    if [ -z "$REAL" ] && [ -f /usr/bin/chrome_crashpad_handler ]; then \
        REAL=/usr/bin/chrome_crashpad_handler; \
    fi; \
    if [ -n "$REAL" ]; then \
        cp "$REAL" "${REAL}.real"; \
        printf '#!/bin/sh\nmkdir -p /tmp/crashpad-db\nfor a in "$@"; do\n  case "$a" in --database=*) exec %s "$@";; esac\ndone\nexec %s --database=/tmp/crashpad-db "$@"\n' "${REAL}.real" "${REAL}.real" > "$REAL"; \
        chmod +x "$REAL"; \
        [ -f /usr/bin/chrome_crashpad_handler ] && cp "$REAL" /usr/bin/chrome_crashpad_handler || true; \
    fi

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install -r requirements.txt

# Copiar scripts
COPY webscraping_grex.py .

# Criar pasta data (os xlsx são gerados em runtime pelo script)
RUN mkdir -p /app/data

# Copiar index.html e assets
COPY index.html .
COPY imgs/ ./imgs/

# Copiar entrypoint (gera config.js a partir das env vars do Easypanel)
COPY entrypoint.sh /entrypoint.sh
COPY docker-entrypoint-root.sh /docker-entrypoint-root.sh
RUN chmod +x /entrypoint.sh /docker-entrypoint-root.sh \
    && groupadd -r -g 1001 grex \
    && useradd -r -u 1001 -g grex -s /sbin/nologin grex \
    && chown -R grex:grex /app

# Expor volume para dados
VOLUME ["/app/data"]

# Wrapper root: corrige permissões do volume e dropa para grex
ENTRYPOINT ["/docker-entrypoint-root.sh"]
