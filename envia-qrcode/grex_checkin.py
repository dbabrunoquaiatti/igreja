# -*- coding: utf-8 -*-
"""
Grex - automacao de login e filtros
-------------------------------------
- Abre o Chrome em modo mobile REAL (User-Agent + viewport via Chrome DevTools)
- Le credenciais e URL do arquivo credenciais.cfg (mesma pasta deste script)
- Faz login, ativa modo mobile, aplica filtros e fecha popup de briefing

Requisitos (instalar uma vez):
    pip install selenium
"""

import os
import sys
import time
import datetime
import tkinter as tk
from tkinter import messagebox

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

PASTA_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(PASTA_ATUAL, "credenciais.cfg")



def ler_credenciais(caminho):
    """Le um arquivo no formato:
    email=fulano@exemplo.com
    passw=minhasenha
    url=https://...
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
    url = dados.get("url")

    if not email or not senha:
        print("[ERRO] O arquivo credenciais.cfg precisa ter as linhas 'email=' e 'passw='")
        sys.exit(1)

    if not url:
        print("[ERRO] O arquivo credenciais.cfg precisa ter a linha 'url='")
        sys.exit(1)

    return email, senha, url


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

    driver = webdriver.Chrome(options=options)
    return driver


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


def fechar_briefing_se_existir(driver, aguardar_segundos=0):
    """Fecha o painel/modal de briefing, se ele estiver visivel na tela.
    aguardar_segundos: espera ate N segundos pelo popup aparecer antes de desistir."""
    try:
        if aguardar_segundos > 0:
            try:
                WebDriverWait(driver, aguardar_segundos).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".greg-briefing__close"))
                )
            except TimeoutException:
                return
        elementos = driver.find_elements(
            By.CSS_SELECTOR, ".greg-briefing__close > mat-icon:nth-child(1)"
        )
        for el in elementos:
            if el.is_displayed():
                el.click()
                print("Painel de briefing fechado.")
    except Exception:
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


def configurar_filtros(driver):
    """Abre o painel de filtros e seleciona as opcoes configuradas."""
    espera = WebDriverWait(driver, 15)

    # Aguarda a pagina carregar
    espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-top-bar")))
    time.sleep(1)

    print("Abrindo filtros...")
    botao_filtro = espera.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.app-top-bar__page-btn--filter"))
    )
    botao_filtro.click()

    # Aguarda o dialog de filtros aparecer
    espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "app-generic-filter")))
    time.sleep(0.5)

    print("Abrindo 1o dropdown (Status)...")
    select1 = espera.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-1"))
    )
    select1.click()

    print("Selecionando Aprovado...")
    espera.until(
        EC.element_to_be_clickable((By.XPATH, "//mat-option[normalize-space(.)='Aprovado']"))
    ).click()

    # Fecha o dropdown via JS click no backdrop transparente (invisivel ao Selenium)
    try:
        backdrop = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR,
                "div.cdk-overlay-transparent-backdrop.cdk-overlay-backdrop-showing"))
        )
        driver.execute_script("arguments[0].click();", backdrop)
    except Exception:
        pass

    print("Abrindo 2o dropdown...")
    select2 = espera.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "div#mat-select-value-2"))
    )
    select2.click()

    print("Selecionando Nao...")
    espera.until(
        EC.element_to_be_clickable((By.XPATH, "//mat-option[normalize-space(.)='Não']"))
    ).click()

    print("Clicando em Filtrar...")
    espera.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR,
            "app-generic-filter button.btn.btn--primary:nth-of-type(2)"))
    ).click()
    print("Filtros aplicados.")


def enviar_linha(driver, linha_el, idx, total):
    """Abre o menu de uma linha e clica no 5o botao. Retorna (nome, celular)."""
    espera = WebDriverWait(driver, 10)

    celulas = linha_el.find_elements(By.TAG_NAME, "td")
    nome    = celulas[0].text.strip() if len(celulas) > 0 else f"Linha {idx}"
    celular = celulas[1].text.strip() if len(celulas) > 1 else ""

    print(f"[{idx}/{total}] {nome} | {celular}")

    trigger = linha_el.find_element(By.CSS_SELECTOR, "button.mat-mdc-menu-trigger")
    trigger.click()

    botao = espera.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "div[id^='mat-menu-panel'] > div > button:nth-of-type(5)")
    ))
    botao.click()

    try:
        WebDriverWait(driver, 5).until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, "div[id^='mat-menu-panel']"))
        )
    except Exception:
        pass

    print(f"  -> Enviado.")
    return nome, celular


def processar_linhas(driver, arquivo_log):
    """Processa a primeira linha, confirma com o usuario, depois faz o restante."""
    espera = WebDriverWait(driver, 20)

    try:
        espera.until(EC.presence_of_element_located((By.CSS_SELECTOR, "tr.table__row")))
    except Exception:
        print("[AVISO] Nenhuma linha encontrada na tabela.")
        return

    linhas = driver.find_elements(By.CSS_SELECTOR, "tr.table__row")
    total = len(linhas)
    print(f"{total} linha(s) encontrada(s).")

    with open(arquivo_log, "a", encoding="utf-8") as log:
        # Processa somente a primeira linha
        try:
            nome, celular = enviar_linha(driver, linhas[0], 1, total)
            log.write(f"{nome},{celular}\n")
            log.flush()
        except Exception as e:
            print(f"  [AVISO] Falha na linha 1: {e}")
            return

        if total == 1:
            return

        # Pergunta se quer continuar com o restante
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        continuar = messagebox.askyesno(
            "Confirmar",
            f"Primeira linha enviada.\nFoi certinho?\n\nDeseja continuar com as outras {total - 1} linha(s)?",
            parent=root,
        )
        root.destroy()

        if not continuar:
            print("Envio pausado pelo usuario apos a primeira linha.")
            return

        # Processa o restante
        linhas = driver.find_elements(By.CSS_SELECTOR, "tr.table__row")
        for i in range(1, len(linhas)):
            try:
                nome, celular = enviar_linha(driver, linhas[i], i + 1, total)
                log.write(f"{nome},{celular}\n")
                log.flush()
                time.sleep(0.5)
            except Exception as e:
                print(f"  [AVISO] Falha na linha {i + 1}: {e}")


def main():
    print("Lendo credenciais...")
    email, senha, url = ler_credenciais(ARQUIVO_CREDENCIAIS)

    from urllib.parse import urlparse
    origem = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    print("Abrindo Chrome (modo mobile + kiosk)...")
    driver = montar_driver()
    driver.get(url)

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
    driver.get(url)  # recarrega ja em modo mobile

    # Concede permissao de camera/microfone via CDP para a origem do site
    try:
        driver.execute_cdp_cmd("Browser.grantPermissions", {
            "permissions": ["videoCapture", "audioCapture"],
            "origin": origem,
        })
        print("Permissao de camera concedida via CDP.")
    except Exception as e:
        print(f"[AVISO] CDP grantPermissions falhou: {e}")

    # Popup de briefing aparece ao carregar a pagina, antes dos filtros
    fechar_briefing_se_existir(driver, aguardar_segundos=6)

    try:
        configurar_filtros(driver)
    except Exception as e:
        print(f"[AVISO] Falha ao configurar filtros: {e}")

    # Confirma com o usuario antes de continuar
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    continuar = messagebox.askyesno(
        "Confirmar filtros",
        "Os filtros foram aplicados corretamente?\n\nDeseja continuar?",
        parent=root,
    )
    root.destroy()

    if not continuar:
        print("Operacao cancelada pelo usuario.")
        driver.quit()
        sys.exit(0)

    nome_log = datetime.datetime.now().strftime("enviado_%Y%m%d_%H%M%S.log")
    arquivo_log = os.path.join(PASTA_ATUAL, nome_log)
    print(f"Iniciando envios. Log: {nome_log}")
    processar_linhas(driver, arquivo_log)
    print(f"Concluido. Log salvo em: {arquivo_log}")

    print("Tudo pronto. Deixe esta janela do terminal aberta.")
    print("Feche o Chrome ou pressione Ctrl+C aqui para encerrar.")

    # Mantem o script vivo e fecha o popup de briefing caso reaparea
    try:
        while True:
            time.sleep(3)
            try:
                fechar_briefing_se_existir(driver)
            except Exception:
                # Chrome foi fechado pelo usuario
                break
    except KeyboardInterrupt:
        pass

    print("Encerrando.")


if __name__ == "__main__":
    main()
