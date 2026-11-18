# -*- coding: utf-8 -*-
import os
import sys
import json
import hmac
import re as _re
import secrets
import time
import urllib.parse
import requests
from flask import Flask, request, Response, redirect

app = Flask(__name__)

# PROXY_USER/PROXY_PASS têm prioridade; se não definidos, usa GREX_EMAIL/GREX_PASSWORD
_PROXY_USER = os.environ.get('PROXY_USER') or os.environ.get('GREX_EMAIL') or 'admin'
_PROXY_PASS = os.environ.get('PROXY_PASS') or os.environ.get('GREX_PASSWORD') or ''

# Sessões server-side: {token: {'ts': float, 'email': str, 'senha': str}}
_sessions = {}
_SESSION_TTL = 86400  # 24 h

def _cleanup_sessions():
    now = time.time()
    for k in [k for k, v in list(_sessions.items()) if now - v['ts'] > _SESSION_TTL]:
        del _sessions[k]

def _get_session():
    tok = request.cookies.get('grex_session', '')
    sess = _sessions.get(tok)
    if sess and time.time() - sess['ts'] < _SESSION_TTL:
        return sess
    return None

def _session_ok():
    return _get_session() is not None

@app.before_request
def _proxy_auth():
    if request.path.startswith('/grex-login'):
        return
    if _session_ok():
        return
    # Assets nunca devem receber HTML — MIME type seria bloqueado pelo browser
    if _re.search(r'\.(js|mjs|css|png|jpg|jpeg|gif|svg|woff2?|ico|map|webp|json)(\?|$)',
                  request.path, _re.I):
        return Response('Não autorizado', 401)
    is_nav = (request.headers.get('Sec-Fetch-Mode') == 'navigate' or
              (not request.headers.get('Sec-Fetch-Mode') and
               'text/html' in request.headers.get('Accept', '')))
    if request.method in ('GET', 'HEAD') and is_nav:
        return redirect('/grex-login')
    return Response('Não autorizado', 401)

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

# ── Tela de loading: injetada como primeiro filho do <body> pelo servidor ──
# Aparece imediatamente (sem esperar JS/DOMContentLoaded). Só mostra fora de /eventos/check-in.
LOADING_HTML = (
    '<div id="grex-loading" style="display:none;position:fixed;'
    'top:0;right:0;bottom:0;left:0;'
    'z-index:2147483646;background:#0a1628;flex-direction:column;'
    'align-items:center;justify-content:center;gap:28px;">'
    '<style>'
    '@keyframes grex-spin{to{transform:rotate(360deg)}}'
    '@keyframes grex-pulse{0%,100%{opacity:1}50%{opacity:.4}}'
    '.grex-ring{width:72px;height:72px;border-radius:50%;'
    'border:5px solid rgba(255,255,255,.08);border-top-color:#3b82f6;'
    'animation:grex-spin .9s linear infinite}'
    '.grex-loading-label{color:rgba(255,255,255,.5);font:500 15px/1 sans-serif;'
    'letter-spacing:.08em;animation:grex-pulse 2s ease-in-out infinite}'
    '.grex-ir-btn{display:none;margin-top:8px;padding:13px 32px;border-radius:999px;'
    'border:2px solid rgba(255,255,255,.35);background:transparent;color:#fff;'
    'font-size:14px;font-weight:600;cursor:pointer;letter-spacing:.04em;'
    '-webkit-tap-highlight-color:transparent}'
    '</style>'
    '<div class="grex-ring"></div>'
    '<div class="grex-loading-label">Iniciando check-in…</div>'
    '<button class="grex-ir-btn" id="grex-ir-btn"'
    ' onclick="location.href=\'/eventos/check-in\'">Ir para Check-in</button>'
    '<script>(function(){'
    # Só mostra em páginas que fazem parte do fluxo de login (/login, / , /home, etc.)
    # Nunca na tela de check-in (já chegou) nem em rotas desconhecidas sem o flag
    "var p=location.pathname;"
    "var show=(!p.includes('/eventos/check-in'))&&"
    "(p==='/'||p.includes('/login')||p.includes('/home')||"
    "sessionStorage.getItem('grex-autologin')==='1');"
    "if(!show)return;"
    "sessionStorage.setItem('grex-autologin','1');"
    "document.getElementById('grex-loading').style.display='flex';"
    'setTimeout(function(){'
    "var b=document.getElementById('grex-ir-btn');if(b)b.style.display='block';"
    '},15000);'
    'setTimeout(function(){'
    "if(!location.pathname.includes('/eventos/check-in'))"
    "location.href='/eventos/check-in';"
    '},25000);'
    '})()</script>'
    '</div>'
)

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
      position:fixed; top:0; right:0; bottom:0; left:0; z-index:2147483647;
      animation:grex-fadein 0.28s ease;
      cursor:pointer;
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
    d.addEventListener('click', fecharOverlay);
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
    d.addEventListener('click', fecharOverlay);
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

SCRIPT_AUTOLOGIN = r"""
(function () {
  if (window.__grexAutoLogin) return;
  window.__grexAutoLogin = true;

  function irParaCheckin() {
    if (!location.pathname.includes('/eventos/check-in'))
      location.href = '/eventos/check-in';
  }

  if (location.pathname.includes('/eventos/check-in')) return;

  let navegacaoPendente = false;

  new MutationObserver(() => {
    const btn = document.querySelector('.greg-briefing__close > mat-icon:nth-child(1)');
    if (btn && btn.offsetParent !== null && !navegacaoPendente) {
      navegacaoPendente = true;
      btn.click();
      setTimeout(irParaCheckin, 3000);
    }
  }).observe(document.body, {childList: true, subtree: true});

  function visivel(el) {
    return el && el.offsetParent !== null && getComputedStyle(el).display !== 'none';
  }

  function encontrarCampo(seletores) {
    for (const sel of seletores) {
      const el = document.querySelector(sel);
      if (visivel(el)) return el;
    }
    return null;
  }

  function setVal(el, val) {
    el.focus();
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(el, val);
    el.dispatchEvent(new Event('input',  {bubbles: true}));
    el.dispatchEvent(new Event('change', {bubbles: true}));
    el.dispatchEvent(new Event('blur',   {bubbles: true}));
  }

  // Fallback global: se tudo falhar, navega após 22 s
  var _fallbackNav = setTimeout(irParaCheckin, 22000);

  fetch('/grex-autologin-creds', {cache: 'no-store', credentials: 'same-origin'})
    .then(r => r.ok ? r.json() : null)
    .then(creds => {
      if (!creds) {
        clearTimeout(_fallbackNav);
        setTimeout(irParaCheckin, 2000);
        return;
      }
      clearTimeout(_fallbackNav);
      const EMAIL = creds.email;
      const SENHA = creds.senha;

      const poll = setInterval(() => {
        if (location.pathname.includes('/eventos/check-in')) { clearInterval(poll); return; }
        if (navegacaoPendente) return;

        const campoEmail = encontrarCampo([
          '#login-email-desktop',
          '#login-email-mobile',
          'input[type="email"]',
        ]);
        const campoSenha = encontrarCampo([
          '#login-password-desktop',
          '#login-password-mobile',
          'input[type="password"]',
        ]);
        if (!campoEmail || !campoSenha) return;

        clearInterval(poll);
        setVal(campoEmail, EMAIL);
        setVal(campoSenha, SENHA);

        const btnEntrar = document.querySelector("button[type='submit']") ||
          [...document.querySelectorAll('button')].find(b =>
            b.textContent.trim().toLowerCase().includes('entrar')
          );
        if (!btnEntrar) { setTimeout(irParaCheckin, 2000); return; }

        const loginPath = location.pathname;
        setTimeout(() => {
          btnEntrar.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        }, 400);

        // Espera o Angular navegar após auth (pathname muda = sessão estabelecida)
        // em vez de timer fixo — garante que os cookies do GREX já estão gravados
        const loginTimestamp = Date.now();
        const authPoll = setInterval(() => {
          if (Date.now() - loginTimestamp < 1200) return; // mínimo 1.2 s após click
          if (location.pathname !== loginPath) {
            clearInterval(authPoll);
            clearTimeout(authTimer);
            irParaCheckin();
          }
        }, 300);
        const authTimer = setTimeout(() => {
          clearInterval(authPoll);
          irParaCheckin();
        }, 7000);
      }, 1000);

      // Timeout: se não encontrou o form em 12 s, força navegação
      setTimeout(() => {
        if (!location.pathname.includes('/eventos/check-in') && !navegacaoPendente) {
          clearInterval(poll);
          irParaCheckin();
        }
      }, 12000);
    })
    .catch(() => { clearTimeout(_fallbackNav); setTimeout(irParaCheckin, 2000); });
})();
"""

BODY_INJECTION = f"<script>{SCRIPT_CSS}\n{SCRIPT_SONS}\n{SCRIPT_AUTOLOGIN}</script>"
_LOADING_COVER_CSS = (
    "<style id='grex-cover'>"
    # Fora da página de check-in: esconde o conteúdo da app enquanto carrega
    "body:not(.grex-pronto)>app-root{opacity:0!important;pointer-events:none!important}"
    "body:not(.grex-pronto){background:#0a1628!important}"
    "</style>"
    "<script>"
    "if(location.pathname.includes('/eventos/check-in')){"
    "document.write('<style>body{background:initial!important}</style>');"
    "function _gp(){document.body&&document.body.classList.add('grex-pronto');}"
    "if(document.readyState==='loading'){"
    "document.addEventListener('DOMContentLoaded',_gp);"
    "}else{_gp();}"
    "}"
    "</script>"
)
HEAD_INJECTION = f"{_LOADING_COVER_CSS}<script>{SCRIPT_FIREBASE_PROXY}</script>"

HOP_BY_HOP = {
    'host', 'content-length', 'transfer-encoding', 'connection',
    'keep-alive', 'proxy-authenticate', 'proxy-authorization',
    'te', 'trailers', 'upgrade',
}
STRIP_RESPONSE = {
    'content-encoding', 'content-length', 'transfer-encoding', 'connection',
    'content-security-policy', 'content-security-policy-report-only',
    'x-frame-options', 'strict-transport-security',
    'cache-control', 'pragma', 'expires', 'etag', 'last-modified',
}

@app.after_request
def _no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _rewrite_set_cookie(val):
    """Remove Domain= do Set-Cookie para o browser armazenar o cookie no domínio do proxy."""
    return _re.sub(r';\s*[Dd]omain=[^;,]*', '', val)


def _get_resp_headers(resp):
    """Extrai headers filtrando STRIP_RESPONSE e reescrevendo Set-Cookie (domain fix)."""
    raw_cookies = []
    try:
        raw_cookies = resp.raw.headers.getlist('Set-Cookie')
    except AttributeError:
        # urllib3 mais antigo: itera items() que preserva entradas múltiplas
        try:
            raw_cookies = [v for k, v in resp.raw.headers.items()
                           if k.lower() == 'set-cookie']
        except Exception:
            pass
    except Exception:
        pass

    headers = [(k, v) for k, v in resp.headers.items()
               if k.lower() not in STRIP_RESPONSE and k.lower() != 'set-cookie']
    for ck in raw_cookies:
        headers.append(('Set-Cookie', _rewrite_set_cookie(ck)))
    return headers


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

    # Loading overlay injetado como primeiro filho do <body> — aparece imediatamente
    body_open = html.find('<body')
    if body_open != -1:
        body_close = html.find('>', body_open) + 1
        html = html[:body_close] + LOADING_HTML + html[body_close:]

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


_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acesso — Check-in</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Lato,sans-serif;background:linear-gradient(135deg,#0a1628 0%,#1e3a8a 50%,#2563eb 100%);min-height:100vh}
.wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#fff;border-radius:20px;padding:40px 36px;width:100%;max-width:380px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.logo{text-align:center;margin-bottom:8px}
.logo svg{width:56px;height:56px}
.title{font-size:22px;font-weight:700;color:#2c2c2c;text-align:center;margin-bottom:4px}
.sub{font-size:14px;color:#666;text-align:center;margin-bottom:28px}
.grp{margin-bottom:16px}
.grp label{display:block;font-size:13px;font-weight:600;color:#2c2c2c;margin-bottom:6px}
.grp input{width:100%;padding:12px 14px;border:1.5px solid #e8e8e8;border-radius:10px;font-size:16px;color:#2c2c2c;background:#f5f5f5;outline:none;transition:border-color .2s;-webkit-appearance:none;appearance:none}
.grp input:focus{border-color:#2563eb;background:#fff}
.btn{width:100%;padding:14px;background:linear-gradient(135deg,#2563eb,#3b82f6);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;margin-top:8px;position:relative;overflow:hidden;transition:opacity .2s,transform .1s;-webkit-tap-highlight-color:transparent}
.btn:active{transform:scale(.98);opacity:.9}
.btn:disabled{opacity:.7;cursor:not-allowed}
.btn-txt{transition:opacity .2s;display:block}
.btn-spin{display:none;position:absolute;top:0;right:0;bottom:0;left:0;align-items:center;justify-content:center}
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
<div class="logo"><svg viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="56" rx="14" fill="#2563eb"/><path d="M28 14L38 20V32L28 38L18 32V20L28 14Z" stroke="white" stroke-width="2.5" stroke-linejoin="round"/><circle cx="28" cy="26" r="5" fill="white"/></svg></div>
<div class="title">Check-in Grex</div>
<div class="sub">Entre para continuar</div>
<div class="err" id="err"></div>
<form id="frm" method="POST" action="/grex-login" autocomplete="on">
<div class="grp"><label for="u">E-mail</label><input type="email" id="u" name="user" autocomplete="username" inputmode="email" placeholder="seu@email.com" required></div>
<div class="grp"><label for="p">Senha</label><input type="password" id="p" name="pass" autocomplete="current-password" placeholder="••••••••" required></div>
<button type="submit" class="btn" id="btn"><span class="btn-txt">Entrar</span><span class="btn-spin"><span class="ring"></span></span></button>
</form>
</div></div>
<script>
(function(){
var frm=document.getElementById('frm'),btn=document.getElementById('btn'),errEl=document.getElementById('err');
function showErr(m){errEl.textContent=m;errEl.classList.add('show');}
function setLoad(on){btn.disabled=on;btn.classList.toggle('loading',on);}
var p=new URLSearchParams(location.search);
if(p.get('err'))showErr(decodeURIComponent(p.get('err')));
frm.addEventListener('submit',function(e){
  var u=document.getElementById('u').value.trim();
  var pw=document.getElementById('p').value;
  if(!u||!pw){e.preventDefault();showErr('Preencha e-mail e senha.');return;}
  setLoad(true);
});
})();
</script>
</body>
</html>"""


@app.route('/grex-login', methods=['GET'])
def grex_login_get():
    if _session_ok():
        return redirect('/')
    return Response(_LOGIN_HTML, content_type='text/html; charset=utf-8')


@app.route('/grex-login', methods=['POST'])
def grex_login_post():
    ct = request.content_type or ''
    if 'application/json' in ct:
        data = request.get_json(silent=True) or {}
        user = str(data.get('user', ''))
        pwd  = str(data.get('pass', ''))
        is_json = True
    else:
        user = str(request.form.get('user', ''))
        pwd  = str(request.form.get('pass', ''))
        is_json = False

    if _PROXY_PASS:
        ok = (hmac.compare_digest(user, _PROXY_USER) and
              hmac.compare_digest(pwd,  _PROXY_PASS))
    else:
        ok = bool(user and pwd)

    if ok:
        _cleanup_sessions()
        tok = secrets.token_urlsafe(32)
        _sessions[tok] = {'ts': time.time(), 'email': user, 'senha': pwd}
        if is_json:
            resp = Response(json.dumps({'ok': True}), content_type='application/json')
        else:
            resp = redirect('/')
        resp.set_cookie('grex_session', tok, httponly=True,
                        samesite='Lax', path='/', secure=True)
        return resp

    if is_json:
        return Response(
            json.dumps({'ok': False, 'error': 'E-mail ou senha incorretos.'}),
            status=401, content_type='application/json',
        )
    return redirect('/grex-login?err=' + urllib.parse.quote('E-mail ou senha incorretos.'))


@app.route('/grex-firebase/<host>/<path:path>',
           methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def firebase_proxy(host, path):
    """Encaminha chamadas Firebase com Origin correto para evitar bloqueio de domínio."""
    if host not in FIREBASE_HOSTS:
        return Response("Host not allowed", status=403)
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

    resp_headers = _get_resp_headers(resp)
    return Response(resp.content, resp.status_code, resp_headers)


@app.route('/grex-autologin-creds')
def autologin_creds():
    sess = _get_session()
    if sess and sess.get('email') and sess.get('senha'):
        email, senha = sess['email'], sess['senha']
    else:
        email, senha = GREX_EMAIL, GREX_SENHA
    resp = Response(
        json.dumps({'email': email, 'senha': senha}),
        content_type='application/json',
    )
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    url = f"{GREX_BASE}/{path}"
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', errors='replace')

    # Não envia grex_session (cookie do proxy) para o GREX upstream
    grex_cookies = {k: v for k, v in request.cookies.items() if k != 'grex_session'}

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=_build_upstream_headers(),
            data=request.get_data(),
            cookies=grex_cookies,
            allow_redirects=False,
            timeout=30,
        )
    except requests.RequestException as e:
        return Response(f"Erro ao conectar com o Grex: {e}", status=502)

    # Reescreve Set-Cookie removendo Domain= para o browser armazenar no domínio do proxy
    resp_headers = _get_resp_headers(resp)

    if resp.status_code in (301, 302, 303, 307, 308):
        # Só intercepta redirect externo em navegações HTML — nunca em assets (JS/CSS/etc.)
        is_asset_req = bool(_re.search(
            r'\.(js|mjs|css|png|jpg|jpeg|gif|svg|woff2?|ico|map|webp|json)(\?|$)',
            request.path, _re.I))
        new_hdrs = []
        for k, v in resp_headers:
            if k.lower() == 'location':
                if GREX_BASE in v:
                    v = v.replace(GREX_BASE, proxy_base())
                elif v.startswith('http') and proxy_base() not in v and not is_asset_req:
                    v = '/eventos/check-in'
            new_hdrs.append((k, v))
        resp_headers = new_hdrs

    content_type = resp.headers.get('Content-Type', '')
    if 'text/html' in content_type:
        return Response(inject_and_rewrite(resp.content), resp.status_code, resp_headers)

    return Response(resp.content, resp.status_code, resp_headers)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
