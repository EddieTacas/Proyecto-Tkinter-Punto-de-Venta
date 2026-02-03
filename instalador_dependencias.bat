@echo off
echo ===================================================
echo    INSTALADOR DE DEPENDENCIAS - SISTEMA DE VENTAS
echo ===================================================
echo.
echo Este script verificara e instalara los requisitos necesarios.
echo.

:: 1. Verificar Python
echo [1/3] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ALERTA] Python no se encuentra en el PATH o no esta instalado.
    echo.
    echo Por favor, descargue e instale Python desde:
    echo https://www.python.org/downloads/
    echo.
    echo Asegurese de marcar "Add Python to PATH" durante la instalacion.
    echo.
    set /p open_web="¿Desea abrir la pagina de descarga ahora? (S/N): "
    if /i "%open_web%"=="S" start https://www.python.org/downloads/
    pause
    exit /b
) else (
    echo    Python detectado correctamente.
)

:: 2. Instalar Librerías Python
echo.
echo [2/3] Instalando librerias del sistema (requirements.txt)...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Hubo un problema instalando las librerias. Verifique su conexion a internet.
    pause
    exit /b
)
echo    Librerias instaladas correctamente.

:: 3. Verificar Node.js (Para WhatsApp)
echo.
echo [3/3] Verificando Node.js (Servicio WhatsApp)...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ALERTA] Node.js no esta instalado. Es necesario para la conexion con WhatsApp.
    echo.
    echo Por favor, descargue e instale Node.js (LTS) desde:
    echo https://nodejs.org/
    echo.
    set /p open_web_node="¿Desea abrir la pagina de descarga ahora? (S/N): "
    if /i "%open_web_node%"=="S" start https://nodejs.org/
) else (
    echo    Node.js detectado. Instalando dependencias del servicio WhatsApp...
    if exist "whatsapp_service" (
        cd whatsapp_service
        call npm install
        cd ..
        echo    Dependencias de WhatsApp instaladas.
    ) else (
        echo [ADVERTENCIA] No se encontro la carpeta "whatsapp_service".
    )
)

echo.
echo ===================================================
echo    INSTALACION COMPLETADA
echo ===================================================
echo Ya puede ejecutar el sistema.
echo.
pause
