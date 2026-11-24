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
    ('DUPLICADO_IGNORAR',       v('DUPLICADO_IGNORAR', 'formaPagamento,presenca,dataInscricao,statusPagamento')),
    ('IGNORA_DISCIPULADOR',     v('IGNORA_DISCIPULADOR')),
    ('NOME_FAMILIAR_COL',       v('NOME_FAMILIAR_COL')),
    ('TEL_FAMILIAR_COL',        v('TEL_FAMILIAR_COL')),
    ('PAGAR_DEPOIS_SERVOS',     v('PAGAR_DEPOIS_SERVOS', '0')),
    ('PAGAR_DEPOIS_CONVIDADOS', v('PAGAR_DEPOIS_CONVIDADOS', '0')),
    ('MENSAGEM_INSCRICAO',      v('MENSAGEM_INSCRICAO')),
    ('GREX_EVENTO_URL',         v('GREX_EVENTO_URL')),
    ('GREX_AUTOMACAO_CHECKING', v('GREX_AUTOMACAO_CHECKING')),
    ('FINANCEIRO_URL',          v('FINANCEIRO_URL')),
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

echo "📦 Garantindo openpyxl instalado..."
pip3 install openpyxl --quiet 2>/dev/null || true

echo "🌐 Iniciando servidor web na porta 8080..."
python3 - << 'SERVEREOF' &
import http.server, os, re

def _calcular_pagos_total():
    try:
        import openpyxl
    except ImportError:
        return None, 'openpyxl nao instalado'

    STATUS_VARIANTS = [
        'statusdopagamento', 'statuspagamento', 'statuspgto',
        'paymentstatus', 'status'
    ]
    PAID = {'paid', 'approved', 'aprovado', 'confirmado', 'confirm', 'pago', 'concluido', 'concluído'}

    def norm(s):
        return re.sub(r'\s+', '', str(s or '')).lower()

    def find_col(headers):
        h = {norm(h): i for i, h in enumerate(headers)}
        for v in STATUS_VARIANTS:
            if v in h:
                return h[v]
        return None

    total = 0
    for fname in ('encontro.xlsx', 'encontro2.xlsx'):
        path = os.path.join('/app/data', fname)
        if not os.path.exists(path):
            continue
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            ws = wb.active
            it = ws.iter_rows(values_only=True)
            headers = next(it, None)
            if not headers:
                wb.close(); continue
            col = find_col(headers)
            if col is None:
                wb.close(); continue
            for row in it:
                val = norm(row[col] if col < len(row) else '')
                if val in PAID:
                    total += 1
            wb.close()
        except Exception:
            pass

    pagar_depois = (
        int(os.environ.get('PAGAR_DEPOIS_SERVOS', 0) or 0) +
        int(os.environ.get('PAGAR_DEPOIS_CONVIDADOS', 0) or 0)
    )
    return max(0, total - pagar_depois), None

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/pagos-total':
            self._serve_pagos_total()
        else:
            super().do_GET()

    def _serve_pagos_total(self):
        total, err = _calcular_pagos_total()
        if err:
            body = ('erro: ' + err).encode('utf-8')
            self.send_response(500)
        else:
            body = str(total).encode('utf-8')
            self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        pass

os.chdir('/app')
http.server.HTTPServer(('', 8080), NoCacheHandler).serve_forever()
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
