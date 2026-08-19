@echo off
cd /d "%~dp0"

echo Verificando se o Selenium esta instalado...
python -c "import selenium" 2>nul
if errorlevel 1 (
    echo Instalando Selenium, aguarde...
    pip install selenium
)

echo.
echo Iniciando automacao do check-in...
echo (Esta janela precisa ficar aberta. Feche-a ou aperte Ctrl+C para encerrar.)
echo.
python "%~dp0grex_checkin.py"

pause
