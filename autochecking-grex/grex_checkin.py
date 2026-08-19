# -*- coding: utf-8 -*-
"""
Grex Check-in - automacao completa
-----------------------------------
- Abre o Chrome em modo mobile REAL (User-Agent + viewport via Chrome DevTools)
- Le e-mail/senha do arquivo credenciais.cfg (mesma pasta deste script)
- Preenche o login e clica em "Entrar"
- Injeta um script que toca som de sucesso/erro no check-in
- Roda em kiosk (tela cheia, sem barra de navegador)

Requisitos (instalar uma vez, veja instrucoes no chat):
    pip install selenium
"""

import os
import re
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

URL_CHECKIN = "https://portal.grex.com.br/eventos/check-in"
PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(PASTA_ATUAL, "credenciais.cfg")

# JS que monitora sucesso/erro e toca som (Web Audio API, nao precisa de arquivo)
SCRIPT_CSS = """
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

# JS que monitora sucesso/erro, toca som e exibe overlay animado
SCRIPT_SONS = r"""
(function () {
  if (window.__grexAlertaInstalado) return;
  window.__grexAlertaInstalado = true;

  // ── Audio ──────────────────────────────────────────────────────────────────
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

  // ── Estilos do overlay ─────────────────────────────────────────────────────
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

  // Remove nomes de icones do Material (ex: "report_problem") que aparecem
  // no innerText do snackbar quando ha um <mat-icon> dentro do label
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

  // ── Detecção de snackbar ───────────────────────────────────────────────────
  let ultimoDisparo = 0;
  const INTERVALO_MIN_MS = 2000;

  function verificarLabel(el) {
    const agora = Date.now();
    if (agora - ultimoDisparo < INTERVALO_MIN_MS) return;
    const txt = (el.innerText || el.textContent || '').toLowerCase().trim();
    if (!txt) return;
    console.log('[Grex Alerta][DEBUG] Snackbar texto:', JSON.stringify(txt));
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



def ler_credenciais(caminho):
    """Le um arquivo no formato:
    email=fulano@exemplo.com
    passw=minhasenha
    """
    if not os.path.exists(caminho):
        print(f"[ERRO] Arquivo de credenciais nao encontrado: {caminho}")
        sys.exit(1)

    dados = {}
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            dados[chave.strip().lower()] = valor.strip()

    email = dados.get("email")
    senha = dados.get("passw") or dados.get("senha") or dados.get("password")

    if not email or not senha:
        print("[ERRO] O arquivo credenciais.cfg precisa ter as linhas 'email=' e 'passw='")
        sys.exit(1)

    return email, senha


MOBILE_UA = (
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 "
    "Mobile/15E148 Safari/604.1"
)


def montar_driver():
    options = webdriver.ChromeOptions()

    # NAO ativamos emulacao mobile aqui de proposito: o login usa um
    # formulario "-desktop", entao precisamos comecar em modo desktop
    # e so trocar para mobile DEPOIS de logar (veja ativar_modo_mobile).

    # --- Camera liberada sem popup de permissao + salvar senha desativado ---
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.media_stream_mic": 1,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })

    # --- Autoplay liberado (necessario para os sons tocarem sem clique) ---
    options.add_argument("--autoplay-policy=no-user-gesture-required")

    # --- Camera real via WebRTC sem bloqueio do sandbox ---
    options.add_argument("--use-fake-ui-for-media-stream")  # aceita permissao sem popup (camera real)
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")

    # --- Kiosk (tela cheia, sem barra de endereco) ---
    options.add_argument("--kiosk")
    options.add_argument("--window-size=1366,900")

    # Reduz ruido de logs no console
    options.add_argument("--log-level=3")
    options.add_experimental_option(
        "excludeSwitches", ["enable-logging", "enable-automation"]
    )
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Habilita captura dos console.log() da pagina, para conseguirmos ver
    # no terminal mesmo sem abrir o DevTools (que fica bloqueado em kiosk)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    driver = webdriver.Chrome(options=options)
    return driver


def mostrar_logs_console(driver):
    """Le os console.log() da pagina e imprime no terminal os que forem
    relevantes (prefixo [Grex Alerta])."""
    try:
        for entrada in driver.get_log("browser"):
            msg = entrada.get("message", "")
            if "Grex Alerta" in msg:
                print("[NAVEGADOR]", msg)
    except Exception:
        pass


def ativar_modo_mobile(driver):
    """Troca o navegador para 'modo mobile' de verdade (viewport + user-agent
    reais, via Chrome DevTools Protocol), mas usando o tamanho real da tela
    (como um tablet grande), em vez de encolher para tamanho de celular."""
    largura, altura = driver.execute_script(
        "return [window.screen.width, window.screen.height]"
    )
    driver.execute_cdp_cmd(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": largura,
            "height": altura,
            "deviceScaleFactor": 1,
            "mobile": True,
            "screenWidth": largura,
            "screenHeight": altura,
        },
    )
    driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": MOBILE_UA})
    driver.execute_cdp_cmd("Emulation.setTouchEmulationEnabled", {"enabled": True})


def fechar_briefing_se_existir(driver):
    """Fecha o painel/modal de briefing, se ele estiver visivel na tela."""
    try:
        elementos = driver.find_elements(
            By.CSS_SELECTOR, ".greg-briefing__close > mat-icon:nth-child(1)"
        )
        for el in elementos:
            if el.is_displayed():
                el.click()
                print("Painel de briefing fechado.")
    except Exception:
        # Se nao existir na tela, apenas ignora
        pass


def fazer_login(driver, email, senha):
    espera = WebDriverWait(driver, 20)

    campo_email = espera.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#login-email-desktop"))
    )
    campo_senha = driver.find_element(By.CSS_SELECTOR, "#login-password-desktop")

    campo_email.clear()
    campo_email.send_keys(email)
    campo_senha.clear()
    campo_senha.send_keys(senha)

    # Tenta achar o botao "Entrar" por texto (nao foi passado um seletor exato)
    try:
        botao = espera.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(translate(., 'ENTRAR', 'entrar'), 'entrar')]")
            )
        )
        botao.click()
    except TimeoutException:
        print("[AVISO] Nao encontrei o botao 'Entrar' automaticamente.")
        print("        Pressione Enter manualmente no site, ou me avise o seletor exato do botao.")


def main():
    print("Lendo credenciais...")
    email, senha = ler_credenciais(ARQUIVO_CREDENCIAIS)

    print("Abrindo Chrome (modo mobile + kiosk)...")
    driver = montar_driver()
    driver.get(URL_CHECKIN)

    print("Fazendo login (modo desktop)...")
    fazer_login(driver, email, senha)

    # Aguarda o redirect pos-login (formulario some da tela)
    try:
        WebDriverWait(driver, 15).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "#login-email-desktop"))
        )
    except TimeoutException:
        pass

    print("Ativando modo mobile...")
    ativar_modo_mobile(driver)
    driver.get(URL_CHECKIN)  # recarrega ja em modo mobile

    # Concede permissao de camera/microfone via CDP para a origem do site
    # (mais confiavel que flags ou prefs para WebRTC/getUserMedia)
    try:
        driver.execute_cdp_cmd("Browser.grantPermissions", {
            "permissions": ["videoCapture", "audioCapture"],
            "origin": "https://portal.grex.com.br",
        })
        print("Permissao de camera concedida via CDP.")
    except Exception as e:
        print(f"[AVISO] CDP grantPermissions falhou: {e}")

    fechar_briefing_se_existir(driver)

    print("Instalando alertas sonoros e estilos...")
    # Reinjeta o script sempre que a pagina navegar/recarregar
    driver.execute_script(SCRIPT_SONS)
    driver.execute_script(SCRIPT_CSS)

    print("Tudo pronto. Deixe esta janela do terminal aberta.")
    print("Feche o Chrome ou pressione Ctrl+C aqui para encerrar.")

    # Mantem o script vivo e reinstala o listener de som a cada poucos segundos
    # (cobre casos de navegacao interna / SPA que troca o DOM inteiro)
    try:
        while True:
            time.sleep(3)
            try:
                driver.execute_script(SCRIPT_SONS)
                driver.execute_script(SCRIPT_CSS)
                fechar_briefing_se_existir(driver)
                mostrar_logs_console(driver)
            except Exception:
                # Chrome foi fechado pelo usuario
                break
    except KeyboardInterrupt:
        pass

    print("Encerrando.")


if __name__ == "__main__":
    main()
