# Usar imagem com Chrome pré-instalado (MUITO mais confiável)
FROM python:3.11-slim

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
    wget \
    curl \
    ca-certificates \
    tzdata \
    libnss3 \
    libxss1 \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar scripts
COPY webscraping_grex.py .

# Criar pasta data (os xlsx são gerados em runtime pelo script)
RUN mkdir -p /app/data

# Copiar index.html e assets
COPY index.html .
COPY imgs/ ./imgs/

# Copiar entrypoint (gera config.js a partir das env vars do Easypanel)
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expor volume para dados
VOLUME ["/app/data"]

# Comando padrão
ENTRYPOINT ["/entrypoint.sh"]
