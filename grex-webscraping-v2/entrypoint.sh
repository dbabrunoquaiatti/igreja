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
    ('DUPLICADO_IGNORAR',       v('DUPLICADO_IGNORAR', 'formaPagamento,presenca,dataInscricao')),
    ('IGNORA_DISCIPULADOR',     v('IGNORA_DISCIPULADOR')),
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
import http.server, os, hmac, secrets, time, json

# PANEL_USER/PANEL_PASSWORD têm prioridade; se não definidos, usa GREX_EMAIL/GREX_PASSWORD
PANEL_USER = os.environ.get('PANEL_USER') or os.environ.get('GREX_EMAIL') or 'admin'
PANEL_PASS = os.environ.get('PANEL_PASSWORD') or os.environ.get('GREX_PASSWORD') or ''

# Sessões server-side: {token: timestamp}
_sessions = {}
SESSION_TTL = 86400  # 24 h

def _cleanup_sessions():
    now = time.time()
    for k in [k for k, t in list(_sessions.items()) if now - t > SESSION_TTL]:
        del _sessions[k]

LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acesso — Painel</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Lato,sans-serif;background:linear-gradient(135deg,#1e1b4b 0%,#3730a3 50%,#6b46c1 100%);min-height:100vh}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#fff;border-radius:20px;padding:40px 36px;width:100%;max-width:380px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.logo{text-align:center;margin-bottom:8px}
.logo svg{width:56px;height:56px}
.title{font-size:22px;font-weight:700;color:#2c2c2c;text-align:center;margin-bottom:4px}
.sub{font-size:14px;color:#666;text-align:center;margin-bottom:28px}
.grp{margin-bottom:16px}
.grp label{display:block;font-size:13px;font-weight:600;color:#2c2c2c;margin-bottom:6px}
.grp input{width:100%;padding:12px 14px;border:1.5px solid #e8e8e8;border-radius:10px;font-size:16px;color:#2c2c2c;background:#f5f5f5;outline:none;transition:border-color .2s;-webkit-appearance:none;appearance:none}
.grp input:focus{border-color:#6b46c1;background:#fff}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#6b46c1,#8b5cf6);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;margin-top:8px;position:relative;overflow:hidden;transition:opacity .2s,transform .1s;-webkit-tap-highlight-color:transparent}
.btn:active{transform:scale(.98);opacity:.9}
.btn:disabled{opacity:.7;cursor:not-allowed}
.btn-txt{transition:opacity .2s;display:block}
.btn-spin{display:none;position:absolute;inset:0;align-items:center;justify-content:center}
.btn.loading .btn-txt{opacity:0}
.btn.loading .btn-spin{display:flex}
@keyframes spin{to{transform:rotate(360deg)}}
.ring{width:22px;height:22px;border:2.5px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
.err{background:#fef2f2;border:1px solid #fecaca;color:#dc2626;padding:10px 14px;border-radius:8px;font-size:13px;margin-bottom:14px;display:none}
@keyframes fadein{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
.err.show{display:block;animation:fadein .3s ease}
</style>
</head>
<body>
<div class="wrap"><div class="card">
<div class="logo"><svg viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="56" rx="14" fill="#6b46c1"/><path d="M28 14L38 20V32L28 38L18 32V20L28 14Z" stroke="white" stroke-width="2.5" stroke-linejoin="round"/><circle cx="28" cy="26" r="5" fill="white"/></svg></div>
<div class="title">Painel ADM</div>
<div class="sub">Entre para continuar</div>
<div class="err" id="err"></div>
<form id="frm" autocomplete="on">
<div class="grp"><label for="u">E-mail</label><input type="email" id="u" name="username" autocomplete="username" inputmode="email" placeholder="seu@email.com" required></div>
<div class="grp"><label for="p">Senha</label><input type="password" id="p" name="current-password" autocomplete="current-password" placeholder="••••••••" required></div>
<button type="submit" class="btn" id="btn"><span class="btn-txt">Entrar</span><span class="btn-spin"><span class="ring"></span></span></button>
</form>
</div></div>
<script>
(function(){
var frm=document.getElementById('frm'),btn=document.getElementById('btn'),errEl=document.getElementById('err');
function showErr(m){errEl.textContent=m;errEl.classList.add('show');}
function hideErr(){errEl.classList.remove('show');}
function setLoad(on){btn.disabled=on;btn.classList.toggle('loading',on);}
frm.addEventListener('submit',function(e){
  e.preventDefault();hideErr();
  var u=document.getElementById('u').value.trim();
  var p=document.getElementById('p').value;
  if(!u||!p){showErr('Preencha usuário e senha.');return;}
  setLoad(true);
  fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u,pass:p}),credentials:'same-origin'})
    .then(function(r){return r.json().then(function(d){return{ok:r.ok,d:d};});})
    .then(function(res){
      if(res.ok&&res.d.ok){location.replace('/');}
      else{setLoad(false);showErr((res.d&&res.d.error)||'Usuário ou senha incorretos.');}
    })
    .catch(function(){setLoad(false);showErr('Erro de conexão. Tente novamente.');});
});
})();
</script>
</body>
</html>"""


class AuthNoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/login':
            self._serve_login()
            return
        if not self._check_session():
            self._redirect_to_login()
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._check_session():
            self.send_response(302)
            self.send_header('Location', '/login')
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        path = self.path.split('?')[0]
        if path == '/login':
            self._handle_login()
        else:
            if not self._check_session():
                self.send_response(403)
                self.end_headers()
                return
            self.send_response(404)
            self.end_headers()

    def _check_session(self):
        if not PANEL_PASS:
            return True
        for part in self.headers.get('Cookie', '').split(';'):
            name, _, val = part.strip().partition('=')
            if name.strip() == 'session':
                ts = _sessions.get(val.strip())
                if ts and time.time() - ts < SESSION_TTL:
                    return True
        return False

    def _redirect_to_login(self):
        self.send_response(302)
        self.send_header('Location', '/login')
        self.end_headers()

    def _serve_login(self):
        if self._check_session():
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
            return
        body = LOGIN_HTML.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_login(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length) if length > 0 else b'{}'
        try:
            data = json.loads(raw)
            user = str(data.get('user', ''))
            pwd  = str(data.get('pass', ''))
            if not PANEL_PASS:
                ok = True
            else:
                ok = (hmac.compare_digest(user, PANEL_USER) and
                      hmac.compare_digest(pwd,  PANEL_PASS))
            if ok:
                _cleanup_sessions()
                tok = secrets.token_urlsafe(32)
                _sessions[tok] = time.time()
                resp = json.dumps({'ok': True}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.send_header('Set-Cookie',
                    f'session={tok}; HttpOnly; SameSite=Strict; Path=/')
                self.end_headers()
                self.wfile.write(resp)
            else:
                resp = json.dumps({'ok': False, 'error': 'Usuário ou senha incorretos.'}).encode('utf-8')
                self.send_response(401)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
        except Exception:
            resp = json.dumps({'ok': False, 'error': 'Erro interno.'}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(resp)))
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
