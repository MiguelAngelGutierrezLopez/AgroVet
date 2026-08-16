import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db
from datetime import datetime, timedelta
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

def convertir_para_json(data):
    """Función auxiliar para convertir tipos de datos no serializables a JSON"""
    if isinstance(data, dict):
        return {key: convertir_para_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convertir_para_json(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    elif isinstance(data, timedelta):
        return data.days
    elif isinstance(data, datetime):
        return data.isoformat()
    elif isinstance(data, bytes):
        return data.decode('utf-8')
    elif hasattr(data, '__dict__'):
        return convertir_para_json(data.__dict__)
    else:
        return data

class InventarioModel:
    
    @staticmethod
    def obtener_productos_inventario(filtros=None):
        """Obtener productos con información de inventario"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    p.id,
                    p.nombre,
                    p.descripcion,
                    p.categoria,
                    p.cantidad as stock_actual,
                    p.presentacion,
                    p.proveedor,
                    pr.nombre_proveedor,
                    pr.telefono as telefono_proveedor,
                    p.precio_costo,
                    p.precio_venta,
                    -- Calcular margen
                    CASE 
                        WHEN p.precio_costo > 0 
                        THEN ROUND(((p.precio_venta - p.precio_costo) / p.precio_costo) * 100, 1)
                        ELSE 0 
                    END as margen_porcentaje,
                    -- Calcular ventas últimos 30 días
                    COALESCE((
                        SELECT SUM(dv.cantidad_vendida) 
                        FROM detalle_venta dv
                        WHERE dv.id_producto = p.id 
                        AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    ), 0) as ventas_30_dias,
                    -- Calcular rotación
                    CASE 
                        WHEN p.cantidad > 0 
                        THEN COALESCE((
                            SELECT SUM(dv.cantidad_vendida) 
                            FROM detalle_venta dv
                            WHERE dv.id_producto = p.id 
                            AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                        ), 0) / p.cantidad * 100
                        ELSE 0 
                    END as rotacion_porcentaje
                FROM productos p
                LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                WHERE 1=1
            """
            
            params = []
            
            if filtros:
                if filtros.get('categoria'):
                    query += " AND p.categoria = %s"
                    params.append(filtros['categoria'])
                
                if filtros.get('proveedor'):
                    query += " AND p.proveedor = %s"
                    params.append(filtros['proveedor'])
                
                if filtros.get('estado_stock'):
                    estado = filtros['estado_stock']
                    if estado == 'critico':
                        query += " AND p.cantidad < 10"
                    elif estado == 'bajo':
                        query += " AND p.cantidad BETWEEN 10 AND 25"
                    elif estado == 'medio':
                        query += " AND p.cantidad BETWEEN 25 AND 75"
                    elif estado == 'alto':
                        query += " AND p.cantidad > 75"
                    elif estado == 'agotado':
                        query += " AND p.cantidad <= 0"
                
                if filtros.get('busqueda'):
                    query += " AND (p.nombre LIKE %s OR p.descripcion LIKE %s OR p.categoria LIKE %s)"
                    busqueda_term = f"%{filtros['busqueda']}%"
                    params.extend([busqueda_term, busqueda_term, busqueda_term])
            
            query += " ORDER BY p.nombre"
            
            cursor.execute(query, params)
            productos = cursor.fetchall()
            
            # Calcular estado de stock para cada producto
            for producto in productos:
                stock = producto['stock_actual']
                
                if stock <= 0:
                    estado = 'agotado'
                    clase = 'stock-critico'
                    label = 'AGOTADO'
                elif stock < 10:
                    estado = 'critico'
                    clase = 'stock-critico'
                    label = 'CRÍTICO'
                elif stock < 25:
                    estado = 'bajo'
                    clase = 'stock-bajo'
                    label = 'BAJO'
                elif stock < 75:
                    estado = 'medio'
                    clase = 'stock-medio'
                    label = 'MEDIO'
                else:
                    estado = 'alto'
                    clase = 'stock-alto'
                    label = 'ALTO'
                
                producto['estado_stock'] = estado
                producto['estado_clase'] = clase
                producto['estado_label'] = label
                producto['valor_total'] = stock * producto.get('precio_costo', 0)
                producto['codigo_formateado'] = f"#{str(producto['id']).zfill(4)}"
            
            cursor.close()
            conn.close()
            
            productos = convertir_para_json(productos)
            
            logger.info(f"Obtenidos {len(productos)} productos del inventario")
            return {
                'success': True,
                'productos': productos,
                'total': len(productos)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo productos inventario: {e}")
            return {
                'success': False,
                'error': str(e),
                'productos': [],
                'total': 0
            }
    

    @staticmethod
    def obtener_ventas_mensuales(mes, anio):
        """Obtener ventas mensuales por producto"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Validar que el mes/año no sea futuro
            hoy = datetime.now()
            if anio > hoy.year or (anio == hoy.year and mes > hoy.month):
                return {
                    'success': False,
                    'error': 'No se pueden obtener datos de meses futuros'
                }
            
            # Consulta corregida para obtener ventas mensuales
            query = """
                SELECT 
                    p.categoria as tipo_producto,
                    p.nombre as nombre_producto,
                    p.presentacion as unidad_presentacion,
                    COALESCE(SUM(dv.cantidad_vendida), 0) as cantidad_unidades_vendidas,
                    COALESCE(SUM(dv.precio_neto), 0) as valor_ventas
                FROM productos p
                LEFT JOIN detalle_venta dv ON p.id = dv.id_producto
                LEFT JOIN ventas v ON dv.id_venta = v.id
                WHERE dv.fecha_venta IS NOT NULL 
                    AND MONTH(dv.fecha_venta) = %s 
                    AND YEAR(dv.fecha_venta) = %s
                GROUP BY p.id, p.categoria, p.nombre, p.presentacion
                HAVING COALESCE(SUM(dv.cantidad_vendida), 0) > 0
                ORDER BY p.categoria, valor_ventas DESC
            """
            
            cursor.execute(query, (mes, anio))
            resultados = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            resultados = convertir_para_json(resultados)
            
            return {
                'success': True,
                'ventas_mensuales': resultados,
                'mes': mes,
                'anio': anio,
                'total_registros': len(resultados)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ventas mensuales: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas_mensuales': [],
                'total_registros': 0
            }
        
    @staticmethod
    def obtener_estadisticas_inventario():
        """Obtener estadísticas generales del inventario"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            stats = {}
            
            # Total productos
            cursor.execute("SELECT COUNT(*) as total FROM productos")
            stats['total_productos'] = cursor.fetchone()['total']
            
            # Valor total inventario
            cursor.execute("""
                SELECT 
                    SUM(cantidad * precio_costo) as valor_total,
                    SUM(cantidad * precio_venta) as valor_venta_total
                FROM productos 
                WHERE precio_costo IS NOT NULL
            """)
            result = cursor.fetchone()
            stats['valor_inventario'] = float(result['valor_total'] or 0)
            stats['valor_venta_inventario'] = float(result['valor_venta_total'] or 0)
            
            # Productos con stock crítico (< 10)
            cursor.execute("SELECT COUNT(*) as critico FROM productos WHERE cantidad < 10 AND cantidad > 0")
            stats['stock_critico'] = cursor.fetchone()['critico']
            
            # Productos agotados
            cursor.execute("SELECT COUNT(*) as agotado FROM productos WHERE cantidad <= 0")
            stats['stock_agotado'] = cursor.fetchone()['agotado']
            
            # Estado de stock agrupado
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN cantidad <= 0 THEN 1 END) as agotado,
                    COUNT(CASE WHEN cantidad > 0 AND cantidad < 10 THEN 1 END) as critico,
                    COUNT(CASE WHEN cantidad BETWEEN 10 AND 25 THEN 1 END) as bajo,
                    COUNT(CASE WHEN cantidad BETWEEN 25 AND 75 THEN 1 END) as medio,
                    COUNT(CASE WHEN cantidad > 75 THEN 1 END) as alto
                FROM productos
            """)
            stats['estado_stock_agrupado'] = cursor.fetchone()
            
            # Rotación (ventas últimos 30 días / stock total)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(dv.cantidad_vendida), 0) as ventas_30_dias,
                    COALESCE(SUM(p.cantidad), 0) as stock_total
                FROM productos p
                LEFT JOIN detalle_venta dv ON p.id = dv.id_producto 
                    AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            """)
            rotacion = cursor.fetchone()
            if rotacion['stock_total'] > 0:
                stats['rotacion_porcentaje'] = (rotacion['ventas_30_dias'] / rotacion['stock_total']) * 100
            else:
                stats['rotacion_porcentaje'] = 0
            
            # Distribución por categoría
            cursor.execute("""
                SELECT 
                    categoria, 
                    COUNT(*) as cantidad_productos, 
                    SUM(cantidad) as total_stock,
                    SUM(cantidad * precio_costo) as valor_total
                FROM productos
                GROUP BY categoria
                ORDER BY cantidad_productos DESC
            """)
            stats['distribucion_categoria'] = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            stats = convertir_para_json(stats)
            
            return {
                'success': True,
                'estadisticas': stats
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas inventario: {e}")
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {}
            }
    
    @staticmethod
    def obtener_movimientos_recientes(limite=10):
        """Obtener movimientos recientes (ventas como salidas)"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    dv.id,
                    dv.id_venta,
                    v.numero_venta,
                    dv.id_producto,
                    p.nombre as producto_nombre,
                    p.categoria,
                    dv.cantidad_vendida as cantidad,
                    dv.precio_unidad,
                    dv.precio_neto,
                    dv.fecha_venta,
                    v.fecha_hora,
                    v.nombre_cliente,
                    v.tipo_pago,
                    'salida' as tipo_movimiento,
                    'venta' as motivo,
                    CONCAT(SUBSTRING(v.fecha_hora, 1, 5), ' hrs') as hora_formateada
                FROM detalle_venta dv
                JOIN productos p ON dv.id_producto = p.id
                JOIN ventas v ON dv.id_venta = v.id
                WHERE dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                ORDER BY dv.fecha_venta DESC, v.fecha_hora DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limite,))
            movimientos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            movimientos = convertir_para_json(movimientos)
            
            return {
                'success': True,
                'movimientos': movimientos,
                'total': len(movimientos)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo movimientos recientes: {e}")
            return {
                'success': False,
                'error': str(e),
                'movimientos': [],
                'total': 0
            }
    
    @staticmethod
    def obtener_productos_mas_vendidos(dias=30, limite=5):
        """Obtener los productos más vendidos en un período"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    p.id,
                    p.nombre,
                    p.categoria,
                    p.presentacion,
                    p.precio_venta,
                    SUM(dv.cantidad_vendida) as cantidad_vendida,
                    SUM(dv.precio_neto) as ingresos_totales,
                    p.cantidad as stock_actual
                FROM productos p
                JOIN detalle_venta dv ON p.id = dv.id_producto
                WHERE dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                GROUP BY p.id, p.nombre, p.categoria, p.presentacion, p.precio_venta, p.cantidad
                ORDER BY cantidad_vendida DESC
                LIMIT %s
            """
            
            cursor.execute(query, (dias, limite))
            productos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            productos = convertir_para_json(productos)
            
            return {
                'success': True,
                'productos': productos,
                'periodo_dias': dias
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo productos más vendidos: {e}")
            return {
                'success': False,
                'error': str(e),
                'productos': [],
                'periodo_dias': dias
            }
    
    @staticmethod
    def obtener_filtros_disponibles():
        """Obtener listas para filtros"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Categorías
            cursor.execute("SELECT DISTINCT categoria FROM productos ORDER BY categoria")
            categorias = [row['categoria'] for row in cursor.fetchall()]
            
            # Proveedores activos
            cursor.execute("""
                SELECT DISTINCT 
                    p.telefono,
                    p.nombre_empresa
                FROM proveedor p
                JOIN productos pr ON p.telefono = pr.proveedor
                WHERE p.estado = 'activo'
                ORDER BY p.nombre_empresa
            """)
            proveedores = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'categorias': categorias,
                'proveedores': convertir_para_json(proveedores)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo filtros disponibles: {e}")
            return {
                'success': False,
                'error': str(e),
                'categorias': [],
                'proveedores': []
            }
    
    @staticmethod
    def ajustar_stock_producto(producto_id, cantidad, tipo, motivo='', observaciones='', usuario_id=1):
        """Ajustar stock de un producto (entrada/salida/ajuste)"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Obtener stock actual
            cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (producto_id,))
            producto = cursor.fetchone()
            
            if not producto:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'error': 'Producto no encontrado'
                }
            
            stock_actual = producto['cantidad']
            nuevo_stock = stock_actual
            
            # Calcular nuevo stock según tipo
            if tipo == 'entrada':
                nuevo_stock = stock_actual + cantidad
            elif tipo == 'salida':
                if cantidad > stock_actual:
                    cursor.close()
                    conn.close()
                    return {
                        'success': False,
                        'error': 'No hay suficiente stock disponible'
                    }
                nuevo_stock = stock_actual - cantidad
            elif tipo == 'ajuste':
                nuevo_stock = cantidad
            else:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'error': 'Tipo de ajuste inválido'
                }
            
            # Actualizar stock
            cursor.execute("UPDATE productos SET cantidad = %s WHERE id = %s", (nuevo_stock, producto_id))
            
            # Aquí podrías insertar en una tabla de movimientos_inventario si existiera
            # Por ahora, solo actualizamos el stock
            
            conn.commit()
            
            # Obtener producto actualizado
            cursor.execute("""
                SELECT p.*, pr.nombre_proveedor 
                FROM productos p
                LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                WHERE p.id = %s
            """, (producto_id,))
            producto_actualizado = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            producto_actualizado = convertir_para_json(producto_actualizado)
            
            logger.info(f"Stock ajustado: Producto {producto_id}, Tipo: {tipo}, Cantidad: {cantidad}, Stock anterior: {stock_actual}, Nuevo stock: {nuevo_stock}")
            
            return {
                'success': True,
                'message': 'Stock ajustado exitosamente',
                'producto': producto_actualizado,
                'ajuste': {
                    'tipo': tipo,
                    'cantidad': cantidad,
                    'stock_anterior': stock_actual,
                    'nuevo_stock': nuevo_stock,
                    'motivo': motivo,
                    'fecha': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error ajustando stock: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def obtener_detalle_producto(producto_id):
        """Obtener detalle completo de un producto"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Información básica del producto
            query = """
                SELECT 
                    p.*,
                    pr.nombre_proveedor,
                    pr.nombre_empresa,
                    pr.telefono as telefono_proveedor,
                    pr.correo as correo_proveedor,
                    -- Calcular estadísticas
                    COALESCE((
                        SELECT SUM(dv.cantidad_vendida) 
                        FROM detalle_venta dv
                        WHERE dv.id_producto = p.id 
                        AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                    ), 0) as ventas_30_dias,
                    COALESCE((
                        SELECT SUM(dv.cantidad_vendida) 
                        FROM detalle_venta dv
                        WHERE dv.id_producto = p.id 
                        AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
                    ), 0) as ventas_90_dias
                FROM productos p
                LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
                WHERE p.id = %s
            """
            
            cursor.execute(query, (producto_id,))
            producto = cursor.fetchone()
            
            if not producto:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'error': 'Producto no encontrado'
                }
            
            # Ventas recientes por mes
            cursor.execute("""
                SELECT 
                    DATE_FORMAT(dv.fecha_venta, '%Y-%m') as mes,
                    SUM(dv.cantidad_vendida) as cantidad_vendida,
                    SUM(dv.precio_neto) as ingresos_totales
                FROM detalle_venta dv
                WHERE dv.id_producto = %s
                AND dv.fecha_venta >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(dv.fecha_venta, '%Y-%m')
                ORDER BY mes DESC
            """, (producto_id,))
            ventas_por_mes = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            producto = convertir_para_json(producto)
            ventas_por_mes = convertir_para_json(ventas_por_mes)
            
            return {
                'success': True,
                'producto': producto,
                'ventas_por_mes': ventas_por_mes
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo detalle producto: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# Instancia global del modelo
model = InventarioModel()