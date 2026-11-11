# -*- coding: utf-8 -*-
import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

GREX_BASE = "https://portal.grex.com.br"

FIREBASE_HOSTS = [
    'firebaseinstallations.googleapis.com',
    'identitytoolkit.googleapis.com',
    'securetoken.googleapis.com',
    'firebaselogging-pa.googleapis.com',
    'firebaseremoteconfig.googleapis.com',
    'firebase.googleapis.com',
]


def _ler_credenciais():
    email = os.environ.get('GREX_EMAIL', '').strip()
    senha = os.environ.get('GREX_PASSWORD', '').strip()
    if email and senha:
        return email, senha
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credenciais.cfg')
    if os.path.exists(cfg):
        with open(cfg, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if '=' not in linha:
                    continue
                chave, valor = linha.split('=', 1)
                chave = chave.strip().lower()
                if chave == 'email':
                    email = valor.strip()
                elif chave in ('passw', 'senha', 'password'):
                    senha = valor.strip()
    return email, senha


GREX_EMAIL, GREX_SENHA = _ler_credenciais()

# ── Patch fetch/XHR: intercepta chamadas Firebase e as redireciona pelo proxy ──
# Deve ser injetado o mais cedo possível (no <head>), antes do Firebase SDK iniciar.
SCRIPT_FIREBASE_PROXY = r"""
(function () {
  if (window.__grexFirebaseProxy) return;
  window.__grexFirebaseProxy = true;
  const HOSTS = """ + str(FIREBASE_HOSTS) + r""";
  const BASE = window.location.origin + '/grex-firebase/';

  const _fetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    let url = (input instanceof Request) ? input.url : String(input);
    for (const h of HOSTS) {
      if (url.startsWith('https://' + h)) {
        const newUrl = BASE + h + url.slice(('https://' + h).length);
        input = (input instanceof Request) ? new Request(newUrl, input) : newUrl;
        break;
      }
    }
    return _fetch(input, init);
  };

  const _open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url) {
    let u = String(url);
    for (const h of HOSTS) {
      if (u.startsWith('https://' + h)) {
        u = BASE + h + u.slice(('https://' + h).length);
        break;
      }
    }
    return _open.apply(this, [method, u, ...Array.prototype.slice.call(arguments, 2)]);
  };
})();
"""

SCRIPT_CSS = r"""
(function () {
  if (document.getElementById('grex-estilos-custom')) return;
  const s = document.createElement('style');
  s.id = 'grex-estilos-custom';
  s.textContent = `
    .side-menu__brand,
    #app-side-menu-nav,
    .list__footer,
    .app-top-bar__inner { display: none !important; }

    .side-menu__brand,
    .side-menu__brand *,
    greg-side-menu,
    app-side-menu {
      background: transparent !important;
      background-image: none !important;
    }
  `;
  document.head.appendChild(s);
})();
"""

SCRIPT_SONS = r"""
(function () {
  if (window.__grexAlertaInstalado) return;
  window.__grexAlertaInstalado = true;

  let audioCtx = null;
  function getCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
  }
  function tocarTom(freq, dur, tipo, vol, atraso) {
    const ctx = getCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = tipo; osc.frequency.value = freq; gain.gain.value = vol;
    osc.connect(gain); gain.connect(ctx.destination);
    const t = ctx.currentTime + atraso / 1000;
    osc.start(t); osc.stop(t + dur / 1000);
  }
  function tocarSucesso() {
    tocarTom(523, 100, 'sine', 0.455, 0);
    tocarTom(659, 100, 'sine', 0.455, 110);
    tocarTom(784, 220, 'sine', 0.455, 220);
  }
  function tocarErro() {
    tocarTom(300, 220, 'square', 0.455, 0);
    tocarTom(220, 300, 'square', 0.455, 250);
  }

  const CSS = `
    @keyframes grex-fadein { from { opacity:0 } to { opacity:1 } }
    @keyframes grex-pop    { from { transform:scale(0.88); opacity:0 } to { transform:scale(1); opacity:1 } }
    @keyframes grex-draw   { to { stroke-dashoffset: 0 } }
    #grex-overlay {
      position:fixed; inset:0; z-index:2147483647;
      animation:grex-fadein 0.28s ease;
    }
    .grex-card {
      width:100%; height:100%;
      display:flex; flex-direction:column;
      align-items:center; justify-content:center;
      text-align:center;
      animation:grex-pop 0.35s cubic-bezier(0.175,0.885,0.32,1.275);
    }
    .grex-card.sucesso { background:#14532d; }
    .grex-card.erro    { background:#7f1d1d; }
    .grex-circulo {
      width:120px; height:120px; border-radius:50%;
      display:flex; align-items:center; justify-content:center;
      margin-bottom:36px;
    }
    .sucesso .grex-circulo { background:#22c55e; }
    .erro    .grex-circulo { background:#ef4444; }
    .grex-path {
      stroke-dasharray:100; stroke-dashoffset:100;
      animation:grex-draw 0.45s 0.1s ease forwards;
    }
    .grex-titulo {
      color:#fff; font-size:36px; font-weight:700;
      font-family:sans-serif; margin-bottom:12px;
    }
    .grex-sub {
      color:rgba(255,255,255,0.7); font-size:18px;
      font-family:sans-serif; margin:0; max-width:480px;
    }
    .grex-btn {
      margin-top:48px; padding:18px 64px; border-radius:999px;
      border:none; background:#fff; color:#7f1d1d;
      font-size:20px; font-weight:700; font-family:sans-serif;
      cursor:pointer; letter-spacing:0.3px;
    }
    .grex-btn:active { opacity:0.85; }
  `;

  function injetarCSS() {
    if (document.getElementById('grex-overlay-css')) return;
    const s = document.createElement('style');
    s.id = 'grex-overlay-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function fecharOverlay() {
    const el = document.getElementById('grex-overlay');
    if (el) el.remove();
  }

  function limparTexto(raw) {
    return (raw || '').replace(/\b[a-z]+(?:_[a-z]+)+\b/g, '').replace(/\s+/g, ' ').trim();
  }

  function mostrarSucesso() {
    injetarCSS(); fecharOverlay();
    const d = document.createElement('div');
    d.id = 'grex-overlay';
    d.innerHTML = `
      <div class="grex-card sucesso">
        <div class="grex-circulo">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <polyline class="grex-path" pathLength="100"
              points="12,30 24,42 44,16"
              stroke="white" stroke-width="5.5"
              stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <div class="grex-titulo">Check-in realizado!</div>
        <div class="grex-sub">Fechando em 5 segundos…</div>
      </div>`;
    document.body.appendChild(d);
    setTimeout(fecharOverlay, 5000);
  }

  function mostrarErro(msg) {
    injetarCSS(); fecharOverlay();
    const txt = limparTexto(msg) || 'Tente novamente.';
    const d = document.createElement('div');
    d.id = 'grex-overlay';
    d.innerHTML = `
      <div class="grex-card erro">
        <div class="grex-circulo">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <line class="grex-path" pathLength="100"
              x1="16" y1="16" x2="40" y2="40"
              stroke="white" stroke-width="5.5" stroke-linecap="round"/>
            <line class="grex-path" pathLength="100"
              x1="40" y1="16" x2="16" y2="40"
              stroke="white" stroke-width="5.5" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="grex-titulo">Erro no check-in</div>
        <div class="grex-sub">${txt}</div>
        <div class="grex-sub" style="margin-top:12px;font-size:13px;opacity:0.5">Fechando em 5 segundos…</div>
      </div>`;
    document.body.appendChild(d);
    setTimeout(fecharOverlay, 5000);
  }

  let ultimoDisparo = 0;
  const INTERVALO_MIN_MS = 2000;

  function verificarLabel(el) {
    const agora = Date.now();
    if (agora - ultimoDisparo < INTERVALO_MIN_MS) return;
    const txt = (el.innerText || el.textContent || '').toLowerCase().trim();
    if (!txt) return;
    if (txt.includes('sucesso')) {
      ultimoDisparo = agora;
      tocarSucesso();
      mostrarSucesso();
    } else if (txt.includes('erro') || txt.includes('error') || txt.includes('inv') || txt.includes('nao encontrado') || txt.includes('não encontrado')) {
      ultimoDisparo = agora;
      tocarErro();
      mostrarErro(el.innerText || el.textContent || '');
    }
  }

  new MutationObserver((mutacoes) => {
    for (const m of mutacoes) {
      for (const node of m.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches && node.matches('.mat-mdc-snack-bar-label')) {
          verificarLabel(node);
        }
        if (node.querySelectorAll) {
          for (const label of node.querySelectorAll('.mat-mdc-snack-bar-label')) {
            verificarLabel(label);
          }
        }
      }
    }
  }).observe(document.body, { childList: true, subtree: true });
})();
"""

SCRIPT_AUTOLOGIN = """
(function () {{
  if (window.__grexAutoLogin) return;
  window.__grexAutoLogin = true;
  const EMAIL = {email};
  const SENHA = {senha};

  function setVal(el, val) {{
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input', {{bubbles: true}}));
    el.dispatchEvent(new Event('change', {{bubbles: true}}));
  }}

  function fecharBriefing() {{
    document.querySelectorAll('.greg-briefing__close > mat-icon:nth-child(1)').forEach(el => {{
      if (el.offsetParent !== null) el.click();
    }});
  }}

  function irParaCheckin() {{
    if (!window.location.pathname.includes('/eventos/check-in')) {{
      window.location.href = '/eventos/check-in';
    }}
  }}

  // Fecha briefing sempre que aparecer no DOM
  new MutationObserver(fecharBriefing).observe(document.body, {{childList: true, subtree: true}});

  // Já está na página certa: apenas fecha briefing e encerra
  if (window.location.pathname.includes('/eventos/check-in')) {{
    fecharBriefing();
    return;
  }}

  // Aguarda o modal de briefing aparecer, fecha e só então navega após 3s.
  // Se o modal nunca aparecer, navega após timeout de segurança.
  function aguardarBriefingENavegar() {{
    let navegou = false;
    function navegar() {{
      if (navegou) return;
      navegou = true;
      setTimeout(irParaCheckin, 3000);
    }}
    const obsModal = new MutationObserver(() => {{
      const btn = document.querySelector('.greg-briefing__close > mat-icon:nth-child(1)');
      if (btn && btn.offsetParent !== null) {{
        obsModal.disconnect();
        btn.click();
        navegar();
      }}
    }});
    obsModal.observe(document.body, {{childList: true, subtree: true}});
    // Fallback: se o modal não aparecer em 12s, navega de qualquer forma
    setTimeout(() => {{ obsModal.disconnect(); navegar(); }}, 12000);
  }}

  function tentarLogin() {{
    const campoEmail = document.querySelector('#login-email-desktop');
    const campoSenha = document.querySelector('#login-password-desktop');
    if (!campoEmail || !campoSenha) return false;
    if (EMAIL && SENHA) {{
      setVal(campoEmail, EMAIL);
      setVal(campoSenha, SENHA);
    }}
    const btn = [...document.querySelectorAll('button')].find(b =>
      b.textContent.trim().toLowerCase().includes('entrar')
    );
    if (btn) {{
      setTimeout(() => {{
        btn.click();
        aguardarBriefingENavegar();
      }}, 400);
    }}
    return true;
  }}

  if (!tentarLogin()) {{
    const obs = new MutationObserver(() => {{ if (tentarLogin()) obs.disconnect(); }});
    obs.observe(document.body, {{childList: true, subtree: true}});
    // Sessão já ativa (sem formulário): navega direto após 3s
    setTimeout(() => {{ obs.disconnect(); irParaCheckin(); }}, 3000);
  }}
}})();
""".format(
    email=repr(GREX_EMAIL),
    senha=repr(GREX_SENHA),
)

BODY_INJECTION = f"<script>{SCRIPT_CSS}\n{SCRIPT_SONS}\n{SCRIPT_AUTOLOGIN}</script>"
HEAD_INJECTION = f"<script>{SCRIPT_FIREBASE_PROXY}</script>"

HOP_BY_HOP = {
    'host', 'content-length', 'transfer-encoding', 'connection',
    'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'upgrade',
}
STRIP_RESPONSE = {
    'content-encoding', 'content-length', 'transfer-encoding', 'connection',
    'content-security-policy', 'content-security-policy-report-only',
    'x-frame-options', 'strict-transport-security',
}


def proxy_base():
    return request.url_root.rstrip('/')


def inject_and_rewrite(html_bytes):
    html = html_bytes.decode('utf-8', errors='replace')
    html = html.replace(GREX_BASE, proxy_base())

    # Firebase proxy patch vai no <head> para rodar antes do Firebase SDK
    head_pos = html.find('<head>')
    if head_pos != -1:
        insert = head_pos + len('<head>')
        html = html[:insert] + HEAD_INJECTION + html[insert:]

    # Demais scripts vão no fim do <body>
    body_pos = html.rfind('</body>')
    if body_pos != -1:
        html = html[:body_pos] + BODY_INJECTION + html[body_pos:]
    else:
        html += BODY_INJECTION

    return html.encode('utf-8')


def _build_upstream_headers():
    headers = {k: v for k, v in request.headers if k.lower() not in HOP_BY_HOP}
    headers['Accept-Encoding'] = 'gzip, deflate'
    proxy_origin = request.host_url.rstrip('/')
    for hdr in ('referer', 'origin'):
        if hdr in headers:
            headers[hdr] = headers[hdr].replace(proxy_origin, GREX_BASE)
    return headers


@app.route('/grex-firebase/<host>/<path:path>',
           methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def firebase_proxy(host, path):
    """Encaminha chamadas Firebase com Origin correto para evitar bloqueio de domínio."""
    url = f"https://{host}/{path}"
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', errors='replace')

    headers = {k: v for k, v in request.headers if k.lower() not in HOP_BY_HOP}
    headers['Accept-Encoding'] = 'gzip, deflate'
    headers['Origin'] = GREX_BASE
    headers['Referer'] = GREX_BASE + '/'

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data(),
            allow_redirects=False,
            timeout=30,
        )
    except requests.RequestException as e:
        return Response(f"Erro Firebase proxy: {e}", status=502)

    resp_headers = [(k, v) for k, v in resp.headers.items()
                    if k.lower() not in STRIP_RESPONSE]
    return Response(resp.content, resp.status_code, resp_headers)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    url = f"{GREX_BASE}/{path}"
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', errors='replace')

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=_build_upstream_headers(),
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
        )
    except requests.RequestException as e:
        return Response(f"Erro ao conectar com o Grex: {e}", status=502)

    resp_headers = [(k, v) for k, v in resp.headers.items()
                    if k.lower() not in STRIP_RESPONSE]

    if resp.status_code in (301, 302, 303, 307, 308):
        resp_headers = [
            (k, v.replace(GREX_BASE, proxy_base()) if k.lower() == 'location' else v)
            for k, v in resp_headers
        ]

    content_type = resp.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        return Response(inject_and_rewrite(resp.content), resp.status_code, resp_headers)

    return Response(resp.content, resp.status_code, resp_headers)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
