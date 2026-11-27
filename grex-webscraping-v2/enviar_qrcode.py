#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Envio de QR codes via Selenium para o portal GREX.
Uso:
  python enviar_qrcode.py todos          -> envia para todos (filtros: Aprovado + Nao enviado)
  python enviar_qrcode.py "Nome Pessoa"  -> envia para uma pessoa especifica
"""

import os
import json
import time
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

CHROME_BIN        = "/usr/bin/chromium"
CHROMEDRIVER_BIN  = "/usr/bin/chromedriver"
CHROME_PROFILE    = "/tmp/chrome-profile-qr"
STATUS_FILE       = "/app/data/qrcode_status.json"


def _salvar_status(**kw):
    Path(STATUS_FILE).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), **kw}, f, ensure_ascii=False)
    except Exception:
        pass


def _setup_driver():
    shutil.rmtree(CHROME_PROFILE, ignore_errors=True)
    os.makedirs(CHROME_PROFILE, exist_ok=True)
    os.makedirs("/tmp/chrome-crashes", exist_ok=True)

    opts = Options()
    opts.binary_location = CHROME_BIN
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1366,900")
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    opts.add_argument("--crash-dumps-dir=/tmp/chrome-crashes")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    svc = Service(CHROMEDRIVER_BIN)
    return webdriver.Chrome(service=svc, options=opts)


def _login(driver, email, senha):
    driver.get("https://portal.grex.com.br/login")
    wait = WebDriverWait(driver, 20)
    em_el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#login-email-desktop")))
    pw_el = driver.find_element(By.CSS_SELECTOR, "#login-password-desktop")
    em_el.click(); time.sleep(0.2)
    em_el.send_keys(Keys.CONTROL + "a"); em_el.send_keys(email)
    pw_el.click(); time.sleep(0.2)
    pw_el.send_keys(Keys.CONTROL + "a"); pw_el.send_keys(senha)
    time.sleep(0.3)
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        btn.click()
    except Exception:
        driver.execute_script("document.querySelector(\"button[type='submit']\").click()")
    WebDriverWait(driver, 30).until(lambda d: "login" not in d.current_url)
    print("[QR] Login OK", flush=True)


def _fechar_briefing(driver):
    try:
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".greg-briefing__close")))
        for el in driver.find_elements(By.CSS_SELECTOR, ".greg-briefing__close > mat-icon:nth-child(1)"):
            if el.is_displayed():
                el.click()
    except Exception:
        pass


def _configurar_filtros(driver):
    wait = WebDriverWait(driver, 15)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-top-bar")))
    time.sleep(1)
    wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.app-top-bar__page-btn--filter"))).click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-generic-filter")))
    time.sleep(0.5)
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-1"))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//mat-option[normalize-space(.)='Aprovado']"))).click()
    try:
        bd = WebDriverWait(driver, 3).until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            "div.cdk-overlay-transparent-backdrop.cdk-overlay-backdrop-showing")))
        driver.execute_script("arguments[0].click();", bd)
    except Exception:
        pass
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-2"))).click()
    wait.until(EC.element_to_be_clickable(
        (By.XPATH, "//mat-option[normalize-space(.)='Não']"))).click()
    wait.until(EC.element_to_be_clickable((
        By.CSS_SELECTOR,
        "app-generic-filter button.btn.btn--primary:nth-of-type(2)"))).click()
    time.sleep(2)
    print("[QR] Filtros aplicados", flush=True)


def _enviar_linha(driver, linha_el):
    wait = WebDriverWait(driver, 10)
    trigger = linha_el.find_element(By.CSS_SELECTOR, "button.mat-mdc-menu-trigger")
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", trigger)
    time.sleep(0.3)
    # JS click evita o "element click intercepted" do Angular CDK overlay
    driver.execute_script("arguments[0].click();", trigger)
    botao = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "div[id^='mat-menu-panel'] > div > button:nth-of-type(5)")))
    driver.execute_script("arguments[0].click();", botao)
    try:
        WebDriverWait(driver, 5).until(EC.invisibility_of_element_located(
            (By.CSS_SELECTOR, "div[id^='mat-menu-panel']")))
    except Exception:
        pass


def enviar_por_nome(nome_busca):
    email = os.environ.get("GREX_EMAIL", "")
    senha = os.environ.get("GREX_PASSWORD", "")
    url   = os.environ.get("GREX_PARTICIPANTS_URL", "")

    start_ts = time.time()
    _salvar_status(status="iniciando", modo="individual", nome=nome_busca,
                   total=1, enviados=0, atual=nome_busca, concluido=False, start_ts=start_ts)
    driver = None
    try:
        driver = _setup_driver()
        _login(driver, email, senha)
        driver.get(url)
        _fechar_briefing(driver)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.table__row")))
        time.sleep(1)

        encontrado = False
        pagina = 1
        while not encontrado:
            print(f"[QR] Buscando '{nome_busca}' na página {pagina}...", flush=True)
            linhas = driver.find_elements(By.CSS_SELECTOR, "tr.table__row")
            for linha in linhas:
                cels = linha.find_elements(By.TAG_NAME, "td")
                if cels and nome_busca.lower() in cels[0].text.strip().lower():
                    _salvar_status(status="processando", modo="individual", nome=nome_busca,
                                   total=1, enviados=0, atual=nome_busca, concluido=False,
                                   start_ts=start_ts)
                    _enviar_linha(driver, linha)
                    encontrado = True
                    print(f"[QR] Enviado para {nome_busca}", flush=True)
                    break
            if encontrado:
                break
            # Tentar próxima página
            try:
                next_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "button.mat-mdc-paginator-navigation-next, "
                    "button.mat-paginator-navigation-next, "
                    "button[aria-label='Next page']"
                )
                if next_btn.get_attribute("disabled") or not next_btn.is_enabled():
                    break
                driver.execute_script("arguments[0].click();", next_btn)
                pagina += 1
                time.sleep(1)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "tr.table__row")))
                time.sleep(0.5)
            except Exception:
                break

        if encontrado:
            _salvar_status(status="concluido", modo="individual", nome=nome_busca,
                           total=1, enviados=1, atual="", concluido=True, start_ts=start_ts)
        else:
            _salvar_status(status="nao_encontrado", modo="individual", nome=nome_busca,
                           total=1, enviados=0, atual="", concluido=True,
                           start_ts=start_ts,
                           erro=f"Participante não encontrado: {nome_busca}")
    except Exception as e:
        print(f"[QR] Erro: {e}", flush=True)
        _salvar_status(status="erro", modo="individual", nome=nome_busca,
                       total=1, enviados=0, atual="", concluido=True, erro=str(e))
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


def enviar_todos():
    email = os.environ.get("GREX_EMAIL", "")
    senha = os.environ.get("GREX_PASSWORD", "")
    url   = os.environ.get("GREX_PARTICIPANTS_URL", "")

    _salvar_status(status="iniciando", modo="todos", total=0, enviados=0, atual="", concluido=False)
    driver = None
    try:
        driver = _setup_driver()
        _login(driver, email, senha)
        driver.get(url)
        _fechar_briefing(driver)
        _configurar_filtros(driver)

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr.table__row")))
        except TimeoutException:
            _salvar_status(status="concluido", modo="todos", total=0, enviados=0,
                           atual="", concluido=True)
            return

        time.sleep(1)
        total = len(driver.find_elements(By.CSS_SELECTOR, "tr.table__row"))
        enviados = 0
        falhas = 0
        start_ts = time.time()
        _salvar_status(status="processando", modo="todos", total=total,
                       enviados=0, atual="", concluido=False, start_ts=start_ts)
        print(f"[QR] {total} linha(s) para enviar", flush=True)

        for i in range(total):
            # Re-busca as linhas a cada iteração; se a linha desapareceu do filtro
            # (já foi processada), sempre pega a primeira da lista restante.
            linhas = driver.find_elements(By.CSS_SELECTOR, "tr.table__row")
            # Calcula qual índice real usar: se linhas encurtou, usa 0 (primeira restante)
            idx = i - falhas if (i - falhas) < len(linhas) else 0
            if not linhas:
                break
            if idx >= len(linhas):
                idx = 0
            try:
                cels = linhas[idx].find_elements(By.TAG_NAME, "td")
                nome = cels[0].text.strip() if cels else f"Linha {i+1}"
                _salvar_status(status="processando", modo="todos", total=total,
                               enviados=enviados, atual=nome, concluido=False,
                               start_ts=start_ts)
                _enviar_linha(driver, linhas[idx])
                enviados += 1
                # Atualiza DEPOIS do envio para a porcentagem crescer imediatamente
                _salvar_status(status="processando", modo="todos", total=total,
                               enviados=enviados, atual=nome, concluido=False,
                               start_ts=start_ts)
                print(f"[QR] [{enviados}/{total}] {nome}", flush=True)
                time.sleep(0.5)
            except Exception as e:
                falhas += 1
                print(f"[QR] Falha item {i+1}: {e}", flush=True)

        _salvar_status(status="concluido", modo="todos", total=total,
                       enviados=enviados, atual="", concluido=True, start_ts=start_ts)
        print(f"[QR] Concluido: {enviados}/{total}", flush=True)
    except Exception as e:
        print(f"[QR] Erro geral: {e}", flush=True)
        _salvar_status(status="erro", modo="todos", total=0, enviados=0,
                       atual="", concluido=True, erro=str(e))
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "todos"
    if modo == "todos":
        enviar_todos()
    else:
        enviar_por_nome(modo)
