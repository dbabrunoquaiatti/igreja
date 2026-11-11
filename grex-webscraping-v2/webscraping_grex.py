"""
Script de web scraping para GREX - Automação de login e download de participantes
⚠️ AVISO DE SEGURANÇA: Este script contém credenciais. Use variáveis de ambiente em produção!
"""

import os
import shutil
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

CHROME_BIN = "/usr/bin/chromium"
CHROMEDRIVER_BIN = "/usr/bin/chromedriver"
CHROME_PROFILE_DIR = "/tmp/chrome-profile"
CHROMEDRIVER_LOG = "/tmp/chromedriver.log"


def _diagnosticar_chromium():
    """Verifica se o binário do Chromium existe e consegue rodar headless"""
    # 1. Verificar existência
    for path in [CHROME_BIN, "/usr/bin/chromium-browser", "/usr/bin/google-chrome-stable"]:
        if os.path.exists(path):
            print(f"🔍 Binário encontrado: {path}")
            break
    else:
        print(f"❌ CHROMIUM NÃO ENCONTRADO em nenhum caminho padrão")

    # 2. Versão
    try:
        v = subprocess.run([CHROME_BIN, "--version"], capture_output=True, text=True, timeout=10)
        print(f"🔍 Versão: {(v.stdout or v.stderr).strip()}")
    except FileNotFoundError:
        print(f"❌ {CHROME_BIN} não encontrado (FileNotFoundError)")
    except Exception as e:
        print(f"⚠️ Erro ao obter versão: {e}")

    # 3. Teste headless direto (fora do Selenium)
    print("🧪 Testando Chromium headless diretamente...")
    try:
        shutil.rmtree(CHROME_PROFILE_DIR, ignore_errors=True)
        os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
        os.makedirs("/tmp/chrome-crashes", exist_ok=True)
        test = subprocess.run(
            [CHROME_BIN, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--disable-dev-shm-usage", f"--user-data-dir={CHROME_PROFILE_DIR}",
             "--crash-dumps-dir=/tmp/chrome-crashes",
             "--dump-dom", "about:blank"],
            capture_output=True, text=True, timeout=20
        )
        if test.returncode == 0:
            print("✅ Chromium headless OK")
        else:
            print(f"❌ Chromium saiu com código {test.returncode}")
            if test.stderr:
                print(f"   stderr:\n{test.stderr[:1500]}")
    except Exception as e:
        print(f"❌ Falha no teste Chromium: {e}")


def setup_driver():
    """Configura o driver do Chrome com opções de download"""
    _diagnosticar_chromium()

    # Criar pasta data se não existir
    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)

    # Limpar perfil do Chrome entre execuções (evita conflito de lock)
    shutil.rmtree(CHROME_PROFILE_DIR, ignore_errors=True)
    os.makedirs(CHROME_PROFILE_DIR, exist_ok=True)
    os.makedirs("/tmp/chrome-crashes", exist_ok=True)

    chrome_options = Options()
    chrome_options.binary_location = CHROME_BIN

    prefs = {
        "download.default_directory": str(data_folder.absolute()),
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False,
        "plugins.always_open_pdf_externally": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    # Evitar detecção de automação pelo site
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-component-update")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-device-discovery-notifications")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=TranslateUI")
    chrome_options.add_argument("--disable-sync-preferences")
    chrome_options.add_argument("--metrics-recording-only")

    # Essencial para rodar em Docker como não-root
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--remote-debugging-port=0")
    # Chromium 156 (Debian trixie): --disable-crash-reporter impede inicialização do crashpad
    # mas Chrome ainda spawna o handler sem --database → mata o processo.
    # Solução: deixar o crashpad inicializar normalmente com diretório explícito.
    chrome_options.add_argument("--crash-dumps-dir=/tmp/chrome-crashes")

    service = Service(
        CHROMEDRIVER_BIN,
        service_args=["--verbose", f"--log-path={CHROMEDRIVER_LOG}"]
    )
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver


def _preencher_campo_angular(driver, element, text):
    """Preenche um campo usando native value setter + eventos Angular/React"""
    element.click()
    # Usar native setter para bypassar React/Angular synthetic events
    driver.execute_script("""
        var el = arguments[0];
        var nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value').set;
        nativeSetter.call(el, arguments[1]);
        el.dispatchEvent(new Event('input',  { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    """, element, text)
    # send_keys garante que o valor DOM está visível para o ChromeDriver também
    element.send_keys(Keys.END)


def login(driver, email, password):
    """Realiza login no portal GREX"""
    print("🔐 Acessando página de login...")
    driver.get("https://portal.grex.com.br/login")

    try:
        # Aguardar formulário carregar
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#login-email-desktop")))

        print("📧 Preenchendo email...")
        email_field = driver.find_element(By.CSS_SELECTOR, "#login-email-desktop")
        _preencher_campo_angular(driver, email_field, email)

        print("🔑 Preenchendo senha...")
        password_field = driver.find_element(By.CSS_SELECTOR, "#login-password-desktop")
        _preencher_campo_angular(driver, password_field, password)

        # Verificar que o Angular enxerga os valores
        vals = driver.execute_script("""
            return [
                document.querySelector('#login-email-desktop') ?
                    document.querySelector('#login-email-desktop').value : 'N/A',
                document.querySelector('#login-password-desktop') ?
                    document.querySelector('#login-password-desktop').value : 'N/A'
            ];
        """)
        print(f"   Valores no DOM: email={repr(vals[0][:5]+'***' if vals[0] else '')}, pwd={repr('***' if vals[1] else '')}")

        # Dar tempo para Angular processar os bindings
        time.sleep(1)

        print("🖱️  Enviando login...")
        # Tentar Enter no campo senha (mais confiável em Angular Material)
        password_field.send_keys(Keys.RETURN)
        print("   Submit via Keys.RETURN na senha")

        # Aguardar redirecionamento (25s)
        wait2 = WebDriverWait(driver, 25)
        wait2.until(lambda d: "login" not in d.current_url)
        print("✅ Login realizado com sucesso!")

    except Exception as e:
        driver.save_screenshot("/app/data/login_debug.png")
        print(f"❌ Erro ao fazer login: {e}")
        print(f"   URL atual: {driver.current_url}")
        # Mostrar mensagens de erro visíveis na página
        try:
            erros = driver.find_elements(By.CSS_SELECTOR,
                "[class*='error'], [class*='alert'], [class*='invalid'], [class*='danger'], [role='alert']")
            for el in erros[:5]:
                txt = el.text.strip()
                if txt:
                    print(f"   Msg da página: {txt}")
        except Exception:
            pass
        print("💡 Dica: Verifique se as credenciais estão corretas")
        raise


def navigate_to_participants(driver, url):
    """Navega para a URL de participantes especificada"""
    print(f"🔗 Navegando para: {url[:60]}...")
    driver.get(url)

    try:
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".list-page-header")))
        time.sleep(1)
        driver.save_screenshot("/tmp/grex_debug_page_loaded.png")
        print("✅ Página de participantes carregada!")
    except Exception as e:
        driver.save_screenshot("/tmp/grex_debug_page_error.png")
        print(f"❌ Erro ao navegar: {e}")
        raise


def click_export_button(driver):
    """Clica no botão de exportação"""
    print("📤 Clicando no botão de exportação...")

    try:
        # Aguardar Angular terminar de renderizar
        wait = WebDriverWait(driver, 15)
        time.sleep(2)

        seletores_export = [
            (By.CSS_SELECTOR, "div.list-page-header__actions__end > button"),
            (By.CSS_SELECTOR, "div.list-page-header__actions__end button"),
            (By.CSS_SELECTOR, ".list-page-header button"),
            (By.CSS_SELECTOR, "button.btn--icon"),
        ]

        export_button = None
        for seletor in seletores_export:
            elements = driver.find_elements(*seletor)
            if elements:
                export_button = elements[0]
                print(f"   Botão encontrado via: {seletor[1]}")
                break

        if not export_button:
            driver.save_screenshot("/tmp/grex_debug_no_button.png")
            raise Exception("Botão de exportação não encontrado")

        # Rolar até o elemento
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", export_button)
        time.sleep(0.5)

        driver.save_screenshot("/tmp/grex_debug_before_click.png")

        # Tentar JS click primeiro, ActionChains como fallback
        try:
            driver.execute_script("arguments[0].click();", export_button)
        except Exception:
            ActionChains(driver).move_to_element(export_button).click().perform()

        print("✅ Botão clicado! Modal abrindo...")
        time.sleep(1.5)

    except Exception as e:
        print(f"❌ Erro ao clicar no botão de exportação: {e}")
        raise


def select_export_type(driver):
    """Seleciona o tipo de exportação no modal (XLSX/Excel)"""
    print("📋 Selecionando tipo de exportação (XLSX/Excel)...")

    try:
        wait = WebDriverWait(driver, 20)

        # Aguardar o modal aparecer antes de qualquer coisa
        print("⏳ Aguardando modal abrir...")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-dialog-container")))
            print("✅ Modal detectado!")
        except Exception:
            print("⚠️ mat-dialog-container não detectado, tentando continuar...")

        # Aguardar radio buttons aparecerem dentro do modal
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "mat-radio-button")))
            time.sleep(0.5)
        except Exception:
            print("⚠️ Radio buttons não detectados via wait, tentando de qualquer forma...")
            time.sleep(3)

        print("🔍 Procurando radio buttons no modal...")
        radio_buttons = driver.find_elements(By.CSS_SELECTOR, "mat-radio-button")
        print(f"   Encontrados {len(radio_buttons)} radio buttons")

        selected = False

        # Tentar por input[value='xlsx'] primeiro
        for seletor in [
            (By.CSS_SELECTOR, "input[value='xlsx']"),
            (By.CSS_SELECTOR, "input[type='radio'][value='xlsx']"),
            (By.XPATH, "//input[@value='xlsx']"),
            (By.CSS_SELECTOR, "input[type='radio']"),
            (By.XPATH, "//input[@type='radio']"),
        ]:
            elements = driver.find_elements(*seletor)
            for elem in elements:
                try:
                    value = elem.get_attribute("value")
                    if value == "xlsx" or not selected:
                        driver.execute_script("arguments[0].click();", elem)
                        time.sleep(0.3)
                        if value == "xlsx":
                            print("✅ Input XLSX clicado!")
                            selected = True
                            break
                except Exception:
                    continue
            if selected:
                break

        # Tentar por texto nos mat-radio-button
        if not selected and radio_buttons:
            for idx, radio in enumerate(radio_buttons):
                try:
                    text = radio.text.upper()
                    print(f"   Radio {idx}: {text}")
                    if "XLSX" in text or "EXCEL" in text or "XLS" in text:
                        driver.execute_script("arguments[0].scrollIntoView(true);", radio)
                        time.sleep(0.3)
                        radio.click()
                        print("✅ XLSX/Excel selecionado por texto!")
                        selected = True
                        break
                except Exception:
                    continue

            # Fallback: segundo radio button
            if not selected and len(radio_buttons) > 1:
                try:
                    radio_buttons[1].click()
                    print("✅ Segundo radio button clicado (fallback)!")
                    selected = True
                except Exception as e:
                    print(f"❌ Fallback falhou: {e}")

        if not selected:
            raise Exception("Não foi possível selecionar XLSX/Excel")

        print("✅ XLSX selecionado com sucesso!")
        time.sleep(1)

    except Exception as e:
        print(f"❌ Erro ao selecionar tipo de exportação: {e}")
        raise


def confirm_export(driver):
    """Confirma a exportação clicando no botão primário"""
    print("✔️  Confirmando exportação...")

    try:
        time.sleep(1)  # Aguardar modal finalizar animação

        # Tirar screenshot para debug
        driver.save_screenshot("/tmp/grex_confirm_button_debug.png")

        # Procurar por qualquer botão
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        print(f"   Encontrados {len(buttons)} botões na página")

        for idx, btn in enumerate(buttons):
            try:
                text = btn.text
                cls = btn.get_attribute("class")
                print(f"   Botão {idx}: text='{text}' class='{cls}'")
            except:
                pass

        # Tentar seletores com timeout curto
        seletores = [
            (By.CSS_SELECTOR, "button.btn--primary"),
            (By.CSS_SELECTOR, "button.btn.btn--primary"),
            (By.XPATH, "//button[contains(@class, 'primary')]"),
            (By.CSS_SELECTOR, "mat-dialog-actions button"),
            (By.CSS_SELECTOR, "button"),  # Qualquer botão
        ]

        confirm_button = None
        wait = WebDriverWait(driver, 3)

        for seletor in seletores:
            try:
                confirm_button = wait.until(EC.element_to_be_clickable(seletor))
                print(f"✅ Botão encontrado com seletor: {seletor}")
                break
            except:
                continue

        if not confirm_button:
            raise Exception("Nenhum botão encontrado")

        confirm_button.click()
        print("✅ Exportação iniciada!")

        # Aguardar download
        time.sleep(1)

    except Exception as e:
        print(f"❌ Erro ao confirmar exportação: {e}")
        raise


def rename_downloaded_file(target_name="encontro.xlsx"):
    """Renomeia o arquivo baixado para o nome especificado e limpa antigos"""
    print(f"📁 Processando arquivo baixado → {target_name}...")

    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)

    reserved = {"encontro.xlsx", "encontro2.xlsx"}
    xlsx_files = list(data_folder.glob("*.xlsx"))

    if not xlsx_files:
        print("⚠️  Nenhum arquivo .xlsx encontrado na pasta de downloads")
        return None

    non_target_files = [f for f in xlsx_files if f.name not in reserved]

    if not non_target_files:
        target_path = data_folder / target_name
        if target_path.exists():
            print(f"✅ Arquivo já é {target_name}")
            return target_path
        print("⚠️  Nenhum arquivo novo para renomear")
        return None

    latest_file = max(non_target_files, key=lambda p: p.stat().st_mtime)
    target_path = data_folder / target_name

    if target_path.exists():
        try:
            target_path.unlink()
        except PermissionError:
            pass

    try:
        latest_file.rename(target_path)
        print(f"✅ Arquivo renomeado: {latest_file.name} → {target_name}")
    except Exception as e:
        print(f"⚠️  Erro ao renomear: {e}")
        return None

    # Limpar arquivos antigos (Subscriptions, etc)
    old_files = list(data_folder.glob("Subscriptions*.xlsx"))
    for old_file in old_files:
        try:
            old_file.unlink()
            print(f"   🗑️  Removido: {old_file.name}")
        except:
            pass

    print(f"✅ Arquivo salvo em: {target_path.absolute()}")
    return target_path


def fechar_modal(driver):
    """Tenta fechar qualquer modal aberto antes de um retry"""
    try:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
        time.sleep(1)
    except Exception:
        pass


def baixar_fonte(driver, url, target_name, max_retries=3):
    """Executa o fluxo de download para uma URL com até max_retries tentativas"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 [{target_name}] Tentativa {attempt}/{max_retries}...")
            navigate_to_participants(driver, url)
            click_export_button(driver)
            select_export_type(driver)
            confirm_export(driver)
            time.sleep(4)
            result = rename_downloaded_file(target_name)
            if result and result.exists():
                print(f"✅ [{target_name}] Download concluído!")
                return True
            raise Exception("Arquivo não encontrado após download")
        except Exception as e:
            print(f"⚠️ [{target_name}] Tentativa {attempt} falhou: {e}")
            if attempt < max_retries:
                fechar_modal(driver)
                time.sleep(3)
            else:
                print(f"❌ [{target_name}] Todas as tentativas falharam.")
                raise
    return False


def main():
    """Função principal"""
    print("=" * 60)
    print("🚀 INICIANDO AUTOMAÇÃO GREX [build: diag-v1]")
    print("=" * 60)

    email = os.getenv("GREX_EMAIL")
    password = os.getenv("GREX_PASSWORD")
    if not email or not password:
        raise ValueError("GREX_EMAIL e GREX_PASSWORD devem estar definidos nas variáveis de ambiente.")

    driver = None

    url1 = os.getenv("GREX_PARTICIPANTS_URL")
    url2 = os.getenv("GREX_PARTICIPANTS_URL_2", "").strip()

    if not url1:
        raise ValueError("Variável de ambiente GREX_PARTICIPANTS_URL não definida.")

    try:
        driver = setup_driver()
        login(driver, email, password)

        print("\n--- Fonte 1 ---")
        baixar_fonte(driver, url1, "encontro.xlsx")

        if url2:
            print("\n--- Fonte 2 ---")
            baixar_fonte(driver, url2, "encontro2.xlsx")

        print("\n" + "=" * 60)
        print("✨ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERRO DURANTE A AUTOMAÇÃO: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            time.sleep(2)
            driver.quit()
            print("🔚 Navegador fechado")
        # Exibir log do ChromeDriver para diagnóstico em caso de falha
        if os.path.exists(CHROMEDRIVER_LOG):
            try:
                with open(CHROMEDRIVER_LOG) as _f:
                    lines = _f.readlines()
                if lines:
                    print("=== ChromeDriver Log (últimas 40 linhas) ===")
                    print("".join(lines[-40:]))
            except Exception:
                pass


if __name__ == "__main__":
    main()
