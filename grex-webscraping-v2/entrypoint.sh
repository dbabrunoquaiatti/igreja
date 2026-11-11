#!/bin/bash
set +e
cd /app

echo "🔧 Gerando config.js a partir das variáveis de ambiente do Easypanel..."

# Usa Python para gerar o config.js com JSON encoding correto:
# - strings multi-linha (MENSAGEM_INSCRICAO) são escapadas automaticamente
# - caracteres especiais ($, ", \, emojis) não quebram o JS
python3 - << 'PYEOF'
import os, json

def v(name, default=''):
    return os.environ.get(name, default)

config = [
    ('PANEL_TITLE',             v('PANEL_TITLE')),
    ('PANEL_TOKEN',             v('PANEL_TOKEN')),
    ('PRIMARY_COLOR',           v('PRIMARY_COLOR', '#6b46c1')),
    ('PRIMARY_LIGHT',           v('PRIMARY_LIGHT', '#8b5cf6')),
    ('GREX_PARTICIPANTS_URL',   v('GREX_PARTICIPANTS_URL')),
    ('GREX_PARTICIPANTS_URL_2', v('GREX_PARTICIPANTS_URL_2')),
    ('GREX_FONTE1_COLUNAS',     v('GREX_FONTE1_COLUNAS')),
    ('GREX_FONTE2_COLUNAS',     v('GREX_FONTE2_COLUNAS')),
    ('EXCLUIR_ABAS',            v('EXCLUIR_ABAS')),
    ('EXCLUIR_COLUNAS',         v('EXCLUIR_COLUNAS')),
    ('SERVOS',                  v('SERVOS', 'S')),
    ('CONVIDADOS',              v('CONVIDADOS', 'S')),
    ('DUPLICADO_IGNORAR',       v('DUPLICADO_IGNORAR', 'formaPagamento,presenca,dataInscricao')),
    ('IGNORA_DISCIPULADOR',     v('IGNORA_DISCIPULADOR')),
    ('PAGAR_DEPOIS_SERVOS',     v('PAGAR_DEPOIS_SERVOS', '0')),
    ('PAGAR_DEPOIS_CONVIDADOS', v('PAGAR_DEPOIS_CONVIDADOS', '0')),
    ('MENSAGEM_INSCRICAO',      v('MENSAGEM_INSCRICAO')),
    ('GREX_EVENTO_URL',         v('GREX_EVENTO_URL')),
    ('GREX_AUTOMACAO_CHECKING',  v('GREX_AUTOMACAO_CHECKING')),
]

lines = ['window.CONFIG = {']
for i, (key, val) in enumerate(config):
    comma = ',' if i < len(config) - 1 else ''
    lines.append(f'  {key}: {json.dumps(val)}{comma}')
lines.append('};')
lines.append("console.log('✅ config.js carregado (Easypanel env vars)');")

with open('/app/config.js', 'w') as f:
    f.write('\n'.join(lines) + '\n')

print('config.js gerado com sucesso')
PYEOF

echo "✅ config.js gerado!"

echo "🌐 Iniciando servidor web na porta 8080..."
python3 - << 'SERVEREOF' &
import http.server, os, base64, hmac, secrets, sys

PANEL_USER  = os.environ.get('PANEL_USER', 'admin')
PANEL_PASS  = os.environ.get('PANEL_PASSWORD', '')
PANEL_TOKEN = os.environ.get('PANEL_TOKEN', '')


class AuthNoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if not self._check_auth():
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._check_auth():
            return
        super().do_HEAD()

    def _check_auth(self):
        # Sem PANEL_PASSWORD configurado → acesso público
        if not PANEL_PASS:
            return True
        # Bearer token (fetch() calls do app)
        if PANEL_TOKEN:
            auth = self.headers.get('Authorization', '')
            if hmac.compare_digest(auth, f'Bearer {PANEL_TOKEN}'):
                return True
        # Basic Auth (acesso direto pelo browser)
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth[6:]).decode('utf-8')
                user, pwd = decoded.split(':', 1)
                if user == PANEL_USER and pwd == PANEL_PASS:
                    return True
            except Exception:
                pass
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Painel ADM"')
        self.end_headers()
        return False

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass

os.chdir('/app')
http.server.HTTPServer(('', 8080), AuthNoCacheHandler).serve_forever()
SERVEREOF
SERVER_PID=$!
sleep 3
echo "✅ Servidor web iniciado (PID: $SERVER_PID)"
echo "📍 Acesse: http://localhost:8080"

echo "🔄 Iniciando loop de webscraping..."
while true; do
  echo "[$(date)] Executando webscraping..."
  python webscraping_grex.py 2>&1 || true
  echo "[$(date)] Aguardando 1 minuto..."
  sleep 60
done
