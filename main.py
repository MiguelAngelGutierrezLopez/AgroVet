import datetime
import sys
import os
import logging
import traceback
import webbrowser
from threading import Timer
from flask import Flask, jsonify, render_template, send_from_directory, request, send_file
import codecs

# ======================
# CONFIGURACIÓN DE LOGGING - IGNORAR UNICODE ERRORS
# ======================

class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            message = self.format(record)
            stream = self.stream
            if isinstance(message, str):
                message = message.encode('utf-8', errors='replace').decode('utf-8')
            stream.write(message + self.terminator)
            self.flush()
        except Exception:
            pass

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[SafeStreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# Crear aplicación Flask
app = Flask(__name__, 
            static_folder='static' if os.path.exists('static') else None,
            template_folder='templates' if os.path.exists('templates') else None)
app.secret_key = 'agrovet_secret_key_2024'
app.logger.handlers = logger.handlers
app.logger.setLevel(logging.INFO)

# ======================
# IMPORTAR BLUEPRINTS
# ======================

try:
    from controlador.historial_venta_controller import historial_venta_bp
    logger.info("Blueprint de historial de ventas importado desde controlador")
except ImportError as e:
    logger.error(f"No se pudo importar historial_venta_controller: {e}")
    historial_venta_bp = None

# ======================
# REGISTRO DE CONTROLADORES
# ======================

controladores_a_registrar = []

if historial_venta_bp:
    controladores_a_registrar.append(('historial_venta', historial_venta_bp, '/api'))
    logger.info("Blueprint de historial de ventas listo para registrar")
else:
    logger.error("Blueprint de historial de ventas NO disponible")

try:
    from controlador.ventas_controller import ventas_bp
    controladores_a_registrar.append(('ventas', ventas_bp, ''))
    logger.info("Controlador de ventas importado")
except ImportError as e:
    logger.warning(f"Controlador de ventas no disponible")

try:
    from controlador.productos_controller import productos_bp
    controladores_a_registrar.append(('productos', productos_bp, ''))
    logger.info("Controlador de productos importado")
except ImportError as e:
    logger.warning(f"Controlador de productos no disponible")

try:
    from controlador.cliente_proveedor_controller import cliente_proveedor_bp
    app.register_blueprint(cliente_proveedor_bp, url_prefix='/clientes-proveedores')
    logger.info("Blueprint de clientes/proveedores registrado con prefijo /clientes-proveedores")
    
    from controlador.cliente_proveedor_controller import cliente_proveedor_bp as cliente_proveedor_bp_directo
    app.register_blueprint(cliente_proveedor_bp_directo, name='cliente_proveedor_directo')
    logger.info("Blueprint de clientes/proveedores registrado sin prefijo")
except Exception as e:
    logger.error(f"Error registrando clientes/proveedores: {e}")

try:
    from controlador.reporte_caja_controller import reporte_caja_bp
    controladores_a_registrar.append(('reporte_caja', reporte_caja_bp, ''))
    logger.info("Controlador de reporte caja importado")
except ImportError as e:
    logger.warning(f"Controlador de reporte caja no disponible")

try:
    from controlador.ventas_pdf_controller import ventas_pdf_bp
    controladores_a_registrar.append(('ventas_pdf', ventas_pdf_bp, ''))
    logger.info("Controlador de PDF de ventas importado")
except ImportError as e:
    logger.warning(f"Controlador de PDF de ventas no disponible")

try:
    from controlador.inventario_controller import inventario_bp
    controladores_a_registrar.append(('inventario', inventario_bp, ''))
    logger.info("Controlador de inventario importado exitosamente")
except ImportError as e:
    logger.warning(f"Controlador de inventario no disponible: {e}")

try:
    from controlador.login_controller import login_bp
    controladores_a_registrar.append(('login', login_bp, ''))
    logger.info("Controlador de login importado")
except ImportError as e:
    logger.warning(f"Controlador de login no disponible: {e}")

for nombre, bp, url_prefix in controladores_a_registrar:
    try:
        if url_prefix:
            app.register_blueprint(bp, url_prefix=url_prefix)
            logger.info(f"Blueprint '{nombre}' registrado con prefijo '{url_prefix}'")
        else:
            app.register_blueprint(bp)
            logger.info(f"Blueprint '{nombre}' registrado sin prefijo")
    except Exception as e:
        logger.error(f"Error registrando blueprint '{nombre}': {e}")

if historial_venta_bp:
    try:
        app.register_blueprint(historial_venta_bp, name='historial_venta_directo')
        logger.info("Blueprint de historial de ventas registrado también sin prefijo")
    except Exception as e:
        logger.error(f"Error registrando blueprint sin prefijo: {e}")

# ======================
# RUTAS PRINCIPALES - VERSIÓN MEJORADA PARA .EXE
# ======================

def obtener_base_path():
    """Obtiene el directorio base correcto para el ejecutable"""
    if getattr(sys, 'frozen', False):
        # Estamos en un .exe
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
    else:
        # Estamos en desarrollo
        base_path = os.path.dirname(os.path.abspath(__file__))
    return base_path

def obtener_ruta_html(nombre_archivo, directorio_preferido='vista'):
    """Obtiene la ruta correcta del archivo HTML tanto en .exe como en desarrollo"""
    base_path = obtener_base_path()
    
    # Mapeo de archivos (nombre_archivo solicitado -> archivo real en vista/)
    mapeo_archivos = {
        'login.html': 'login.html',
        'inicio.html': 'inicio.html',
        'ventas.html': 'ventas.html',
        'productos.html': 'productos.html',
        'detalle_venta.html': 'detalle_venta.html',
        'historial_venta.html': 'historial_venta.html',
        'reporte_caja.html': 'reporte_caja.html',
        'clientes_proveedores.html': 'usuarios.html'
    }
    
    archivo_real = mapeo_archivos.get(nombre_archivo, nombre_archivo)
    
    # Rutas a probar en orden de prioridad
    rutas_a_probar = []
    
    # 1. Primero buscar en directorio preferido
    rutas_a_probar.append(os.path.join(base_path, directorio_preferido, archivo_real))
    
    # 2. Buscar en MEIPASS (para .exe)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        rutas_a_probar.append(os.path.join(sys._MEIPASS, directorio_preferido, archivo_real))
    
    # 3. Buscar en directorio actual
    rutas_a_probar.append(os.path.join(base_path, archivo_real))
    
    # 4. Buscar en vista/ (alternativa)
    if directorio_preferido != 'vista':
        rutas_a_probar.append(os.path.join(base_path, 'vista', archivo_real))
    
    # 5. Buscar directamente (último recurso)
    rutas_a_probar.append(os.path.join(base_path, nombre_archivo))
    
    logger.info(f"Buscando {nombre_archivo} -> {archivo_real}")
    
    for ruta in rutas_a_probar:
        if os.path.exists(ruta):
            logger.info(f"✓ Encontrado: {ruta}")
            return ruta
    
    # Si no se encuentra, crear archivo temporal
    logger.error(f"✗ NO SE ENCONTRÓ {nombre_archivo}")
    return None

def servir_html(nombre_archivo, directorio_preferido='vista'):
    """Sirve un archivo HTML con manejo robusto de rutas"""
    try:
        ruta = obtener_ruta_html(nombre_archivo, directorio_preferido)
        
        if ruta:
            # Leer y devolver el contenido
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            return contenido
        else:
            # Archivo no encontrado - crear página de error
            logger.error(f"Archivo {nombre_archivo} no encontrado en ninguna ubicación")
            base_path = obtener_base_path()
            
            # Listar archivos disponibles para diagnóstico
            archivos_disponibles = []
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.html'):
                        archivos_disponibles.append(os.path.relpath(os.path.join(root, file), base_path))
            
            # Crear página de error informativa
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Error - AGROVET</title>
                <style>
                    body {{ padding: 50px; text-align: center; background: #f5f5f5; font-family: Arial, sans-serif; }}
                    .container {{ max-width: 800px; margin: 0 auto; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #e74c3c; }}
                    .info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: left; margin: 20px 0; }}
                    .file-list {{ max-height: 200px; overflow-y: auto; text-align: left; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Error: Archivo {nombre_archivo} no encontrado</h1>
                    <p><strong>Directorio actual:</strong> {base_path}</p>
                    <div class="info">
                        <p><strong>Archivos HTML disponibles:</strong></p>
                        <div class="file-list">
                            {'<br>'.join(archivos_disponibles) if archivos_disponibles else 'No se encontraron archivos HTML'}
                        </div>
                    </div>
                    <a href="/">← Volver al inicio</a> | 
                    <a href="/api/status">Ver estado del sistema</a>
                </div>
            </body>
            </html>
            """
            return error_html, 404
            
    except Exception as e:
        logger.error(f"Error sirviendo {nombre_archivo}: {e}")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="padding: 50px; text-align: center;">
            <h1>Error cargando {nombre_archivo}</h1>
            <p>{str(e)}</p>
            <a href="/">← Reintentar</a>
        </body>
        </html>
        """, 500

@app.route('/')
def login():
    """Página de login"""
    logger.info("Solicitando página de login")
    return servir_html('login.html', 'vista')

@app.route('/venta')
def venta():
    """Página de ventas"""
    return servir_html('ventas.html', 'vista')

@app.route('/productos')
def productos():
    """Página de productos"""
    return servir_html('productos.html', 'vista')

@app.route('/inventario')
def inventario():
    """Página de inventario"""
    return servir_html('detalle_venta.html', 'vista')

@app.route('/detalle_venta')
def detalle_venta():
    """Redirigir detalle_venta a inventario para compatibilidad"""
    from flask import redirect
    return redirect('/inventario')

@app.route('/historial_venta')
def historial_venta():
    """Página de historial de ventas"""
    return servir_html('historial_venta.html', 'vista')

@app.route('/reporte_caja')
def reporte_caja():
    """Página de reporte de caja"""
    return servir_html('reporte_caja.html', 'vista')

@app.route('/usuarios')
def usuarios():
    """Página de gestión de usuarios (clientes/proveedores)"""
    return servir_html('clientes_proveedores.html', 'vista')

@app.route('/clientes')
def clientes():
    """Redirigir clientes a usuarios"""
    from flask import redirect
    return redirect('/usuarios')

@app.route('/inicio')
def inicio():
    """Página de inicio para admin"""
    return servir_html('inicio.html', 'vista')

@app.route('/prueba')
def prueba():
    """Página de prueba para auxiliar"""
    return servir_html('prueba.html', 'vista')

@app.route('/Auxiliar_cliente')
def auxiliar_cliente():
    """Página de gestión de clientes y proveedores"""
    return servir_html('Auxiliar_cliente.html', 'vista')
# ======================
# RUTAS DE ARCHIVOS ESTÁTICOS
# ======================

@app.route('/favicon.ico')
def favicon():
    """Servir favicon"""
    try:
        base_path = obtener_base_path()
        favicon_paths = [
            os.path.join(base_path, 'static', 'favicon.ico'),
            os.path.join(base_path, 'favicon.ico'),
            os.path.join(base_path, 'vista', 'favicon.ico')
        ]
        
        for path in favicon_paths:
            if os.path.exists(path):
                return send_file(path, mimetype='image/vnd.microsoft.icon')
        
        # Si no hay favicon, devolver 404 silencioso
        return '', 204
    except Exception as e:
        logger.error(f"Error con favicon: {e}")
        return '', 204

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Servir archivos estáticos con múltiples ubicaciones"""
    base_path = obtener_base_path()
    static_dirs = [
        os.path.join(base_path, 'static'),
        os.path.join(base_path, 'vista', 'static'),
        os.path.join(base_path, 'vista'),
        os.path.join(base_path, '')
    ]
    
    for static_dir in static_dirs:
        ruta_completa = os.path.join(static_dir, filename)
        if os.path.exists(ruta_completa):
            logger.info(f"Sirviendo estático: {ruta_completa}")
            return send_from_directory(os.path.dirname(ruta_completa), os.path.basename(filename))
    
    logger.warning(f"Archivo estático no encontrado: {filename}")
    return "Archivo no encontrado", 404

# ======================
# NUEVAS RUTAS PARA APOYAR VENTAS MANUALES
# ======================

@app.route('/api/productos/buscar', methods=['GET'])
def buscar_productos_para_venta():
    """Buscar productos por nombre para venta manual"""
    try:
        from database import Database
        db = Database()
        
        nombre = request.args.get('nombre', '')
        if not nombre or len(nombre) < 2:
            return jsonify({
                'success': True,
                'productos': [],
                'total': 0
            })
        
        sql = """
        SELECT id, nombre, categoria, precio_venta, cantidad 
        FROM productos 
        WHERE nombre LIKE %s AND cantidad > 0
        ORDER BY nombre 
        LIMIT 10
        """
        
        productos = db.fetch_all(sql, (f"%{nombre}%",))
        
        return jsonify({
            'success': True,
            'productos': productos,
            'total': len(productos)
        })
        
    except Exception as e:
        logger.error(f"Error buscando productos para venta: {e}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}",
            'productos': []
        }), 500

@app.route('/api/producto/<int:producto_id>', methods=['GET'])
def obtener_producto_por_id(producto_id):
    """Obtener información de un producto específico"""
    try:
        from database import Database
        db = Database()
        
        sql = """
        SELECT id, nombre, categoria, precio_venta, cantidad, presentacion
        FROM productos 
        WHERE id = %s
        """
        
        producto = db.fetch_one(sql, (producto_id,))
        
        if producto:
            return jsonify({
                'success': True,
                'producto': producto
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Producto no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error obteniendo producto: {e}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

# ======================
# RUTAS DE API DE DASHBOARD
# ======================

@app.route('/api/dashboard/estadisticas')
def dashboard_estadisticas():
    """Endpoint para obtener estadísticas del dashboard"""
    try:
        from database import Database
        db = Database()
        
        # Productos en inventario
        productos_result = db.fetch_one("SELECT COUNT(*) as total FROM productos")
        total_productos = productos_result['total'] if productos_result else 0
        
        # Ventas hoy
        ventas_hoy_result = db.fetch_one(
            "SELECT COUNT(*) as total FROM ventas WHERE DATE(fecha_dia) = CURDATE()"
        )
        ventas_hoy = ventas_hoy_result['total'] if ventas_hoy_result else 0
        
        # Clientes registrados
        clientes_result = db.fetch_one("SELECT COUNT(*) as total FROM cliente")
        total_clientes = clientes_result['total'] if clientes_result else 0
        
        # Stock bajo (menos de 10 unidades)
        stock_bajo_result = db.fetch_one(
            "SELECT COUNT(*) as total FROM productos WHERE cantidad < 10"
        )
        stock_bajo = stock_bajo_result['total'] if stock_bajo_result else 0
        
        # Actividad reciente (últimas 5 ventas)
        actividad_result = db.fetch_all("""
            SELECT v.id, v.numero_venta, v.nombre_cliente, v.total, 
                   CONCAT(DATE(v.fecha_dia), ' ', TIME(v.fecha_hora)) as fecha_completa
            FROM ventas v 
            ORDER BY v.id DESC 
            LIMIT 5
        """)
        
        actividades = []
        if actividad_result:
            for venta in actividad_result:
                actividades.append({
                    'id': venta['id'],
                    'numero_venta': venta['numero_venta'],
                    'cliente': venta['nombre_cliente'],
                    'total': float(venta['total']),
                    'fecha': venta['fecha_completa'].strftime('%d/%m/%Y %H:%M') if hasattr(venta['fecha_completa'], 'strftime') else str(venta['fecha_completa']),
                    'tipo': 'venta'
                })
        
        return jsonify({
            'success': True,
            'estadisticas': {
                'total_productos': total_productos,
                'ventas_hoy': ventas_hoy,
                'total_clientes': total_clientes,
                'stock_bajo': stock_bajo
            },
            'actividad_reciente': actividades
        })
        
    except Exception as e:
        logger.error(f"Error en dashboard_estadisticas: {e}")
        # Devolver datos por defecto para que la interfaz funcione
        return jsonify({
            'success': True,  # Cambiado a True para que la interfaz cargue
            'estadisticas': {
                'total_productos': 0,
                'ventas_hoy': 0,
                'total_clientes': 0,
                'stock_bajo': 0
            },
            'actividad_reciente': [
                {
                    'id': 1,
                    'numero_venta': 'SIN-DATA',
                    'cliente': 'Sistema',
                    'total': 0,
                    'fecha': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'tipo': 'sistema'
                }
            ]
        }), 200

# ======================
# RUTAS DE API DE DIAGNÓSTICO
# ======================

@app.route('/api/status')
def api_status():
    """Estado de la API con información detallada"""
    try:
        base_path = obtener_base_path()
        
        # Verificar archivos HTML críticos
        archivos_html = {
            'inicio.html': obtener_ruta_html('inicio.html'),
            'ventas.html': obtener_ruta_html('ventas.html'),
            'productos.html': obtener_ruta_html('productos.html'),
            'detalle_venta.html': obtener_ruta_html('detalle_venta.html'),
            'historial_venta.html': obtener_ruta_html('historial_venta.html'),
            'reporte_caja.html': obtener_ruta_html('reporte_caja.html'),
            'usuarios.html': obtener_ruta_html('clientes_proveedores.html')
        }
        
        archivos_encontrados = {k: v is not None for k, v in archivos_html.items()}
        
        status = {
            'status': 'online',
            'timestamp': datetime.datetime.now().isoformat(),
            'system': 'AGROVET YACUANQUER POS v1.0',
            'base_path': base_path,
            'es_ejecutable': getattr(sys, 'frozen', False),
            'meipass': sys._MEIPASS if hasattr(sys, '_MEIPASS') else None,
            'archivos_html': archivos_encontrados,
            'blueprints_registrados': list(app.blueprints.keys()),
            'rutas_disponibles': [rule.rule for rule in app.url_map.iter_rules() if not rule.rule.startswith('/static')]
        }
        
        return jsonify({'success': True, 'data': status})
        
    except Exception as e:
        logger.error(f"Error en api_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ======================
# MIDDLEWARE DE LOGGING
# ======================

@app.before_request
def log_peticion():
    """Log de peticiones HTTP"""
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return
    logger.info(f"-> {request.method} {request.path}")

@app.after_request
def log_respuesta(response):
    """Log de respuestas HTTP"""
    if request.path.startswith('/static') or request.path == '/favicon.ico':
        return response
    
    status_code = response.status_code
    if 200 <= status_code < 300:
        status_symbol = "[OK]"
    elif 400 <= status_code < 500:
        status_symbol = "[CLIENT ERROR]"
    elif 500 <= status_code < 600:
        status_symbol = "[SERVER ERROR]"
    else:
        status_symbol = "[INFO]"
    
    logger.info(f"<- {status_symbol} {response.status_code} {request.path}")
    return response

# ======================
# FUNCIÓN PARA ABRIR NAVEGADOR
# ======================

def abrir_navegador():
    """Abrir navegador automáticamente"""
    try:
        webbrowser.open_new('http://127.0.0.1:5000')
        logger.info("Navegador abierto automáticamente")
    except Exception as e:
        logger.warning(f"No se pudo abrir el navegador: {e}")
        print("\nPara acceder al sistema, visita: http://127.0.0.1:5000")

# ======================
# INICIO DEL SISTEMA
# ======================

if __name__ == '__main__':
    base_path = obtener_base_path()
    
    # Banner de inicio
    print("\n" + "=" * 60)
    print("    AGROVET YACUANQUER - SISTEMA DE GESTIÓN POS")
    print("=" * 60)
    print(f"   URL: http://127.0.0.1:5000")
    print(f"   Directorio: {base_path}")
    print(f"   Es .exe: {'Sí' if getattr(sys, 'frozen', False) else 'No'}")
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        print(f"   MEIPASS: {sys._MEIPASS}")
    print("=" * 60)
    
    # Verificar archivos críticos antes de iniciar
    print("\n   VERIFICANDO ARCHIVOS HTML:")
    
    archivos_a_verificar = [
        ('Login', 'login.html'),
        ('Inicio', 'inicio.html'),
        ('Ventas', 'ventas.html'),
        ('Productos', 'productos.html'),
        ('Inventario', 'detalle_venta.html'),
        ('Historial', 'historial_venta.html'),
        ('Reporte Caja', 'reporte_caja.html'),
        ('Usuarios', 'clientes_proveedores.html')
    ]
    
    todos_encontrados = True
    for nombre, archivo in archivos_a_verificar:
        ruta = obtener_ruta_html(archivo)
        if ruta:
            print(f"     {nombre}: ✓ ({os.path.basename(ruta)})")
        else:
            print(f"     {nombre}: ✗ NO ENCONTRADO")
            todos_encontrados = False
    
    if not todos_encontrados:
        print("\n   ⚠️  ADVERTENCIA: Algunos archivos no se encontraron")
        print("   Verifica que la carpeta 'vista' contenga todos los archivos HTML")
    
    print("\n   ENDPOINTS PRINCIPALES:")
    print("     / - Página de login")
    print("     /inicio - Dashboard admin")
    print("     /prueba - Ventas auxiliar")
    print("     /venta - Ventas")
    print("     /productos - Productos")
    print("     /inventario - Inventario")
    print("     /usuarios - Clientes/Proveedores (CON VENTAS MANUALES)")
    print("     /api/status - Diagnóstico del sistema")
    print("     /api/dashboard/estadisticas - Estadísticas del dashboard")
    print("     /api/productos/buscar - Buscar productos para venta manual")
    print("     /api/login - Endpoint de login")
    print("=" * 60)
    
    # Abrir navegador después de 2 segundos
    Timer(2, abrir_navegador).start()
    
    # Iniciar servidor
    print("\nIniciando servidor Flask...")
    print("   Presiona Ctrl+C para detener")
    print("=" * 60 + "\n")
    
    try:
        app.run(
            host='127.0.0.1', 
            port=5000, 
            debug=False, 
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n\nServidor detenido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\nError al iniciar el servidor: {e}")
        sys.exit(1)