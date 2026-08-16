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

class HistorialVentaModel:
    
    @staticmethod
    def obtener_historial_completo():
        """Obtener el historial completo de ventas con detalles"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    v.fecha_dia,
                    v.fecha_hora,
                    v.nombre_cliente,
                    v.direccion_cliente,
                    v.telefono_cliente,
                    v.tipo_pago,
                    v.cliente_cedula,
                    v.subtotal,
                    v.descuento,
                    v.total,
                    v.dias_credito,
                    v.submetodo_banco,
                    v.usuario_id,
                    v.estado,
                    COUNT(dv.id) as total_productos,
                    SUM(dv.cantidad_vendida) as total_unidades
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                GROUP BY v.id, v.fecha_dia, v.fecha_hora
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(query)
            ventas = cursor.fetchall()
            
            # Para cada venta, obtener los productos
            for venta in ventas:
                producto_query = """
                    SELECT 
                        dv.id,
                        dv.id_producto,
                        p.nombre,
                        p.categoria,
                        p.presentacion,
                        dv.cantidad_vendida as cantidad,
                        dv.precio_unidad as precio_unitario,
                        dv.precio_neto as subtotal
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                venta['productos'] = cursor.fetchall()
                
                # Determinar tipo de usuario (cliente/proveedor basado en cedula)
                if venta['cliente_cedula']:
                    # Verificar si es cliente o proveedor
                    cursor.execute("SELECT 'cliente' as tipo FROM cliente WHERE cedula = %s", 
                                 (venta['cliente_cedula'],))
                    resultado = cursor.fetchone()
                    venta['usuario_tipo'] = resultado['tipo'] if resultado else 'cliente'
                else:
                    venta['usuario_tipo'] = 'cliente'
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            ventas = convertir_para_json(ventas)
            
            logger.info(f"Obtenidas {len(ventas)} ventas del historial")
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo historial completo: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }
    
    @staticmethod
    def filtrar_ventas(fecha_inicio=None, fecha_fin=None, tipo_pago=None, 
                       tipo_usuario=None, cliente_cedula=None, producto_id=None):
        """Filtrar ventas según criterios"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Construir consulta base
            query = """
                SELECT DISTINCT
                    v.id,
                    v.numero_venta,
                    v.fecha_dia,
                    v.fecha_hora,
                    v.nombre_cliente,
                    v.direccion_cliente,
                    v.telefono_cliente,
                    v.tipo_pago,
                    v.cliente_cedula,
                    v.subtotal,
                    v.descuento,
                    v.total,
                    v.dias_credito,
                    v.submetodo_banco,
                    v.usuario_id,
                    v.estado
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                WHERE 1=1
            """
            params = []
            
            # Filtros de fecha
            if fecha_inicio and fecha_fin:
                query += " AND v.fecha_dia BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                query += " AND v.fecha_dia >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                query += " AND v.fecha_dia <= %s"
                params.append(fecha_fin)
            
            # Filtro por tipo de pago
            if tipo_pago:
                query += " AND v.tipo_pago = %s"
                params.append(tipo_pago)
            
            # Filtro por tipo de usuario
            if tipo_usuario:
                if tipo_usuario == 'cliente':
                    query += " AND v.cliente_cedula IS NOT NULL"
                elif tipo_usuario == 'proveedor':
                    # En tu esquema actual, no hay ventas a proveedores
                    # Esto sería para compras
                    query += " AND 1=0"  # No devuelve resultados
            
            # Filtro por cliente específico
            if cliente_cedula:
                query += " AND v.cliente_cedula = %s"
                params.append(cliente_cedula)
            
            # Filtro por producto
            if producto_id:
                query += " AND dv.id_producto = %s"
                params.append(producto_id)
            
            query += " ORDER BY v.fecha_dia DESC, v.fecha_hora DESC"
            
            cursor.execute(query, params)
            ventas = cursor.fetchall()
            
            # Obtener detalles para cada venta
            for venta in ventas:
                # Productos
                producto_query = """
                    SELECT 
                        dv.id,
                        dv.id_producto,
                        p.nombre,
                        p.categoria,
                        p.presentacion,
                        dv.cantidad_vendida as cantidad,
                        dv.precio_unidad as precio_unitario,
                        dv.precio_neto as subtotal
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                venta['productos'] = cursor.fetchall()
                
                # Calcular total de productos y unidades
                total_productos = len(venta['productos'])
                total_unidades = sum(p.get('cantidad', 0) for p in venta['productos'])
                venta['total_productos'] = total_productos
                venta['total_unidades'] = total_unidades
                
                # Tipo de usuario
                if venta['cliente_cedula']:
                    venta['usuario_tipo'] = 'cliente'
                else:
                    venta['usuario_tipo'] = 'cliente'  # Por defecto
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            ventas = convertir_para_json(ventas)
            
            logger.info(f"Filtradas {len(ventas)} ventas")
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error filtrando ventas: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }
    
    @staticmethod
    def obtener_estadisticas_periodo(fecha_inicio=None, fecha_fin=None):
        """Obtener estadísticas del período"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Construir consulta base
            query = """
                SELECT 
                    COUNT(*) as total_ventas,
                    SUM(v.total) as ingresos_totales,
                    AVG(v.total) as promedio_venta,
                    SUM(dv.cantidad_vendida) as total_unidades_vendidas
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                WHERE 1=1
            """
            params = []
            
            # Filtros de fecha
            if fecha_inicio and fecha_fin:
                query += " AND v.fecha_dia BETWEEN %s AND %s"
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                query += " AND v.fecha_dia >= %s"
                params.append(fecha_inicio)
            elif fecha_fin:
                query += " AND v.fecha_dia <= %s"
                params.append(fecha_fin)
            
            cursor.execute(query, params)
            estadisticas = cursor.fetchone()
            
            # Estadísticas por tipo de pago
            pago_query = """
                SELECT 
                    tipo_pago,
                    COUNT(*) as cantidad,
                    SUM(total) as monto_total
                FROM ventas
                WHERE 1=1
            """
            if fecha_inicio and fecha_fin:
                pago_query += " AND fecha_dia BETWEEN %s AND %s"
                pago_params = [fecha_inicio, fecha_fin]
            else:
                pago_params = []
            
            pago_query += " GROUP BY tipo_pago"
            
            if pago_params:
                cursor.execute(pago_query, pago_params)
            else:
                cursor.execute(pago_query)
            
            ventas_por_pago = cursor.fetchall()
            
            # Ventas por día (últimos 7 días)
            hoy = datetime.now()
            siete_dias_atras = hoy - timedelta(days=6)
            
            tendencia_query = """
                SELECT 
                    fecha_dia,
                    COUNT(*) as cantidad_ventas,
                    SUM(total) as total_dia
                FROM ventas
                WHERE fecha_dia BETWEEN %s AND %s
                GROUP BY fecha_dia
                ORDER BY fecha_dia
            """
            
            cursor.execute(tendencia_query, (siete_dias_atras.date(), hoy.date()))
            tendencia_ventas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convertir tipos no serializables
            if estadisticas:
                estadisticas = convertir_para_json(estadisticas)
            if ventas_por_pago:
                ventas_por_pago = convertir_para_json(ventas_por_pago)
            if tendencia_ventas:
                tendencia_ventas = convertir_para_json(tendencia_ventas)
            
            # Procesar resultados
            resultado = {
                'success': True,
                'estadisticas': {
                    'total_ventas': int(estadisticas.get('total_ventas', 0)) if estadisticas else 0,
                    'ingresos_totales': float(estadisticas.get('ingresos_totales', 0)) if estadisticas else 0.0,
                    'promedio_venta': float(estadisticas.get('promedio_venta', 0)) if estadisticas else 0.0,
                    'total_unidades': int(estadisticas.get('total_unidades_vendidas', 0)) if estadisticas else 0
                },
                'ventas_por_pago': ventas_por_pago if ventas_por_pago else [],
                'tendencia_ventas': tendencia_ventas if tendencia_ventas else []
            }
            
            logger.info(f"Estadísticas obtenidas: {resultado['estadisticas']}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {
                    'total_ventas': 0,
                    'ingresos_totales': 0.0,
                    'promedio_venta': 0.0,
                    'total_unidades': 0
                },
                'ventas_por_pago': [],
                'tendencia_ventas': []
            }
    
    @staticmethod
    def obtener_detalle_venta(venta_id):
        """Obtener detalle completo de una venta específica"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Información básica de la venta
            venta_query = """
                SELECT 
                    v.*,
                    c.correo as cliente_correo,
                    c.direccion as cliente_direccion_completa
                FROM ventas v
                LEFT JOIN cliente c ON v.cliente_cedula = c.cedula
                WHERE v.id = %s
            """
            cursor.execute(venta_query, (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                return {
                    'success': False,
                    'error': 'Venta no encontrada'
                }
            
            # Productos de la venta
            productos_query = """
                SELECT 
                    dv.id,
                    dv.id_producto,
                    p.nombre,
                    p.descripcion,
                    p.categoria,
                    p.presentacion,
                    dv.cantidad_vendida as cantidad,
                    dv.precio_unidad as precio_unitario,
                    dv.precio_neto as subtotal
                FROM detalle_venta dv
                JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
            """
            cursor.execute(productos_query, (venta_id,))
            venta['productos'] = cursor.fetchall()
            
            # Si es crédito, obtener información del crédito
            if venta.get('tipo_pago') == 'Crédito':
                credito_query = """
                    SELECT 
                        c.*,
                        DATEDIFF(CURDATE(), c.fecha_vencimiento) as dias_vencido
                    FROM creditos c
                    WHERE c.venta_id = %s
                """
                cursor.execute(credito_query, (venta_id,))
                credito = cursor.fetchone()
                if credito:
                    venta['credito'] = credito
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            venta = convertir_para_json(venta)
            
            logger.info(f"Detalle obtenido para venta ID: {venta_id}")
            return {
                'success': True,
                'venta': venta
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo detalle de venta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def obtener_clientes_para_filtro():
        """Obtener lista de clientes para el filtro"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # CORREGIDO: Usar nombre_empresa en lugar de nombre para proveedores
            query = """
                SELECT 
                    cedula as id,
                    nombre,
                    telefono,
                    'cliente' as tipo
                FROM cliente
                UNION
                SELECT 
                    telefono as id,
                    nombre_empresa as nombre,
                    telefono,
                    'proveedor' as tipo
                FROM proveedor
                ORDER BY nombre
            """
            
            cursor.execute(query)
            usuarios = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            usuarios = convertir_para_json(usuarios)
            
            return {
                'success': True,
                'usuarios': usuarios
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo clientes para filtro: {e}")
            return {
                'success': False,
                'error': str(e),
                'usuarios': []
            }
    
    @staticmethod
    def obtener_productos_para_filtro():
        """Obtener lista de productos para el filtro"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    id,
                    nombre,
                    categoria,
                    presentacion
                FROM productos
                WHERE cantidad > 0
                ORDER BY nombre
            """
            
            cursor.execute(query)
            productos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            productos = convertir_para_json(productos)
            
            return {
                'success': True,
                'productos': productos
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo productos para filtro: {e}")
            return {
                'success': False,
                'error': str(e),
                'productos': []
            }
    
    @staticmethod
    def obtener_ventas_recientes(limit=10):
        """Obtener las ventas más recientes"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    v.fecha_dia,
                    v.fecha_hora,
                    v.nombre_cliente,
                    v.tipo_pago,
                    v.total,
                    COUNT(dv.id) as total_productos
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                GROUP BY v.id, v.fecha_dia, v.fecha_hora
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            ventas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Convertir para JSON
            ventas = convertir_para_json(ventas)
            
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ventas recientes: {e}")
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }

# Instancia global del modelo
model = HistorialVentaModel()