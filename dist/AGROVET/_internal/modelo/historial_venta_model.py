from database import db
from datetime import datetime, timedelta, date
import logging
from decimal import Decimal
import sys
import os
import unicodedata

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# ============================================================
#  FUNCIÓN: Normalizar texto (sin tildes, espacios, mayúsculas)
# ============================================================
def normalizar_texto(texto):
    """Normalizar texto: minúsculas, sin tildes, sin espacios extra"""
    if not texto:
        return ''
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

# ============================================================
#  FUNCIÓN: Convertir datos a JSON
# ============================================================
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
        meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        hora_12 = data.hour % 12
        if hora_12 == 0:
            hora_12 = 12
        ampm = "AM" if data.hour < 12 else "PM"
        fecha = f"{data.day:02d} {meses[data.month-1]} {data.year}"
        if data.hour != 0 or data.minute != 0 or data.second != 0:
            fecha += f" {hora_12:02d}:{data.minute:02d} {ampm}"
        return fecha
    elif isinstance(data, date):
        meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
        return f"{data.day:02d} {meses[data.month-1]} {data.year}"
    elif isinstance(data, bytes):
        return data.decode('utf-8')
    elif hasattr(data, '__dict__'):
        return convertir_para_json(data.__dict__)
    else:
        return data

class HistorialVentaModel:
    
    # ============================================================
    #  OBTENER HISTORIAL COMPLETO
    # ============================================================
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
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
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
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                    (SELECT COUNT(*) FROM ventas_mixtas vm WHERE vm.id_venta = v.id) as es_mixta
                FROM ventas v
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(query)
            ventas = cursor.fetchall()
            
            for venta in ventas:
                # Combinar fecha y hora
                if venta.get('fecha_dia') and venta.get('fecha_hora'):
                    try:
                        fecha_obj = venta['fecha_dia']
                        hora_str = str(venta['fecha_hora'])
                        if isinstance(fecha_obj, date):
                            hora_partes = hora_str.split(':')
                            hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                            minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                            segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                            fecha_datetime = datetime(
                                fecha_obj.year, fecha_obj.month, fecha_obj.day,
                                hora, minuto, segundo
                            )
                            venta['fecha_completa'] = fecha_datetime
                    except Exception as e:
                        logger.warning(f"Error combinando fecha/hora: {e}")
                        venta['fecha_completa'] = venta['fecha_dia']
                else:
                    venta['fecha_completa'] = venta['fecha_dia']
                
                # Obtener información del crédito
                credito_query = """
                    SELECT 
                        c.estado as estado_credito,
                        c.anticipo as anticipo_credito,
                        c.abonos_realizados as abonos_credito,
                        c.saldo_pendiente as saldo_pendiente_credito,
                        c.deuda_inicial as deuda_inicial_credito,
                        c.fecha_vencimiento as fecha_vencimiento_credito
                    FROM creditos c
                    WHERE c.venta_id = %s
                    LIMIT 1
                """
                cursor.execute(credito_query, (venta['id'],))
                credito = cursor.fetchone()
                
                if credito:
                    venta.update(credito)
                else:
                    venta['estado_credito'] = None
                    venta['anticipo_credito'] = 0
                    venta['abonos_credito'] = 0
                    venta['saldo_pendiente_credito'] = 0
                    venta['deuda_inicial_credito'] = 0
                    venta['fecha_vencimiento_credito'] = None
                
                # Si es venta mixta, obtener detalles
                if venta['es_mixta']:
                    mixta_query = """
                        SELECT 
                            categoria,
                            metodo_pago,
                            submetodo,
                            SUM(monto) as monto_total
                        FROM ventas_mixtas
                        WHERE id_venta = %s
                        GROUP BY categoria, metodo_pago, submetodo
                        ORDER BY categoria, metodo_pago
                    """
                    cursor.execute(mixta_query, (venta['id'],))
                    detalles_mixtos = cursor.fetchall()
                    venta['detalles_mixtos'] = detalles_mixtos
                
                # Obtener productos
                producto_query = """
                    SELECT 
                        dv.id,
                        dv.id_producto,
                        p.nombre,
                        p.categoria,
                        p.presentacion,
                        dv.cantidad_vendida as cantidad,
                        dv.precio_unidad as precio_unitario,
                        dv.precio_neto as subtotal,
                        p.precio_costo,
                        p.precio_venta,
                        (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                productos = cursor.fetchall()
                
                utilidad_total = 0
                costo_total = 0
                
                for producto in productos:
                    precio_unidad = float(producto.get('precio_unitario', 0))
                    precio_costo = float(producto.get('precio_costo', 0))
                    cantidad = int(producto.get('cantidad', 0))
                    
                    utilidad_producto = (precio_unidad - precio_costo) * cantidad
                    producto['utilidad_producto'] = utilidad_producto
                    
                    utilidad_total += utilidad_producto
                    costo_total += precio_costo * cantidad
                
                venta['productos'] = productos
                venta['utilidad'] = utilidad_total
                venta['costo_total'] = costo_total
                
                # Utilidad realizada vs proyectada
                if venta['es_mixta']:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                elif venta.get('tipo_pago') == 'CRÉDITO':
                    if venta.get('estado_credito') == 'pagado':
                        venta['utilidad_realizada'] = utilidad_total
                        venta['utilidad_proyectada'] = 0
                    else:
                        venta['utilidad_realizada'] = 0
                        venta['utilidad_proyectada'] = utilidad_total
                else:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
            
            cursor.close()
            conn.close()
            
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

    # ============================================================
    #  OBTENER INGRESOS POR CATEGORÍA DE PAGO
    # ============================================================
    @staticmethod
    def obtener_ingresos_por_categoria_pago(fecha_inicio=None, fecha_fin=None, periodo=None, hora_inicio=None, hora_fin=None):
        """Obtener ingresos por categoría de pago SIN ventas mixtas"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_parts = []
            params = []
            
            if fecha_inicio and fecha_fin:
                where_parts.append("v.fecha_dia BETWEEN %s AND %s")
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_parts.append("v.fecha_dia >= %s")
                params.append(fecha_inicio)
            elif fecha_fin:
                where_parts.append("v.fecha_dia <= %s")
                params.append(fecha_fin)
            
            if hora_inicio:
                where_parts.append("TIME(v.fecha_hora) >= %s")
                params.append(hora_inicio)
            if hora_fin:
                where_parts.append("TIME(v.fecha_hora) <= %s")
                params.append(hora_fin)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            query = f"""
                SELECT 
                    CASE 
                        WHEN v.tipo_pago = 'CONTADO' THEN 'CONTADO'
                        WHEN v.tipo_pago = 'CRÉDITO' THEN 'CRÉDITO'
                        WHEN v.tipo_pago IN ('NEQUI', 'TRANSACCIÓN', 'TARJETA') THEN 'BANCO'
                        ELSE 'BANCO'
                    END as categoria_pago,
                    COUNT(DISTINCT v.id) as cantidad_ventas,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CONTADO' THEN v.total
                            WHEN v.tipo_pago = 'NEQUI' THEN v.total
                            WHEN v.tipo_pago = 'TRANSACCIÓN' THEN v.total
                            WHEN v.tipo_pago = 'TARJETA' THEN v.total
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE v.total
                        END
                    ), 0) as ingresos_reales,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN v.total
                            ELSE 0
                        END
                    ), 0) as total_creditos,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.saldo_pendiente, 0)
                            ELSE 0
                        END
                    ), 0) as saldo_pendiente
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id AND v.tipo_pago = 'CRÉDITO'
                WHERE v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
                    AND {where_clause}
                GROUP BY categoria_pago
                ORDER BY ingresos_reales DESC
            """
            
            cursor.execute(query, params)
            categorias = cursor.fetchall()
            
            # Obtener detalle de métodos bancarios
            bancos_query = f"""
                SELECT 
                    v.tipo_pago as metodo_pago,
                    COUNT(DISTINCT v.id) as cantidad_ventas,
                    COALESCE(SUM(v.total), 0) as monto_total
                FROM ventas v
                WHERE v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
                    AND v.tipo_pago NOT IN ('CONTADO', 'CRÉDITO')
                    AND {where_clause}
                GROUP BY v.tipo_pago
                ORDER BY monto_total DESC
            """
            
            cursor.execute(bancos_query, params)
            metodos_bancarios = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            resultado = []
            for categoria in categorias:
                cat_data = convertir_para_json(categoria)
                
                if cat_data['cantidad_ventas'] > 0:
                    if cat_data['categoria_pago'] == 'BANCO':
                        cat_data['detalle_bancos'] = []
                        for metodo in metodos_bancarios:
                            metodo_data = convertir_para_json(metodo)
                            if metodo_data['monto_total'] > 0:
                                tipo_pago = str(metodo_data['metodo_pago']).upper().strip()
                                mapeo_tipos = {
                                    'NEQUI': 'NEQUI',
                                    'TRANSACCIÓN': 'TRANSACCIÓN',
                                    'TRANSFERENCIA': 'TRANSFERENCIA',
                                    'TARJETA': 'TARJETA',
                                    'BANCO': 'TRANSFERENCIA BANCARIA'
                                }
                                nombre_tipo = mapeo_tipos.get(tipo_pago, tipo_pago)
                                cat_data['detalle_bancos'].append({
                                    'metodo': nombre_tipo,
                                    'cantidad': int(metodo_data['cantidad_ventas']),
                                    'monto': float(metodo_data['monto_total'])
                                })
                    
                    resultado.append({
                        'categoria': cat_data['categoria_pago'],
                        'cantidad_ventas': int(cat_data['cantidad_ventas']),
                        'ingresos_reales': float(cat_data['ingresos_reales']),
                        'total_creditos': float(cat_data.get('total_creditos', 0)),
                        'saldo_pendiente': float(cat_data.get('saldo_pendiente', 0)),
                        'detalle_bancos': cat_data.get('detalle_bancos', [])
                    })
            
            logger.info(f"Ingresos por categoría: {len(resultado)} categorías")
            return {
                'success': True,
                'ingresos': resultado
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ingresos por categoría: {e}")
            return {
                'success': False,
                'error': str(e),
                'ingresos': []
            }

    # ============================================================
    #  FILTRAR VENTAS (CORREGIDO)
    # ============================================================
    @staticmethod
    def filtrar_ventas(fecha_inicio=None, fecha_fin=None, tipo_pago=None, 
                       tipo_usuario=None, cliente_cedula=None, producto_id=None,
                       hora_inicio=None, hora_fin=None):
        """Filtrar ventas según criterios con normalización"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # ============================================================
            #  CONSTRUIR WHERE DINÁMICAMENTE (solo filtros con valor)
            # ============================================================
            where_parts = []
            params = []
            
            # Fechas
            if fecha_inicio and fecha_fin:
                where_parts.append("v.fecha_dia BETWEEN %s AND %s")
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_parts.append("v.fecha_dia >= %s")
                params.append(fecha_inicio)
            elif fecha_fin:
                where_parts.append("v.fecha_dia <= %s")
                params.append(fecha_fin)
            
            # Horas
            if hora_inicio:
                where_parts.append("TIME(v.fecha_hora) >= %s")
                params.append(hora_inicio)
            if hora_fin:
                where_parts.append("TIME(v.fecha_hora) <= %s")
                params.append(hora_fin)
            
            # Tipo de pago
            if tipo_pago:
                where_parts.append("v.tipo_pago = %s")
                params.append(tipo_pago)
            
            # ============================================================
            #  CLIENTE - BÚSQUEDA NORMALIZADA
            # ============================================================
            if cliente_cedula:
                cliente_cedula = cliente_cedula.strip()
                
                # Cliente final (formato 'final|nombre|telefono')
                if cliente_cedula.startswith('final|'):
                    partes = cliente_cedula.split('|')
                    if len(partes) >= 2:
                        nombre_cliente = partes[1]
                        telefono_cliente = partes[2] if len(partes) > 2 else ''
                        
                        nombre_norm = normalizar_texto(nombre_cliente)
                        
                        where_parts.append("""
                            (LOWER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                COALESCE(v.nombre_cliente, ''), 
                                'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'))) = %s
                             OR LOWER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                                COALESCE(v.nombre_cliente, ''), 
                                'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'))) LIKE %s
                             OR v.telefono_cliente = %s)
                        """)
                        params.extend([nombre_norm, f'%{nombre_norm}%', telefono_cliente])
                else:
                    # Cliente registrado (por cédula o nombre)
                    cedula_norm = normalizar_texto(cliente_cedula)
                    where_parts.append("""
                        (v.cliente_cedula = %s 
                         OR LOWER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                            COALESCE(v.nombre_cliente, ''), 
                            'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'))) = %s
                         OR LOWER(TRIM(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                            COALESCE(v.nombre_cliente, ''), 
                            'á','a'), 'é','e'), 'í','i'), 'ó','o'), 'ú','u'))) LIKE %s)
                    """)
                    params.extend([cliente_cedula, cedula_norm, f'%{cedula_norm}%'])
            
            # Producto
            if producto_id:
                where_parts.append("""
                    EXISTS (SELECT 1 FROM detalle_venta dv 
                            WHERE dv.id_venta = v.id AND dv.id_producto = %s)
                """)
                params.append(producto_id)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            # ============================================================
            #  QUERY PRINCIPAL
            # ============================================================
            query = f"""
                SELECT 
                    v.id,
                    v.numero_venta,
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
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
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                    (SELECT COUNT(*) FROM ventas_mixtas vm WHERE vm.id_venta = v.id) as es_mixta,
                    c.estado as estado_credito,
                    c.anticipo as anticipo_credito,
                    c.abonos_realizados as abonos_credito,
                    c.saldo_pendiente as saldo_pendiente_credito,
                    c.deuda_inicial as deuda_inicial_credito
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(query, params)
            ventas = cursor.fetchall()
            
            # ============================================================
            #  ENRIQUECER CON PRODUCTOS Y UTILIDAD
            # ============================================================
            for venta in ventas:
                # Combinar fecha y hora
                if venta.get('fecha_dia') and venta.get('fecha_hora'):
                    try:
                        fecha_obj = venta['fecha_dia']
                        hora_str = str(venta['fecha_hora'])
                        if isinstance(fecha_obj, date):
                            hora_partes = hora_str.split(':')
                            hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                            minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                            segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                            fecha_datetime = datetime(
                                fecha_obj.year, fecha_obj.month, fecha_obj.day,
                                hora, minuto, segundo
                            )
                            venta['fecha_completa'] = fecha_datetime
                    except Exception:
                        venta['fecha_completa'] = venta['fecha_dia']
                else:
                    venta['fecha_completa'] = venta['fecha_dia']
                
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
                        dv.precio_neto as subtotal,
                        p.precio_costo,
                        p.precio_venta,
                        (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """
                cursor.execute(producto_query, (venta['id'],))
                productos = cursor.fetchall()
                
                utilidad_total = 0
                costo_total = 0
                
                for producto in productos:
                    precio_unidad = float(producto.get('precio_unitario', 0))
                    precio_costo = float(producto.get('precio_costo', 0))
                    cantidad = int(producto.get('cantidad', 0))
                    
                    utilidad_producto = (precio_unidad - precio_costo) * cantidad
                    producto['utilidad_producto'] = utilidad_producto
                    
                    utilidad_total += utilidad_producto
                    costo_total += precio_costo * cantidad
                
                venta['productos'] = productos
                venta['utilidad'] = utilidad_total
                venta['costo_total'] = costo_total
                
                # Utilidad realizada vs proyectada
                if venta['es_mixta']:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                elif venta.get('tipo_pago') == 'CRÉDITO':
                    if venta.get('estado_credito') == 'pagado':
                        venta['utilidad_realizada'] = utilidad_total
                        venta['utilidad_proyectada'] = 0
                    else:
                        venta['utilidad_realizada'] = 0
                        venta['utilidad_proyectada'] = utilidad_total
                else:
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
            
            cursor.close()
            conn.close()
            
            ventas = convertir_para_json(ventas)
            
            logger.info(f"Filtradas {len(ventas)} ventas")
            return {
                'success': True,
                'ventas': ventas,
                'total': len(ventas)
            }
            
        except Exception as e:
            logger.error(f"Error filtrando ventas: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'ventas': [],
                'total': 0
            }

    # ============================================================
    #  OBTENER ESTADÍSTICAS DEL PERÍODO
    # ============================================================
    @staticmethod
    def obtener_estadisticas_periodo(fecha_inicio=None, fecha_fin=None, hora_inicio=None, hora_fin=None):
        """Obtener estadísticas del período considerando créditos correctamente"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_parts = []
            params = []
            
            if fecha_inicio and fecha_fin:
                where_parts.append("v.fecha_dia BETWEEN %s AND %s")
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_parts.append("v.fecha_dia >= %s")
                params.append(fecha_inicio)
            elif fecha_fin:
                where_parts.append("v.fecha_dia <= %s")
                params.append(fecha_fin)
            
            if hora_inicio:
                where_parts.append("TIME(v.fecha_hora) >= %s")
                params.append(hora_inicio)
            if hora_fin:
                where_parts.append("TIME(v.fecha_hora) <= %s")
                params.append(hora_fin)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            query = f"""
                SELECT 
                    COUNT(DISTINCT v.id) as total_ventas,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN v.total
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE 0
                        END
                    ), 0) as ingresos_totales,
                    COALESCE(AVG(v.total), 0) as promedio_venta,
                    COALESCE(SUM(dv.cantidad_vendida), 0) as total_unidades
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
            """
            
            cursor.execute(query, params)
            estadisticas = cursor.fetchone()
            
            # Ventas por tipo de pago
            pago_query = f"""
                SELECT 
                    v.tipo_pago,
                    COUNT(DISTINCT v.id) as cantidad,
                    COALESCE(SUM(v.total), 0) as monto_total,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' THEN 
                                COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0)
                            ELSE v.total
                        END
                    ), 0) as ingresos_reales
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
                GROUP BY v.tipo_pago
            """
            
            cursor.execute(pago_query, params)
            ventas_por_pago = cursor.fetchall()
            
            # Tendencia (últimos 7 días)
            hoy = datetime.now()
            siete_dias_atras = hoy - timedelta(days=6)
            
            tendencia_query = """
                SELECT 
                    fecha_dia,
                    COUNT(*) as cantidad_ventas,
                    COALESCE(SUM(total), 0) as total_dia
                FROM ventas
                WHERE fecha_dia BETWEEN %s AND %s
                GROUP BY fecha_dia
                ORDER BY fecha_dia
            """
            
            cursor.execute(tendencia_query, (siete_dias_atras.date(), hoy.date()))
            tendencia_ventas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            estadisticas = convertir_para_json(estadisticas)
            ventas_por_pago = convertir_para_json(ventas_por_pago)
            tendencia_ventas = convertir_para_json(tendencia_ventas)
            
            return {
                'success': True,
                'estadisticas': {
                    'total_ventas': int(estadisticas.get('total_ventas', 0)),
                    'ingresos_totales': float(estadisticas.get('ingresos_totales', 0)),
                    'promedio_venta': float(estadisticas.get('promedio_venta', 0)),
                    'total_unidades': int(estadisticas.get('total_unidades', 0))
                },
                'ventas_por_pago': ventas_por_pago,
                'tendencia_ventas': tendencia_ventas,
                'ingresos_por_pago': []
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {
                    'total_ventas': 0,
                    'ingresos_totales': 0,
                    'promedio_venta': 0,
                    'total_unidades': 0
                },
                'ventas_por_pago': [],
                'tendencia_ventas': [],
                'ingresos_por_pago': []
            }

    # ============================================================
    #  OBTENER DETALLE DE VENTA
    # ============================================================
    @staticmethod
    def obtener_detalle_venta(venta_id):
        """Obtener detalle completo de una venta específica"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            venta_query = """
                SELECT 
                    v.*,
                    c.correo as cliente_correo,
                    c.direccion as cliente_direccion_completa,
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados
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
            
            # Combinar fecha y hora
            if venta.get('fecha_dia') and venta.get('fecha_hora'):
                try:
                    fecha_obj = venta['fecha_dia']
                    hora_str = str(venta['fecha_hora'])
                    if isinstance(fecha_obj, date):
                        hora_partes = hora_str.split(':')
                        hora = int(hora_partes[0]) if len(hora_partes) > 0 else 0
                        minuto = int(hora_partes[1]) if len(hora_partes) > 1 else 0
                        segundo = int(hora_partes[2]) if len(hora_partes) > 2 else 0
                        fecha_datetime = datetime(
                            fecha_obj.year, fecha_obj.month, fecha_obj.day,
                            hora, minuto, segundo
                        )
                        venta['fecha_completa'] = fecha_datetime
                except Exception:
                    venta['fecha_completa'] = venta['fecha_dia']
            else:
                venta['fecha_completa'] = venta['fecha_dia']
            
            # Crédito
            credito_query = """
                SELECT 
                    cr.estado as estado_credito,
                    cr.anticipo as anticipo_credito,
                    cr.abonos_realizados as abonos_credito,
                    cr.saldo_pendiente as saldo_pendiente_credito,
                    cr.deuda_inicial as deuda_inicial_credito,
                    cr.fecha_inicio as fecha_inicio_credito,
                    cr.fecha_vencimiento as fecha_vencimiento_credito,
                    cr.dias_credito as dias_credito_credito
                FROM creditos cr
                WHERE cr.venta_id = %s
                LIMIT 1
            """
            cursor.execute(credito_query, (venta_id,))
            credito = cursor.fetchone()
            if credito:
                venta.update(credito)
            
            # Ventas mixtas
            venta_mixta_query = """
                SELECT COUNT(*) as total
                FROM ventas_mixtas 
                WHERE id_venta = %s
            """
            cursor.execute(venta_mixta_query, (venta_id,))
            venta_mixta = cursor.fetchone()
            venta['es_mixta'] = venta_mixta['total'] > 0 if venta_mixta else False
            
            if venta['es_mixta']:
                detalle_mixta_query = """
                    SELECT 
                        categoria,
                        metodo_pago,
                        submetodo,
                        monto
                    FROM ventas_mixtas
                    WHERE id_venta = %s
                    ORDER BY categoria, metodo_pago
                """
                cursor.execute(detalle_mixta_query, (venta_id,))
                venta['detalles_mixtos'] = cursor.fetchall()
            
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
                    dv.precio_neto as subtotal,
                    p.precio_costo,
                    p.precio_venta,
                    (dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida as utilidad_producto
                FROM detalle_venta dv
                JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
            """
            cursor.execute(producto_query, (venta_id,))
            productos = cursor.fetchall()
            
            utilidad_total = 0
            costo_total = 0
            
            for producto in productos:
                precio_unidad = float(producto.get('precio_unitario', 0))
                precio_costo = float(producto.get('precio_costo', 0))
                cantidad = int(producto.get('cantidad', 0))
                
                utilidad_producto = (precio_unidad - precio_costo) * cantidad
                producto['utilidad_producto'] = utilidad_producto
                
                utilidad_total += utilidad_producto
                costo_total += precio_costo * cantidad
            
            venta['productos'] = productos
            venta['utilidad'] = utilidad_total
            venta['costo_total'] = costo_total
            
            if venta['es_mixta']:
                venta['utilidad_realizada'] = utilidad_total
                venta['utilidad_proyectada'] = 0
            elif venta.get('tipo_pago') == 'CRÉDITO':
                if venta.get('estado_credito') == 'pagado':
                    venta['utilidad_realizada'] = utilidad_total
                    venta['utilidad_proyectada'] = 0
                else:
                    venta['utilidad_realizada'] = 0
                    venta['utilidad_proyectada'] = utilidad_total
            else:
                venta['utilidad_realizada'] = utilidad_total
                venta['utilidad_proyectada'] = 0
            
            cursor.close()
            conn.close()
            
            venta = convertir_para_json(venta)
            
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

    # ============================================================
    #  OBTENER CLIENTES PARA FILTRO (CORREGIDO)
    # ============================================================
    @staticmethod
    def obtener_clientes_para_filtro():
        """Obtener lista de clientes para el filtro"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Clientes registrados
            cursor.execute("""
                SELECT CAST(cedula AS CHAR) AS id,
                       CAST(nombre AS CHAR) AS nombre,
                       CAST(telefono AS CHAR) AS telefono,
                       'cliente' AS tipo
                FROM cliente
                WHERE nombre IS NOT NULL AND TRIM(CAST(nombre AS CHAR)) != ''
            """)
            clientes = cursor.fetchall()
            
            # Clientes finales (de ventas sin cédula)
            cursor.execute("""
                SELECT CONCAT('final|', REPLACE(TRIM(CAST(nombre_cliente AS CHAR)), '|', ' '), '|', COALESCE(TRIM(CAST(telefono_cliente AS CHAR)), '')) AS id,
                       TRIM(CAST(nombre_cliente AS CHAR)) AS nombre,
                       TRIM(CAST(telefono_cliente AS CHAR)) AS telefono,
                       'cliente_final' AS tipo
                FROM ventas
                WHERE TRIM(COALESCE(CAST(nombre_cliente AS CHAR), '')) != ''
                  AND (
                      TRIM(COALESCE(CAST(cliente_cedula AS CHAR), '')) = ''
                      OR TRIM(COALESCE(CAST(cliente_cedula AS CHAR), '')) = 'final'
                      OR LOWER(TRIM(COALESCE(CAST(cliente_cedula AS CHAR), ''))) = 'cliente final'
                  )
            """)
            clientes_finales = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            # Combinar y eliminar duplicados
            todos = []
            vistos = set()
            
            for c in clientes + clientes_finales:
                nombre = c.get('nombre') or ''
                key = normalizar_texto(nombre)
                if key and key not in vistos:
                    vistos.add(key)
                    todos.append({
                        'id': str(c.get('id') or ''),
                        'nombre': nombre,
                        'telefono': c.get('telefono') or '',
                        'tipo': c.get('tipo') or 'cliente'
                    })
            
            todos = sorted(todos, key=lambda x: normalizar_texto(x.get('nombre', '')))
            todos = convertir_para_json(todos)
            
            return {
                'success': True,
                'usuarios': todos
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo clientes para filtro: {e}")
            return {
                'success': False,
                'error': str(e),
                'usuarios': []
            }

    # ============================================================
    #  OBTENER PRODUCTOS PARA FILTRO
    # ============================================================
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
                    presentacion,
                    precio_costo,
                    precio_venta
                FROM productos
                WHERE cantidad >= 0
                ORDER BY nombre
            """
            
            cursor.execute(query)
            productos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
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

    # ============================================================
    #  OBTENER VENTAS RECIENTES
    # ============================================================
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
                    DATE(v.fecha_dia) as fecha_dia,
                    TIME(v.fecha_hora) as fecha_hora,
                    v.nombre_cliente,
                    v.tipo_pago,
                    v.total,
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados
                FROM ventas v
                ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
                LIMIT %s
            """
            
            cursor.execute(query, (limit,))
            ventas = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
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

    # ============================================================
    #  OBTENER ESTADÍSTICAS FINANCIERAS
    # ============================================================
    @staticmethod
    def obtener_estadisticas_financieras(fecha_inicio=None, fecha_fin=None, hora_inicio=None, hora_fin=None):
        """Obtener estadísticas financieras completas"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            where_parts = []
            params = []
            
            if fecha_inicio and fecha_fin:
                where_parts.append("v.fecha_dia BETWEEN %s AND %s")
                params.extend([fecha_inicio, fecha_fin])
            elif fecha_inicio:
                where_parts.append("v.fecha_dia >= %s")
                params.append(fecha_inicio)
            elif fecha_fin:
                where_parts.append("v.fecha_dia <= %s")
                params.append(fecha_fin)
            
            if hora_inicio:
                where_parts.append("TIME(v.fecha_hora) >= %s")
                params.append(hora_inicio)
            if hora_fin:
                where_parts.append("TIME(v.fecha_hora) <= %s")
                params.append(hora_fin)
            
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"
            
            # Ingresos cobrados
            query_ingresos = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN v.tipo_pago != 'CRÉDITO' THEN v.total ELSE 0 END), 0) as ventas_contado,
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.anticipo, 0) ELSE 0 END), 0) as anticipos_cobrados,
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.abonos_realizados, 0) ELSE 0 END), 0) as abonos_cobrados,
                    COUNT(DISTINCT v.id) as total_ventas
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
            """
            cursor.execute(query_ingresos, params)
            ingresos = cursor.fetchone()
            
            # Créditos pendientes
            query_creditos = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN v.total ELSE 0 END), 0) as total_credito_vendido,
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.anticipo, 0) + COALESCE(c.abonos_realizados, 0) ELSE 0 END), 0) as credito_ya_pagado,
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN COALESCE(c.saldo_pendiente, 0) ELSE 0 END), 0) as credito_faltante,
                    COUNT(DISTINCT CASE WHEN v.tipo_pago = 'CRÉDITO' AND c.estado IN ('pendiente', 'vencido') THEN c.id END) as creditos_pendientes_count
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
            """
            cursor.execute(query_creditos, params)
            creditos = cursor.fetchone()
            
            # Estado de créditos
            query_estado = f"""
                SELECT 
                    COALESCE(SUM(CASE WHEN c.estado = 'vencido' THEN c.saldo_pendiente ELSE 0 END), 0) as creditos_vencidos,
                    COALESCE(SUM(CASE WHEN c.estado = 'pendiente' THEN c.saldo_pendiente ELSE 0 END), 0) as creditos_en_fecha
                FROM creditos c
                JOIN ventas v ON c.venta_id = v.id
                WHERE {where_clause}
            """
            cursor.execute(query_estado, params)
            estado = cursor.fetchone()
            
            # Utilidad realizada
            query_utilidad = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago != 'CRÉDITO' THEN 
                                (SELECT SUM((dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida)
                                 FROM detalle_venta dv
                                 JOIN productos p ON dv.id_producto = p.id
                                 WHERE dv.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_contado,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado = 'pagado' THEN 
                                (SELECT SUM((dv.precio_unidad - p.precio_costo) * dv.cantidad_vendida)
                                 FROM detalle_venta dv
                                 JOIN productos p ON dv.id_producto = p.id
                                 WHERE dv.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as utilidad_creditos_pagados
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
            """
            cursor.execute(query_utilidad, params)
            utilidad = cursor.fetchone()
            
            # Utilidad proyectada
            query_proyectada = f"""
                SELECT 
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado != 'pagado' THEN v.total
                            ELSE 0
                        END
                    ), 0) as valor_ventas_pendientes,
                    COALESCE(SUM(
                        CASE 
                            WHEN v.tipo_pago = 'CRÉDITO' AND c.estado != 'pagado' THEN 
                                (SELECT SUM(p.precio_costo * dv.cantidad_vendida)
                                 FROM detalle_venta dv
                                 JOIN productos p ON dv.id_producto = p.id
                                 WHERE dv.id_venta = v.id)
                            ELSE 0
                        END
                    ), 0) as costo_ventas_pendientes
                FROM ventas v
                LEFT JOIN creditos c ON v.id = c.venta_id
                WHERE {where_clause}
            """
            cursor.execute(query_proyectada, params)
            proyectada = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            # Construir resultado
            estadisticas = {
                'ventas_contado': float(ingresos.get('ventas_contado', 0)),
                'anticipos_cobrados': float(ingresos.get('anticipos_cobrados', 0)),
                'abonos_cobrados': float(ingresos.get('abonos_cobrados', 0)),
                'total_ventas': int(ingresos.get('total_ventas', 0)),
                'total_credito_vendido': float(creditos.get('total_credito_vendido', 0)),
                'credito_ya_pagado': float(creditos.get('credito_ya_pagado', 0)),
                'credito_faltante': float(creditos.get('credito_faltante', 0)),
                'ventas_credito_pendientes': float(creditos.get('credito_faltante', 0)),
                'creditos_pendientes_count': int(creditos.get('creditos_pendientes_count', 0)),
                'creditos_vencidos': float(estado.get('creditos_vencidos', 0)),
                'creditos_en_fecha': float(estado.get('creditos_en_fecha', 0)),
                'saldo_por_cobrar': float(creditos.get('credito_faltante', 0)),
                'utilidad_realizada': float(utilidad.get('utilidad_contado', 0)) + float(utilidad.get('utilidad_creditos_pagados', 0)),
                'utilidad_contado': float(utilidad.get('utilidad_contado', 0)),
                'utilidad_creditos_pagados': float(utilidad.get('utilidad_creditos_pagados', 0)),
                'utilidad_proyectada': float(proyectada.get('valor_ventas_pendientes', 0)) - float(proyectada.get('costo_ventas_pendientes', 0)),
                'valor_ventas_pendientes': float(proyectada.get('valor_ventas_pendientes', 0)),
                'costo_ventas_pendientes': float(proyectada.get('costo_ventas_pendientes', 0))
            }
            
            estadisticas = convertir_para_json(estadisticas)
            
            return {
                'success': True,
                'estadisticas': estadisticas
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas financieras: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'estadisticas': {}
            }

    # ============================================================
    #  ESTADÍSTICAS FINANCIERAS POR PERÍODO RÁPIDO
    # ============================================================
    @staticmethod
    def obtener_estadisticas_financieras_periodo_rapido(periodo, hora_inicio=None, hora_fin=None):
        """Obtener estadísticas financieras para períodos rápidos"""
        try:
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
                fecha_inicio = hoy.date()
                fecha_fin = hoy.date()
            
            return HistorialVentaModel.obtener_estadisticas_financieras(
                fecha_inicio=str(fecha_inicio),
                fecha_fin=str(fecha_fin),
                hora_inicio=hora_inicio,
                hora_fin=hora_fin
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas financieras para período rápido: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    # ============================================================
    #  VERIFICAR VENTA PARA ELIMINAR
    # ============================================================
    @staticmethod
    def verificar_venta_para_eliminar(venta_id):
        """Verificar información de una venta antes de eliminarla"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    v.id,
                    v.numero_venta,
                    v.tipo_pago,
                    v.fecha_dia,
                    v.nombre_cliente,
                    v.total,
                    DATEDIFF(CURDATE(), v.fecha_dia) as dias_pasados,
                    COUNT(DISTINCT dv.id) as productos_count,
                    COALESCE(MAX(c.id), 0) as credito_id,
                    COUNT(DISTINCT vm.id) as ventas_mixtas_count
                FROM ventas v
                LEFT JOIN detalle_venta dv ON v.id = dv.id_venta
                LEFT JOIN creditos c ON v.id = c.venta_id
                LEFT JOIN ventas_mixtas vm ON v.id = vm.id_venta
                WHERE v.id = %s
                GROUP BY v.id
            """
            
            cursor.execute(query, (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'error': 'Venta no encontrada'
                }
            
            cursor.close()
            conn.close()
            
            venta = convertir_para_json(venta)
            
            puede_recuperar_productos = venta.get('dias_pasados', 0) <= 7
            
            return {
                'success': True,
                'puede_eliminar': True,
                'puede_recuperar_productos': puede_recuperar_productos,
                'venta': {
                    'id': venta_id,
                    'numero_venta': venta.get('numero_venta'),
                    'tipo_pago': venta.get('tipo_pago'),
                    'fecha': venta.get('fecha_dia'),
                    'dias_pasados': venta.get('dias_pasados', 0),
                    'cliente': venta.get('nombre_cliente', 'CLIENTE FINAL'),
                    'total': float(venta.get('total', 0)),
                    'productos_count': venta.get('productos_count', 0),
                    'es_credito': venta.get('tipo_pago') == 'CRÉDITO',
                    'es_mixta': venta.get('ventas_mixtas_count', 0) > 0,
                    'tiene_credito': venta.get('credito_id') is not None,
                    'puede_recuperar_productos': puede_recuperar_productos
                },
                'advertencias': [],
                'mensaje': 'Esta acción eliminará permanentemente la venta y todos sus registros relacionados.'
            }
            
        except Exception as e:
            logger.error(f"Error verificando venta {venta_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'puede_eliminar': False
            }

    # ============================================================
    #  ELIMINAR VENTA COMPLETA
    # ============================================================
    @staticmethod
    def eliminar_venta_completa(venta_id, recuperar_productos=False):
        """Eliminar una venta con opción de recuperar productos al inventario"""
        try:
            conn = db.get_connection()
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            
            # Verificar que existe
            cursor.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
            venta = cursor.fetchone()
            if not venta:
                conn.rollback()
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Venta no encontrada'}
            
            productos_recuperados = []
            
            # Recuperar productos si se solicita
            if recuperar_productos:
                cursor.execute("""
                    SELECT dv.id_producto, dv.cantidad_vendida, p.nombre, p.cantidad as stock_actual
                    FROM detalle_venta dv
                    JOIN productos p ON dv.id_producto = p.id
                    WHERE dv.id_venta = %s
                """, (venta_id,))
                productos = cursor.fetchall()
                
                for p in productos:
                    cursor.execute("""
                        UPDATE productos SET cantidad = cantidad + %s WHERE id = %s
                    """, (p['cantidad_vendida'], p['id_producto']))
                    
                    cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (p['id_producto'],))
                    nuevo_stock = cursor.fetchone()
                    
                    productos_recuperados.append({
                        'nombre': p['nombre'],
                        'cantidad_recuperada': p['cantidad_vendida'],
                        'stock_anterior': p['stock_actual'],
                        'stock_nuevo': nuevo_stock['cantidad'] if nuevo_stock else 0,
                        'actualizado': True
                    })
            
            # Eliminar registros relacionados
            cursor.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (venta_id,))
            cursor.execute("DELETE FROM ventas_mixtas WHERE id_venta = %s", (venta_id,))
            cursor.execute("DELETE FROM creditos WHERE venta_id = %s", (venta_id,))
            cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': f'Venta #{venta_id} eliminada exitosamente',
                'detalles': {
                    'productos_recuperados': productos_recuperados,
                    'recuperar_productos': recuperar_productos
                }
            }
            
        except Exception as e:
            logger.error(f"Error eliminando venta: {e}", exc_info=True)
            try:
                conn.rollback()
            except:
                pass
            return {
                'success': False,
                'error': str(e)
            }

    # ============================================================
    #  ELIMINAR VENTAS MÚLTIPLES
    # ============================================================
    @staticmethod
    def eliminar_ventas_multiples(ventas_ids, recuperar_productos=False):
        """Eliminar múltiples ventas en una sola transacción"""
        try:
            conn = db.get_connection()
            conn.start_transaction()
            cursor = conn.cursor(dictionary=True)
            
            resultados = {
                'eliminadas': 0,
                'detalles_eliminados': 0,
                'creditos_eliminados': 0,
                'ventas_mixtas_eliminadas': 0,
                'productos_recuperados': [],
                'errores': []
            }
            
            for venta_id in ventas_ids:
                try:
                    # Verificar que existe
                    cursor.execute("SELECT * FROM ventas WHERE id = %s", (venta_id,))
                    venta = cursor.fetchone()
                    if not venta:
                        resultados['errores'].append(f'Venta {venta_id} no encontrada')
                        continue
                    
                    # Recuperar productos
                    if recuperar_productos:
                        cursor.execute("""
                            SELECT dv.id_producto, dv.cantidad_vendida, p.nombre, p.cantidad as stock_actual
                            FROM detalle_venta dv
                            JOIN productos p ON dv.id_producto = p.id
                            WHERE dv.id_venta = %s
                        """, (venta_id,))
                        productos = cursor.fetchall()
                        
                        for p in productos:
                            cursor.execute("""
                                UPDATE productos SET cantidad = cantidad + %s WHERE id = %s
                            """, (p['cantidad_vendida'], p['id_producto']))
                            
                            cursor.execute("SELECT cantidad FROM productos WHERE id = %s", (p['id_producto'],))
                            nuevo_stock = cursor.fetchone()
                            
                            resultados['productos_recuperados'].append({
                                'venta_id': venta_id,
                                'nombre': p['nombre'],
                                'cantidad': p['cantidad_vendida'],
                                'stock_anterior': p['stock_actual'],
                                'stock_nuevo': nuevo_stock['cantidad'] if nuevo_stock else 0,
                                'actualizado': True
                            })
                    
                    cursor.execute("DELETE FROM detalle_venta WHERE id_venta = %s", (venta_id,))
                    resultados['detalles_eliminados'] += cursor.rowcount
                    
                    cursor.execute("DELETE FROM ventas_mixtas WHERE id_venta = %s", (venta_id,))
                    resultados['ventas_mixtas_eliminadas'] += cursor.rowcount
                    
                    cursor.execute("DELETE FROM creditos WHERE venta_id = %s", (venta_id,))
                    if cursor.rowcount > 0:
                        resultados['creditos_eliminados'] += 1
                    
                    cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
                    if cursor.rowcount > 0:
                        resultados['eliminadas'] += 1
                    
                except Exception as e:
                    resultados['errores'].append(f'Error en venta {venta_id}: {str(e)}')
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'eliminadas': resultados['eliminadas'],
                'message': f'{resultados["eliminadas"]} ventas eliminadas',
                'detalles': resultados
            }
            
        except Exception as e:
            logger.error(f"Error en eliminación múltiple: {e}", exc_info=True)
            try:
                conn.rollback()
            except:
                pass
            return {
                'success': False,
                'error': str(e),
                'eliminadas': 0
            }

    # ============================================================
    #  NUEVO: OBTENER TENDENCIA DE VENTAS (CORREGIDO)
    # ============================================================
    @staticmethod
    def obtener_tendencia_ventas(fecha_inicio=None, fecha_fin=None, dias=7):
        """Obtener tendencia de ventas para el gráfico"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Si no hay fechas, usar los últimos 'dias' días
            if not fecha_inicio and not fecha_fin:
                hoy = datetime.now().date()
                fecha_fin = str(hoy)
                fecha_inicio = str(hoy - timedelta(days=dias - 1))
            elif fecha_inicio and not fecha_fin:
                # Si solo hay fecha_inicio, usar días desde esa fecha
                fecha_fin = str(datetime.now().date())
            elif not fecha_inicio and fecha_fin:
                # Si solo hay fecha_fin, usar días hacia atrás
                fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                fecha_inicio = str(fecha_fin_obj - timedelta(days=dias - 1))
            
            query = """
                SELECT 
                    fecha_dia,
                    COUNT(*) as cantidad_ventas,
                    COALESCE(SUM(total), 0) as total_dia
                FROM ventas
                WHERE fecha_dia BETWEEN %s AND %s
                GROUP BY fecha_dia
                ORDER BY fecha_dia
            """
            
            cursor.execute(query, (fecha_inicio, fecha_fin))
            tendencia = cursor.fetchall()
            
            # Si no hay datos en el rango, generar días vacíos
            if not tendencia:
                from datetime import timedelta
                start = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                end = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                
                current = start
                while current <= end:
                    tendencia.append({
                        'fecha_dia': str(current),
                        'cantidad_ventas': 0,
                        'total_dia': 0
                    })
                    current += timedelta(days=1)
            else:
                # Completar días faltantes en el rango
                from datetime import timedelta
                start = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                end = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                
                # Crear diccionario con los datos existentes
                datos_dict = {str(item['fecha_dia']): item for item in tendencia}
                
                # Completar días faltantes
                tendencia_completa = []
                current = start
                while current <= end:
                    fecha_str = str(current)
                    if fecha_str in datos_dict:
                        tendencia_completa.append(datos_dict[fecha_str])
                    else:
                        tendencia_completa.append({
                            'fecha_dia': fecha_str,
                            'cantidad_ventas': 0,
                            'total_dia': 0
                        })
                    current += timedelta(days=1)
                
                tendencia = tendencia_completa
            
            cursor.close()
            conn.close()
            
            tendencia = convertir_para_json(tendencia)
            
            logger.info(f"Tendencia obtenida: {len(tendencia)} días entre {fecha_inicio} y {fecha_fin}")
            
            return {
                'success': True,
                'tendencia': tendencia
            }
            
        except Exception as e:
            logger.error(f"Error en obtener_tendencia_ventas: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'tendencia': []
            }


# Instancia global del modelo
model = HistorialVentaModel()