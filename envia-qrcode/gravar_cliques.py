# -*- coding: utf-8 -*-
"""
Gravador de cliques - faz login, aplica filtros automaticamente e
deixa voce clicar nos elementos para capturar os seletores corretos.
"""

import os
import sys
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(PASTA_ATUAL, "credenciais.cfg")

SCRIPT_GRAVADOR = """
(function () {
  if (window.__gravadorInstalado) return;
  window.__gravadorInstalado = true;

  function getCssPath(el) {
    const path = [];
    while (el && el.nodeType === 1 && el !== document.body) {
      let sel = el.tagName.toLowerCase();
      if (el.id) { sel += '#' + el.id; path.unshift(sel); break; }
      const classes = Array.from(el.classList)
        .filter(c => !c.startsWith('ng-') && c !== 'cdk-focused' && c !== 'mat-focused')
        .slice(0, 3).join('.');
      if (classes) sel += '.' + classes;
      let nth = 1, sib = el.previousElementSibling;
      while (sib) { if (sib.tagName === el.tagName) nth++; sib = sib.previousElementSibling; }
      if (nth > 1) sel += ':nth-of-type(' + nth + ')';
      path.unshift(sel);
      el = el.parentElement;
    }
    return path.join(' > ');
  }

  function getXPath(el) {
    if (el.id) return '//*[@id="' + el.id + '"]';
    const parts = [];
    while (el && el.nodeType === 1) {
      let ix = 1, sib = el.previousElementSibling;
      while (sib) { if (sib.tagName === el.tagName) ix++; sib = sib.previousElementSibling; }
      parts.unshift(el.tagName.toLowerCase() + '[' + ix + ']');
      el = el.parentElement;
    }
    return '/' + parts.join('/');
  }

  document.addEventListener('click', function (e) {
    const el = e.target;
    const txt = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').substring(0, 60);
    const css = getCssPath(el);
    const xp  = getXPath(el);
    console.log('%%CLICK%%|id=' + el.id + '|texto=' + txt + '|css=' + css + '|xpath=' + xp);
  }, true);

  console.log('%%GRAVADOR%% instalado');
})();
"""


def ler_credenciais(caminho):
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
    url   = dados.get("url")
    if not email or not senha or not url:
        print("[ERRO] credenciais.cfg precisa ter email=, passw= e url=")
        sys.exit(1)
    return email, senha, url


def fazer_login(driver, email, senha):
    espera = WebDriverWait(driver, 20)
    campo_email = espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#login-email-desktop")))
    campo_senha = driver.find_element(By.CSS_SELECTOR, "#login-password-desktop")
    campo_email.clear(); campo_email.send_keys(email)
    campo_senha.clear(); campo_senha.send_keys(senha)
    try:
        botao = espera.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(translate(., 'ENTRAR', 'entrar'), 'entrar')]")))
        botao.click()
    except TimeoutException:
        print("[AVISO] Clique em 'Entrar' manualmente.")


def fechar_briefing(driver):
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".greg-briefing__close")))
        els = driver.find_elements(By.CSS_SELECTOR, ".greg-briefing__close > mat-icon:nth-child(1)")
        for el in els:
            if el.is_displayed():
                el.click()
                print("Briefing fechado.")
    except Exception:
        pass


def aplicar_filtros(driver):
    espera = WebDriverWait(driver, 15)
    print("Aplicando filtros automaticamente...")

    espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-top-bar")))
    time.sleep(1)

    espera.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.app-top-bar__page-btn--filter"))).click()

    espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-generic-filter")))
    time.sleep(0.5)

    espera.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-1"))).click()
    espera.until(EC.element_to_be_clickable(
        (By.XPATH, "//mat-option[normalize-space(.)='Aprovado']"))).click()

    try:
        backdrop = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "div.cdk-overlay-transparent-backdrop.cdk-overlay-backdrop-showing")))
        driver.execute_script("arguments[0].click();", backdrop)
    except Exception:
        pass

    espera.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-2"))).click()
    espera.until(EC.element_to_be_clickable(
        (By.XPATH, "//mat-option[normalize-space(.)='Não']"))).click()

    espera.until(EC.element_to_be_clickable((By.CSS_SELECTOR,
        "app-generic-filter button.btn.btn--primary:nth-of-type(2)"))).click()

    print("Filtros aplicados. Aguardando tabela...")
    time.sleep(2)


def main():
    email, senha, url = ler_credenciais(ARQUIVO_CREDENCIAIS)

    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    })
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    print("Abrindo Chrome...")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.get(url)

    print("Fazendo login...")
    fazer_login(driver, email, senha)
    try:
        WebDriverWait(driver, 15).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "#login-email-desktop")))
    except TimeoutException:
        pass

    driver.get(url)
    fechar_briefing(driver)

    try:
        aplicar_filtros(driver)
    except Exception as e:
        print(f"[AVISO] Filtros falharam: {e}")
        print("Aplique os filtros manualmente e pressione Enter para continuar...")
        input()

    print("Instalando gravador...")
    driver.execute_script(SCRIPT_GRAVADOR)

    print()
    print("=" * 60)
    print("Pronto! Clique nos elementos da TABELA para capturar seletores.")
    print("Pressione Ctrl+C quando terminar.")
    print("=" * 60)
    print()

    contador = 0
    try:
        while True:
            time.sleep(1)
            try:
                driver.execute_script(SCRIPT_GRAVADOR)
                for entrada in driver.get_log("browser"):
                    msg = entrada.get("message", "")
                    if "%%CLICK%%" in msg:
                        contador += 1
                        inicio = msg.find("%%CLICK%%")
                        linha = msg[inicio:].replace("%%CLICK%%|", "").replace('"', "")
                        partes = dict(p.split("=", 1) for p in linha.split("|") if "=" in p)
                        print(f"--- Clique #{contador} ---")
                        if partes.get("id"):
                            print(f"  ID    : #{partes['id']}")
                        if partes.get("texto"):
                            print(f"  Texto : {partes['texto']}")
                        print(f"  CSS   : {partes.get('css', '')}")
                        print(f"  XPath : {partes.get('xpath', '')}")
                        print()
                    elif "%%GRAVADOR%%" in msg:
                        print("[Gravador reinstalado]")
            except Exception:
                break
    except KeyboardInterrupt:
        pass

    print(f"\nTotal de cliques capturados: {contador}")
    driver.quit()


if __name__ == "__main__":
    main()
