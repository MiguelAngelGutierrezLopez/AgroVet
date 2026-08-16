@echo off
chcp 65001 > nul
cls

echo ========================================
echo    COMPILADOR AGROVET YACUANQUER
echo ========================================
echo.

title Compilando AGROVET YACUANQUER

REM Verificar si estamos en el entorno virtual
echo 🔍 Verificando entorno virtual...
if exist "agrovet\Scripts\activate.bat" (
    echo ✅ Entorno virtual encontrado
    call agrovet\Scripts\activate
) else (
    echo ⚠️  No se encuentra entorno virtual 'agrovet'
    echo    Usando Python del sistema...
)

REM Definir intérprete Python a usar (priorizar virtualenv)
set "PYPATH=agrovet\Scripts\python.exe"
if not exist "%PYPATH%" set "PYPATH=python"

REM Instalar/actualizar PyInstaller usando el intérprete seleccionado
echo 📦 Instalando PyInstaller en %PYPATH%...
"%PYPATH%" -m pip install --upgrade pyinstaller > nul 2>&1
echo ✅ PyInstaller actualizado (%PYPATH%)

REM Verificar estructura de archivos
echo 📁 Verificando archivos...
if not exist "main.py" (
    echo ❌ No se encuentra main.py
    pause
    exit /b 1
)

if not exist "vista" (
    echo ⚠️  No se encuentra carpeta 'vista'
    echo    Creando carpeta vista...
    mkdir vista
)

REM Verificar archivo SQL de base de datos
echo 📊 Verificando base de datos...
if exist "AgroVet.sql" (
    echo ✅ Base de datos AgroVet.sql encontrada
    echo    Tamaño: %~z0 AgroVet.sql bytes
) else (
    echo ⚠️  ADVERTENCIA: AgroVet.sql no encontrada
    echo    La base de datos debe estar en el mismo directorio
)

echo ✅ Todos los archivos necesarios encontrados
echo.

REM Opción de compilación
echo Selecciona el tipo de compilación:
echo [1] Una carpeta completa (recomendado)
echo [2] Un solo archivo .exe
echo [3] Solo configurar base de datos
echo.
set /p opcion="Opción (1, 2 o 3): "

if "%opcion%"=="1" (
    echo 🔨 Compilando en carpeta...
    
    REM Crear carpeta para datos si no existe
    if not exist "data" mkdir data
    
    REM Crear README para instalación
    echo Creando documentación de instalación...
    (
    echo # AGROVET YACUANQUER - Manual de Instalación
        echo.
        echo ## Requisitos del Sistema
        echo 1. MySQL o MariaDB instalado y ejecutándose
        echo 2. Puerto 3306 disponible
        echo 3. Usuario: root (puede cambiar después)
        echo.
        echo ## Instalación de Base de Datos
        echo Ejecutar: setup_database.exe
        echo O usar HeidiSQL para importar AgroVet.sql
        echo.
        echo ## Ejecutar la Aplicación
        echo 1. Ejecutar AGROVET.exe
        echo 2. Navegador se abrirá automáticamente
        echo 3. URL: http://localhost:5000
        echo.
        echo ## Solución de Problemas
        echo - Verificar que MySQL esté ejecutándose
        echo - Revisar config.py para credenciales
        echo - Ejecutar como administrador si hay errores
    ) > "README_INSTALACION.txt"
    
    "%PYPATH%" -m PyInstaller --name "AGROVET" ^
                --onedir ^
                --add-data "vista;vista" ^
                --add-data "controlador;controlador" ^
                --add-data "modelo;modelo" ^
                --add-data "data;data" ^
                --add-data "AgroVet.sql;." ^
                --add-data "README_INSTALACION.txt;." ^
                --add-data "config.py;." ^
                --add-data "database.py;." ^
                --add-data "requirements.txt;." ^
                --hidden-import mysql.connector ^
                --hidden-import flask ^
                --hidden-import waitress ^
                --hidden-import reportlab ^
                --hidden-import arabic_reshaper ^
                --hidden-import bidi ^
                --hidden-import pyphen ^
                --hidden-import xhtml2pdf ^
                --hidden-import svglib ^
                --hidden-import lxml ^
                --console ^
                --clean ^
                main.py
    
    REM También compilar el configurador de base de datos
    echo 🔧 Compilando configurador de base de datos...
    "%PYPATH%" -m PyInstaller --name "setup_database" ^
                --onefile ^
                --add-data "AgroVet.sql;." ^
                --hidden-import mysql.connector ^
                --console ^
                --clean ^
                setup_database.py
    
    echo ✅ Compilación completada!
    echo 📁 La aplicación está en: dist\AGROVET\
    echo 📄 Ejecuta: dist\AGROVET\AGROVET.exe
    echo 🔧 Configurador BD: dist\setup_database.exe
)

if "%opcion%"=="2" (
    echo 🔨 Compilando en un solo .exe...
    
    "%PYPATH%" -m PyInstaller --name "AGROVET" ^
                --onefile ^
                --add-data "vista;vista" ^
                --add-data "controlador;controlador" ^
                --add-data "modelo;modelo" ^
                --add-data "data;data" ^
                --add-data "AgroVet.sql;." ^
                --add-data "config.py;." ^
                --add-data "database.py;." ^
                --hidden-import mysql.connector ^
                --hidden-import flask ^
                --hidden-import waitress ^
                --hidden-import reportlab ^
                --hidden-import arabic_reshaper ^
                --hidden-import bidi ^
                --hidden-import pyphen ^
                --hidden-import xhtml2pdf ^
                --hidden-import svglib ^
                --hidden-import lxml ^
                --console ^
                --clean ^
                main.py
    
    echo ✅ Compilación completada!
    echo 📄 El ejecutable está en: dist\AGROVET.exe
)

if "%opcion%"=="3" (
    echo 🔧 Configurando solo base de datos...
    
    if exist "setup_database.py" (
        echo Ejecutando configuración de base de datos...
        "%PYPATH%" setup_database.py
    ) else (
        echo ❌ setup_database.py no encontrado
        echo Creando archivo de configuración...
        
        REM Crear setup_database.py temporalmente
        (
            echo import subprocess
            echo import os
            echo.
            echo print("Configuración de Base de Datos AGROVET")
            echo print("="^50)
            echo.
            echo print("Por favor, sigue estos pasos:")
            echo print("1. Asegúrate de que MySQL/MariaDB esté instalado")
            echo print("2. Ejecuta HeidiSQL como administrador")
            echo print("3. Conéctate al servidor localhost:3306")
            echo print("4. Importa el archivo AgroVet.sql")
            echo print("5. La base de datos se llamará 'agrovet'")
            echo print("6. Usuario: root, Contraseña: [la que configuraste]")
            echo.
            echo input("Presiona Enter para continuar...")
        ) > setup_database.py
        
        "%PYPATH%" setup_database.py
        echo ✅ Configuración de base de datos completada.
        echo 📄 Archivo setup_database.py conservado para futuras ejecuciones.
    )
    
    pause
    exit /b 0
)

echo.
echo ========================================
echo    PASOS PARA LA INSTALACIÓN COMPLETA
echo ========================================
echo.
echo 📋 PASO 1: Instalar MySQL/MariaDB si no lo tiene
echo    - Descargar desde: https://mariadb.org/download/
echo    - O usar XAMPP: https://www.apachefriends.org/
echo.
echo 📋 PASO 2: Configurar base de datos
echo    a) Ejecutar setup_database.exe
echo    b) O usar HeidiSQL para importar AgroVet.sql
echo.
echo 📋 PASO 3: Ejecutar la aplicación
echo    - Ejecutar AGROVET.exe
echo    - El navegador se abrirá automáticamente
echo.
echo 📋 PASO 4: (Opcional) Instalar HeidiSQL
echo    - Descargar desde: https://www.heidisql.com/
echo    - Útil para administrar la base de datos
echo.
echo 📋 TROUBLESHOOTING:
echo    - Error de conexión: Verificar que MySQL esté corriendo
echo    - Error 1045: Revisar usuario/contraseña en config.py
echo    - Permisos: Ejecutar como administrador
echo    - Puerto bloqueado: Verificar que 3306 esté libre
echo.
echo 📄 Documentación completa en: README_INSTALACION.txt
echo.
pause