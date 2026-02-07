@echo off
echo ===================================================
echo    COMPILADOR DEL SISTEMA DE VENTAS (PyInstaller)
echo ===================================================
echo.

:: 1. Verificación de Entorno
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no detectado. Por favor instale Python.
    pause
    exit /b
)

:: 2. Instalar herramientas de compilación
echo [INFO] Instalando PyInstaller...
python -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo [ERROR] Falló la instalación de PyInstaller.
    pause
    exit /b
)

:: 3. Limpiar compilaciones previas
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

:: 4. Compilar
echo.
echo [INFO] Iniciando Compilacion...
echo Esto puede tardar unos minutos.
echo.

:: Argumentos Clave:
:: --noconsole: Oculta la terminal (Quitar para depurar errores)
:: --hidden-import: Importa módulos que PyInstaller no detecta (ttkbootstrap, babel)
:: --add-data: Incluye carpetas y archivos (formato "origen;destino")
:: --icon: Icono del ejecutable (si existe)

python -m PyInstaller --noconsole ^
 --name "SistemaVentas" ^
 --hidden-import=ttkbootstrap ^
 --hidden-import=PIL ^
 --hidden-import=lxml ^
 --hidden-import=signxml ^
 --hidden-import=cryptography ^
 --hidden-import=babel.numbers ^
 --hidden-import=win32print ^
 --hidden-import=win32ui ^
 --hidden-import=win32api ^
 --hidden-import=win32con ^
 --hidden-import=pythoncom ^
 --hidden-import=pywintypes ^
 --hidden-import=pandas ^
 --hidden-import=openpyxl ^
 --collect-all qrcode ^
 --collect-all signxml ^
 --collect-all lxml ^
 --collect-all cryptography ^
 --collect-all win32print ^
 --collect-all win32ui ^
 --collect-all win32api ^
 --collect-all ttkbootstrap ^
 --clean ^
 --add-data "whatsapp_service;whatsapp_service" ^
 --add-data "SEE Electronica;SEE Electronica" ^
 --add-data "ubigeo.json;." ^
 --add-data "unidades_medida.json;." ^
 --add-data "group_order.json;." ^
 --add-data "product_order.json;." ^
 --add-data "codigo_qr.png;." ^
 --add-data "pos_config.json;." ^
 --icon=codigo_qr.png ^
 main.py

if %errorlevel% neq 0 (
    echo.
    echo.
    echo [ERROR] Ocurrió un error durante la compilación de SistemaVentas.
    pause
    exit /b
)

:: 5. Compilar Updater
echo.
echo [INFO] Compilando Updater...
python -m PyInstaller --noconsole --onefile --name=Updater --distpath dist/SistemaVentas updater.py

if %errorlevel% neq 0 (
    echo.
    echo.
    echo [ERROR] Ocurrió un error durante la compilación de Updater.
    pause
    exit /b
)

:: 6. Copiar version.json
echo.
echo [INFO] Copiando version.json...
copy version.json "dist\SistemaVentas\" >nul

echo.
echo ===================================================
echo    COMPILACION EXITOSA
echo ===================================================
echo El ejecutable se encuentra en la carpeta "dist/SistemaVentas"
echo.
echo.
pause
