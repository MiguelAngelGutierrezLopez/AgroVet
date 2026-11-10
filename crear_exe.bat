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

    REM Compilar en una carpeta temporal para evitar bloqueos de salidas anteriores
    if exist "dist\_build" rmdir /s /q "dist\_build"
    if exist "build\_build" rmdir /s /q "build\_build"
    if exist "build\_build_setup" rmdir /s /q "build\_build_setup"
    if exist "%TEMP%\AGROVET_1.0" rmdir /s /q "%TEMP%\AGROVET_1.0"
    if exist "AGROVET.spec" del /q "AGROVET.spec"
    if exist "setup_database.spec" del /q "setup_database.spec"
    if exist "dist\AGROVET_1.0" rmdir /s /q "dist\AGROVET_1.0"
    if exist "dist\AGROVET_1.0.zip" del /q "dist\AGROVET_1.0.zip"
    if exist "dist\AGROVET_1.0" (
        echo ❌ No se pudo limpiar dist\AGROVET_1.0
        echo    Cierra cualquier ventana o proceso que use esa carpeta e intenta de nuevo.
        pause
        exit /b 1
    )
    
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
        echo ## Base de Datos
        echo MySQL/MariaDB debe estar iniciado antes de abrir AgroVet.
        echo Al iniciar AGROVET.exe se aplican automaticamente las migraciones pendientes.
        echo Para una instalacion nueva, ejecuta setup_database.exe primero.
        echo.
        echo ## Ejecutar la Aplicación
        echo 1. Ejecutar AGROVET.exe
        echo 2. Navegador se abrirá automáticamente
        echo 3. URL: http://localhost:5000
        echo.
        echo ## Solución de Problemas
        echo - Verificar que el servicio MySQL/MariaDB esté ejecutándose
        echo - Verificar las credenciales configuradas para la base de datos
        echo - Ejecutar como administrador si hay errores
    ) > "README_INSTALACION.txt"
    
    "%PYPATH%" -m PyInstaller --name "AGROVET" ^
                --onedir ^
                --add-data "vista;vista" ^
                --add-data "data;data" ^
                --add-data "imagenes;imagenes" ^
                --add-data "static;static" ^
                --add-data "templates;templates" ^
                --add-data "migrations;migrations" ^
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
                --noconfirm ^
                --distpath "dist\_build" ^
                --workpath "build\_build" ^
                main.py

    if errorlevel 1 (
        echo ❌ Error compilando AGROVET
        pause
        exit /b 1
    )
    
    REM También compilar el configurador de base de datos
    echo 🔧 Compilando configurador de base de datos...
    "%PYPATH%" -m PyInstaller --name "setup_database" ^
                --onefile ^
                --add-data "AgroVet.sql;." ^
                --add-data "migrations;migrations" ^
                --hidden-import mysql.connector ^
                --console ^
                --clean ^
                --noconfirm ^
                --distpath "dist\_build" ^
                --workpath "build\_build_setup" ^
                setup_database.py

    if errorlevel 1 (
        echo ❌ Error compilando setup_database
        pause
        exit /b 1
    )

    if not exist "dist\_build\AGROVET\AGROVET.exe" (
        echo ❌ No se genero AGROVET.exe
        pause
        exit /b 1
    )
    if not exist "dist\_build\setup_database.exe" (
        echo ❌ No se genero setup_database.exe
        pause
        exit /b 1
    )

    REM Preparar una carpeta independiente para entregar al cliente
    echo 📦 Preparando paquete de entrega...
    mkdir "dist\AGROVET_1.0" > nul 2>&1
    xcopy "dist\_build\AGROVET\*" "dist\AGROVET_1.0\" /E /I /H /Y > nul
    copy /Y "dist\_build\setup_database.exe" "dist\AGROVET_1.0\setup_database.exe" > nul
    copy /Y "README_INSTALACION.txt" "dist\AGROVET_1.0\README_INSTALACION.txt" > nul

    REM Comprimir desde TEMP para evitar bloqueos de OneDrive o del antivirus en dist
    xcopy "dist\AGROVET_1.0\*" "%TEMP%\AGROVET_1.0\" /E /I /H /Y > nul
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path (Join-Path $env:TEMP 'AGROVET_1.0') -DestinationPath (Join-Path '%CD%' 'dist\AGROVET_1.0.zip') -CompressionLevel Optimal -Force"
    if errorlevel 1 (
        echo ❌ Error creando dist\AGROVET_1.0.zip
        rmdir /s /q "%TEMP%\AGROVET_1.0"
        pause
        exit /b 1
    )

    REM Eliminar las carpetas temporales para evitar entregar duplicados
    rmdir /s /q "%TEMP%\AGROVET_1.0"
    rmdir /s /q "dist\_build"
    rmdir /s /q "build\_build"
    rmdir /s /q "build\_build_setup"
    
    echo ✅ Compilación completada!
    echo 📁 Carpeta de entrega: dist\AGROVET_1.0\
    echo 📦 ZIP de entrega: dist\AGROVET_1.0.zip
    echo 📄 Ejecuta: dist\AGROVET_1.0\AGROVET.exe
    exit /b 0
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
                --add-data "migrations;migrations" ^
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