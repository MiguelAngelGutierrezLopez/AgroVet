from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
import sys
import os
from database import db

# Agregar ruta para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modelo.inventario_model import model
    logger = logging.getLogger(__name__)
    logger.info("Modelo de inventario importado correctamente")
except Exception as e:
    print(f"Error importando modelo de inventario: {e}")
    import traceback
    traceback.print_exc()
    # Crear un modelo dummy para evitar errores
    class DummyModel:
        @staticmethod
        def obtener_productos_inventario(filtros=None):
            return {'success': False, 'error': 'Modelo no cargado', 'productos': []}
        @staticmethod
        def obtener_estadisticas_inventario():
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def obtener_movimientos_recientes(limite=10):
            return {'success': False, 'error': 'Modelo no cargado', 'movimientos': []}
        @staticmethod
        def obtener_productos_mas_vendidos(dias=30, limite=5):
            return {'success': False, 'error': 'Modelo no cargado', 'productos': []}
        @staticmethod
        def obtener_filtros_disponibles():
            return {'success': False, 'error': 'Modelo no cargado', 'categorias': [], 'proveedores': []}
        @staticmethod
        def ajustar_stock_producto(producto_id, cantidad, tipo, motivo='', observaciones='', usuario_id=1):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def obtener_detalle_producto(producto_id):
            return {'success': False, 'error': 'Modelo no cargado'}
    
    model = DummyModel()

# Crear blueprint
inventario_bp = Blueprint('inventario', __name__)

@inventario_bp.route('/api/inventario/productos', methods=['GET'])
def obtener_productos_inventario():
    """Obtener productos con filtros de inventario"""
    try:
        logger.info("Solicitando productos de inventario")
        
        # Obtener filtros de la consulta
        filtros = {}
        
        categoria = request.args.get('categoria')
        if categoria:
            filtros['categoria'] = categoria
        
        proveedor = request.args.get('proveedor')
        if proveedor:
            filtros['proveedor'] = proveedor
        
        estado_stock = request.args.get('estado_stock')
        if estado_stock:
            filtros['estado_stock'] = estado_stock
        
        busqueda = request.args.get('busqueda')
        if busqueda:
            filtros['busqueda'] = busqueda
        
        resultado = model.obtener_productos_inventario(filtros)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_productos_inventario: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'productos': [],
            'total': 0
        }), 500

@inventario_bp.route('/api/inventario/estadisticas', methods=['GET'])
def obtener_estadisticas_inventario():
    """Obtener estadísticas generales del inventario"""
    try:
        logger.info("Solicitando estadísticas de inventario")
        resultado = model.obtener_estadisticas_inventario()
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_inventario: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'estadisticas': {}
        }), 500

@inventario_bp.route('/api/inventario/movimientos/recientes', methods=['GET'])
def obtener_movimientos_recientes():
    """Obtener movimientos recientes de inventario"""
    try:
        limite = request.args.get('limite', default=10, type=int)
        logger.info(f"Solicitando {limite} movimientos recientes")
        
        resultado = model.obtener_movimientos_recientes(limite)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_movimientos_recientes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'movimientos': [],
            'total': 0
        }), 500

@inventario_bp.route('/api/inventario/productos/mas-vendidos', methods=['GET'])
def obtener_productos_mas_vendidos():
    """Obtener productos más vendidos"""
    try:
        dias = request.args.get('dias', default=30, type=int)
        limite = request.args.get('limite', default=5, type=int)
        
        logger.info(f"Solicitando {limite} productos más vendidos de los últimos {dias} días")
        
        resultado = model.obtener_productos_mas_vendidos(dias, limite)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_productos_mas_vendidos: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'productos': [],
            'periodo_dias': dias
        }), 500

@inventario_bp.route('/api/inventario/filtros', methods=['GET'])
def obtener_filtros_disponibles():
    """Obtener listas para filtros"""
    try:
        logger.info("Solicitando filtros disponibles")
        resultado = model.obtener_filtros_disponibles()
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_filtros_disponibles: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'categorias': [],
            'proveedores': []
        }), 500

@inventario_bp.route('/api/inventario/ajustar-stock', methods=['POST'])
def ajustar_stock():
    """Ajustar stock de un producto"""
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['producto_id', 'tipo', 'cantidad']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                }), 400
        
        producto_id = data['producto_id']
        tipo = data['tipo']
        cantidad = data['cantidad']
        motivo = data.get('motivo', '')
        observaciones = data.get('observaciones', '')
        usuario_id = data.get('usuario_id', 1)
        
        # Validar tipo
        tipos_validos = ['entrada', 'salida', 'ajuste']
        if tipo not in tipos_validos:
            return jsonify({
                'success': False,
                'error': f'Tipo inválido. Debe ser: {", ".join(tipos_validos)}'
            }), 400
        
        # Validar cantidad
        if cantidad <= 0:
            return jsonify({
                'success': False,
                'error': 'La cantidad debe ser mayor a 0'
            }), 400
        
        logger.info(f"Ajustando stock: Producto {producto_id}, Tipo: {tipo}, Cantidad: {cantidad}")
        
        resultado = model.ajustar_stock_producto(
            producto_id=producto_id,
            cantidad=cantidad,
            tipo=tipo,
            motivo=motivo,
            observaciones=observaciones,
            usuario_id=usuario_id
        )
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 400
            
    except Exception as e:
        logger.error(f"Error en ajustar_stock: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@inventario_bp.route('/api/inventario/producto/<int:producto_id>', methods=['GET'])
def obtener_detalle_producto(producto_id):
    """Obtener detalle completo de un producto"""
    try:
        logger.info(f"Obteniendo detalle para producto ID: {producto_id}")
        
        resultado = model.obtener_detalle_producto(producto_id)
        
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 404
            
    except Exception as e:
        logger.error(f"Error en obtener_detalle_producto: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@inventario_bp.route('/api/inventario/exportar/excel', methods=['GET'])
def exportar_inventario_excel():
    """Exportar inventario a Excel/CSV"""
    try:
        # Obtener parámetros de filtro
        categoria = request.args.get('categoria')
        estado_stock = request.args.get('estado_stock')
        busqueda = request.args.get('busqueda')
        
        logger.info(f"Exportando inventario a Excel con filtros: categoria={categoria}, estado_stock={estado_stock}")
        
        # Construir filtros
        filtros = {}
        if categoria:
            filtros['categoria'] = categoria
        if estado_stock:
            filtros['estado_stock'] = estado_stock
        if busqueda:
            filtros['busqueda'] = busqueda
        
        # Obtener datos filtrados
        resultado = model.obtener_productos_inventario(filtros)
        
        if not resultado.get('success') or not resultado.get('productos'):
            return jsonify({
                'success': False,
                'error': 'No hay datos para exportar'
            }), 404
        
        productos = resultado['productos']
        
        # Crear contenido CSV
        csv_lines = []
        
        # Encabezados
        headers = [
            "Código", "Producto", "Descripción", "Categoría", 
            "Presentación", "Stock Actual", "Estado Stock",
            "Precio Costo", "Precio Venta", "Margen %", 
            "Valor Total Costo", "Valor Total Venta",
            "Proveedor", "Teléfono Proveedor", "Ventas 30 días"
        ]
        csv_lines.append(";".join(headers))
        
        # Datos de cada producto
        for producto in productos:
            margen = producto.get('margen_porcentaje', 0)
            valor_total_costo = producto.get('valor_total', 0)
            valor_total_venta = producto.get('stock_actual', 0) * producto.get('precio_venta', 0)
            
            linea = [
                producto.get('codigo_formateado', ''),
                producto.get('nombre', ''),
                producto.get('descripcion', '')[:100],  # Limitar descripción
                producto.get('categoria', ''),
                producto.get('presentacion', ''),
                str(producto.get('stock_actual', 0)),
                producto.get('estado_label', ''),
                f"${producto.get('precio_costo', 0):,.0f}",
                f"${producto.get('precio_venta', 0):,.0f}",
                f"{margen:.1f}%",
                f"${valor_total_costo:,.0f}",
                f"${valor_total_venta:,.0f}",
                producto.get('nombre_proveedor', 'Sin proveedor'),
                producto.get('telefono_proveedor', ''),
                str(producto.get('ventas_30_dias', 0))
            ]
            
            # Escapar punto y coma dentro de celdas
            linea_escapada = [str(cell).replace(';', ',') for cell in linea]
            csv_lines.append(";".join(linea_escapada))
        
        csv_content = "\n".join(csv_lines)
        
        # Crear respuesta con archivo CSV
        from io import StringIO
        from flask import Response
        
        output = StringIO()
        output.write(csv_content)
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=inventario_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info(f"Exportación a Excel completada: {len(productos)} productos")
        return response
        
    except Exception as e:
        logger.error(f"Error exportando inventario a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@inventario_bp.route('/api/inventario/test', methods=['GET'])
def test_inventario():
    """Endpoint de prueba para verificar que el inventario funciona"""
    try:
        logger.info("Test endpoint de inventario llamado")
        
        return jsonify({
            'success': True,
            'message': 'Módulo de inventario funcionando correctamente',
            'endpoints': {
                'GET /api/inventario/productos': 'Obtener productos con filtros',
                'GET /api/inventario/estadisticas': 'Estadísticas generales',
                'GET /api/inventario/movimientos/recientes': 'Movimientos recientes',
                'GET /api/inventario/productos/mas-vendidos': 'Productos más vendidos',
                'GET /api/inventario/filtros': 'Filtros disponibles',
                'POST /api/inventario/ajustar-stock': 'Ajustar stock de producto',
                'GET /api/inventario/producto/{id}': 'Detalle de producto',
                'GET /api/inventario/exportar/excel': 'Exportar a Excel'
            },
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en test_inventario: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@inventario_bp.route('/api/inventario/periodo/rapido', methods=['GET'])
def obtener_periodo_rapido():
    """Obtener datos para períodos rápidos (similar al historial)"""
    try:
        periodo = request.args.get('periodo', 'mes')
        
        hoy = datetime.now()
        
        if periodo == 'hoy':
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        elif periodo == 'semana':
            fecha_inicio = (hoy - timedelta(days=hoy.weekday())).date()
            fecha_fin = hoy.date()
        elif periodo == 'mes':
            fecha_inicio = hoy.replace(day=1).date()
            fecha_fin = hoy.date()
        elif periodo == 'anio':
            fecha_inicio = hoy.replace(month=1, day=1).date()
            fecha_fin = hoy.date()
        else:
            fecha_inicio = hoy.replace(day=1).date()
            fecha_fin = hoy.date()
        
        logger.info(f"Período rápido inventario: {periodo} ({fecha_inicio} - {fecha_fin})")
        
        # Obtener estadísticas
        resultado_estadisticas = model.obtener_estadisticas_inventario()
        
        # Obtener productos (todos para el período)
        resultado_productos = model.obtener_productos_inventario()
        
        # Obtener productos más vendidos del período
        resultado_mas_vendidos = model.obtener_productos_mas_vendidos(dias=30)
        
        # Asegurarse de que los datos sean serializables
        response_data = {
            'success': True,
            'periodo': periodo,
            'fecha_inicio': str(fecha_inicio),
            'fecha_fin': str(fecha_fin),
            'estadisticas': resultado_estadisticas.get('estadisticas', {}) if resultado_estadisticas.get('success') else {},
            'productos': resultado_productos.get('productos', []) if resultado_productos.get('success') else [],
            'productos_mas_vendidos': resultado_mas_vendidos.get('productos', []) if resultado_mas_vendidos.get('success') else [],
            'total_productos': resultado_productos.get('total', 0) if resultado_productos.get('success') else 0
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error en obtener_periodo_rapido: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'estadisticas': {},
            'productos': [],
            'productos_mas_vendidos': [],
            'total_productos': 0
        }), 500
    

@inventario_bp.route('/api/inventario/meses-disponibles', methods=['GET'])
def obtener_meses_disponibles():
    """Obtener meses y años con datos disponibles"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Obtener años disponibles
        cursor.execute("""
            SELECT DISTINCT YEAR(fecha_venta) as anio
            FROM detalle_venta 
            WHERE fecha_venta IS NOT NULL
            ORDER BY anio DESC
        """)
        años_disponibles = [row['anio'] for row in cursor.fetchall()]
        
        # Si no hay años, usar solo el año actual
        hoy = datetime.now()
        if not años_disponibles:
            años_disponibles = [hoy.year]
        
        # Para cada año, obtener meses disponibles
        meses_por_año = {}
        for año in años_disponibles:
            cursor.execute("""
                SELECT DISTINCT MONTH(fecha_venta) as mes
                FROM detalle_venta 
                WHERE YEAR(fecha_venta) = %s
                ORDER BY mes DESC
            """, (año,))
            meses = [row['mes'] for row in cursor.fetchall()]
            meses_por_año[año] = meses
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'años_disponibles': años_disponibles,
            'meses_por_año': meses_por_año,
            'hoy': {
                'mes': hoy.month,
                'anio': hoy.year
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo meses disponibles: {e}")
        hoy = datetime.now()
        return jsonify({
            'success': False,
            'error': str(e),
            'años_disponibles': [hoy.year],
            'meses_por_año': {hoy.year: [hoy.month] if hoy.month > 1 else []}
        }), 500
    
    
@inventario_bp.route('/api/inventario/exportar/ventas-mensual', methods=['GET'])
def exportar_ventas_mensual():
    """Exportar ventas mensuales a Excel/CSV"""
    try:
        # Obtener mes y año
        mes = request.args.get('mes')
        anio = request.args.get('anio')
        
        hoy = datetime.now()
        
        # Si no se especifica, usar el mes actual
        if not mes or not anio:
            mes = hoy.month
            anio = hoy.year
        else:
            mes = int(mes)
            anio = int(anio)
        
        # Validar que el mes/año no sea futuro
        if anio > hoy.year or (anio == hoy.year and mes > hoy.month):
            return jsonify({
                'success': False,
                'error': f'No se pueden obtener datos de meses futuros. Fecha actual: {hoy.strftime("%B %Y")}'
            }), 400
        
        logger.info(f"Exportando ventas mensuales: Mes={mes}, Año={anio}")
        
        # Obtener datos de ventas mensuales usando el modelo
        resultado = model.obtener_ventas_mensuales(mes, anio)
        
        if not resultado['success']:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Error al obtener datos de ventas')
            }), 400
        
        resultados = resultado['ventas_mensuales']
        
        if not resultados:
            return jsonify({
                'success': False,
                'error': f'No hay datos de ventas para {datetime(anio, mes, 1).strftime("%B %Y")}'
            }), 404
        
        # Crear contenido CSV
        csv_lines = []
        
        # Encabezados (en el orden solicitado)
        headers = [
            "Tipo de producto",
            "Nombre del producto", 
            "Unidad de presentación", 
            "Cantidad de unidades vendidas", 
            "Valor de las ventas"
        ]
        csv_lines.append(";".join(headers))
        
        # Datos de cada producto
        total_unidades = 0
        total_valor = 0
        
        for item in resultados:
            cantidad = item.get('cantidad_unidades_vendidas', 0)
            valor = float(item.get('valor_ventas', 0))
            
            total_unidades += cantidad
            total_valor += valor
            
            linea = [
                item.get('tipo_producto', ''),
                item.get('nombre_producto', ''),
                item.get('unidad_presentacion', ''),
                str(cantidad),
                f"${valor:,.0f}"
            ]
            
            # Escapar punto y coma dentro de celdas
            linea_escapada = [str(cell).replace(';', ',') for cell in linea]
            csv_lines.append(";".join(linea_escapada))
        
        # Agregar fila de totales
        csv_lines.append("")  # Línea vacía
        csv_lines.append(f"Totales;;;;{total_unidades};${total_valor:,.0f}")
        
        # Agregar información del período
        csv_lines.append("")  # Línea vacía
        nombre_mes = datetime(anio, mes, 1).strftime('%B')
        csv_lines.append(f"Período: {nombre_mes} {anio}")
        csv_lines.append(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        csv_content = "\n".join(csv_lines)
        
        # Crear respuesta con archivo CSV
        from io import StringIO
        from flask import Response
        
        output = StringIO()
        output.write(csv_content)
        
        # Nombre del archivo con mes y año
        nombre_archivo = f"ventas_mensuales_{nombre_mes.lower()}_{anio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info(f"Exportación de ventas mensuales completada: {len(resultados)} productos")
        return response
        
    except ValueError as e:
        logger.error(f"Error de parámetros en exportar_ventas_mensual: {e}")
        return jsonify({
            'success': False,
            'error': 'Parámetros inválidos para mes o año'
        }), 400
    except Exception as e:
        logger.error(f"Error exportando ventas mensuales a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500