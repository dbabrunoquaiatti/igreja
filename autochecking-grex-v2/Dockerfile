FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
# credenciais.cfg é ignorado pelo .gitignore — configure via variáveis de ambiente:
#   GREX_EMAIL    → e-mail do usuário Grex
#   GREX_PASSWORD → senha do usuário Grex
#   PROXY_PASS    → senha do proxy (obrigatório em produção)

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "app:app"]
