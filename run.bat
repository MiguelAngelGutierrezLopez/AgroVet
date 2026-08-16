@echo off
chcp 65001 > nul
cls

echo ========================================
echo    AGROVET YACUANQUER - Sistema
echo ========================================
echo.

title Sistema Agrovet

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no instalado
    echo Instala Python 3.8+ desde python.org
    pause
    exit /b 1
)

REM Verificar/instalar dependencias
if exist "requirements.txt" (
    echo 📦 Instalando dependencias...
    pip install -r requirements.txt
) else (
    echo Creando requirements.txt...
    (
        echo Flask==2.3.3
        echo mysql-connector-python==8.1.0
        echo waitress==2.1.2
    ) > requirements.txt
    pip install -r requirements.txt
)

REM Crear carpeta logs si no existe
if not exist "data\logs" mkdir data\logs

REM Iniciar sistema
echo.
echo 🚀 Iniciando sistema...
echo 📍 Abriendo: http://127.0.0.1:5000
echo ⏳ Por favor espera...
echo.

python main.py

pause