@echo off
echo Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error al instalar las dependencias.
    pause
    exit /b %errorlevel%
)
echo Dependencias instaladas correctamente.
pause
