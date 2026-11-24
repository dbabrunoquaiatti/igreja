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

echo "🌐 Iniciando servidor web na porta 8080..."
python3 - << 'SERVEREOF' &
import http.server, os, re, zipfile, subprocess, json as _json
import xml.etree.ElementTree as ET

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'

def _col_idx(ref):
    """'B3' -> 1  (0-based column index)"""
    m = re.match(r'([A-Z]+)', str(ref))
    if not m:
        return 0
    n = 0
    for ch in m.group(1):
        n = n * 26 + ord(ch) - 64
    return n - 1

def _read_xlsx(path):
    """Return list of rows; each row is a dict {col_index: cell_value_str}."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        # shared strings
        strs = []
        if 'xl/sharedStrings.xml' in names:
            root = ET.parse(zf.open('xl/sharedStrings.xml')).getroot()
            for si in root.findall(f'{{{NS}}}si'):
                strs.append(''.join(t.text or '' for t in si.iter(f'{{{NS}}}t')))
        # first sheet
        sheets = sorted(n for n in names if re.match(r'xl/worksheets/sheet\d+\.xml$', n))
        if not sheets:
            return []
        rows = []
        root = ET.parse(zf.open(sheets[0])).getroot()
        for row_el in root.iter(f'{{{NS}}}row'):
            row = {}
            for c in row_el.findall(f'{{{NS}}}c'):
                col = _col_idx(c.get('r', ''))
                t   = c.get('t', '')
                vel = c.find(f'{{{NS}}}v')
                v   = vel.text if vel is not None else ''
                if t == 's':
                    try: row[col] = strs[int(v)]
                    except: row[col] = ''
                elif t == 'inlineStr':
                    iel = c.find(f'{{{NS}}}is')
                    row[col] = ''.join(x.text or '' for x in iel.iter(f'{{{NS}}}t')) if iel is not None else ''
                else:
                    row[col] = v or ''
            if row:
                rows.append(row)
        return rows

def _calcular_pagos_total():
    STATUS_VARIANTS = ['statusdopagamento','statuspagamento','statuspgto','paymentstatus','status']
    PAID = {'paid','approved','aprovado','confirmado','confirm','pago','concluido','concluído'}

    def norm(s):
        return re.sub(r'\s+', '', str(s or '')).lower()

    total = 0
    for fname in ('encontro.xlsx', 'encontro2.xlsx'):
        path = os.path.join('/app/data', fname)
        if not os.path.exists(path):
            continue
        try:
            rows = _read_xlsx(path)
            if not rows:
                continue
            # header row
            hdr = rows[0]
            col = None
            for sv in STATUS_VARIANTS:
                for ci, val in hdr.items():
                    if norm(val) == sv:
                        col = ci
                        break
                if col is not None:
                    break
            if col is None:
                continue
            for row in rows[1:]:
                if norm(row.get(col, '')) in PAID:
                    total += 1
        except Exception:
            pass

    pagar_depois = (
        int(os.environ.get('PAGAR_DEPOIS_SERVOS', 0) or 0) +
        int(os.environ.get('PAGAR_DEPOIS_CONVIDADOS', 0) or 0)
    )
    return max(0, total - pagar_depois), None

_qrcode_proc = None

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/pagos-total':
            self._serve_pagos_total()
        elif self.path == '/qrcode-status':
            self._serve_qrcode_status()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/enviar-qrcode':
            self._handle_enviar_qrcode()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_pagos_total(self):
        total, err = _calcular_pagos_total()
        if err:
            body = ('0').encode('utf-8')
            self.send_response(500)
        else:
            body = str(total).encode('utf-8')
            self.send_response(200)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _serve_qrcode_status(self):
        status_path = '/app/data/qrcode_status.json'
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                body = f.read().encode('utf-8')
            self.send_response(200)
        except FileNotFoundError:
            body = b'{"status":"idle","concluido":false,"total":0,"enviados":0}'
            self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _handle_enviar_qrcode(self):
        global _qrcode_proc
        content_len = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(content_len)
        try:
            data = _json.loads(raw)
        except Exception:
            data = {}

        # Bloquear novo envio se já houver um em andamento
        status_path = '/app/data/qrcode_status.json'
        try:
            with open(status_path, 'r') as f:
                st = _json.load(f)
            if not st.get('concluido', True) and st.get('status') in ('iniciando', 'processando'):
                resp = _json.dumps({'ok': False, 'erro': 'Envio em andamento'}).encode('utf-8')
                self.send_response(409)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', len(resp))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp)
                return
        except Exception:
            pass

        if data.get('todos'):
            _qrcode_proc = subprocess.Popen(
                ['python3', '/app/enviar_qrcode.py', 'todos'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif data.get('nome'):
            _qrcode_proc = subprocess.Popen(
                ['python3', '/app/enviar_qrcode.py', data['nome']],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            resp = _json.dumps({'ok': False, 'erro': 'Parametro invalido'}).encode('utf-8')
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(resp))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(resp)
            return

        resp = _json.dumps({'ok': True}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(resp))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(resp)

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
