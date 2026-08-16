"""
Modelo para gestión de clientes y proveedores - VERSIÓN COMPLETA CORREGIDA
con soporte para facturación de créditos y abonos
"""
from database import db
import logging
from datetime import datetime, date, timedelta
import decimal

logger = logging.getLogger(__name__)

# ===== FUNCIONES DE SERIALIZACIÓN =====

def convertir_a_serializable(obj):
    """Convertir objetos datetime/timedelta a strings serializables"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return str(obj)
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif hasattr(obj, 'isoformat'):  # Para otros objetos con isoformat
        return obj.isoformat()
    return obj

def serializar_datos(datos):
    """Recursivamente serializar datos para JSON"""
    if isinstance(datos, dict):
        return {k: serializar_datos(v) for k, v in datos.items()}
    elif isinstance(datos, list):
        return [serializar_datos(v) for v in datos]
    else:
        return convertir_a_serializable(datos)

class ClienteProveedorModel:
    
    # ===== MÉTODOS PARA CLIENTES =====
    
    @staticmethod
    def obtener_clientes(busqueda="", estado=None, deuda=None, limit=10, offset=0):
        """Obtener clientes con filtros"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Base de la consulta - usar subconsultas para evitar producto cartesiano
            sql = """
            SELECT c.*,
                   COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) as deuda_total,
                   COALESCE((SELECT COUNT(*) FROM ventas WHERE cliente_cedula = c.cedula), 0) as total_ventas,
                   COALESCE((SELECT SUM(total) FROM ventas WHERE cliente_cedula = c.cedula), 0) as monto_total_ventas,
                   CASE 
                       WHEN COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) = 0 THEN 'activo'
                       WHEN COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) > 50000 THEN 'moroso'
                       ELSE 'activo'
                   END as estado_actual
            FROM cliente c
            WHERE 1=1
            """
            
            params = []
            
            # Búsqueda por texto
            if busqueda:
                sql += " AND (c.nombre LIKE %s OR c.cedula LIKE %s OR c.telefono LIKE %s)"
                like_busqueda = f"%{busqueda}%"
                params.extend([like_busqueda, like_busqueda, like_busqueda])
            
            # Agregar filtros por deuda DIRECTAMENTE (sin GROUP BY)
            if deuda == "sin":
                sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) = 0"
            elif deuda == "pequena":
                sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) > 0 AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) < 50000"
            elif deuda == "grande":
                sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) >= 50000"
            
            # Filtro por estado
            if estado == "activo":
                sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) = 0"
            elif estado == "moroso":
                sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) > 50000"
            
            sql += " ORDER BY c.nombre LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            clientes = cursor.fetchall()
            
            # Serializar los datos
            clientes = serializar_datos(clientes)
            
            # Obtener total para paginación
            count_sql = "SELECT COUNT(*) as total FROM cliente c WHERE 1=1"
            count_params = []
            
            if busqueda:
                count_sql += " AND (c.nombre LIKE %s OR c.cedula LIKE %s OR c.telefono LIKE %s)"
                like_busqueda = f"%{busqueda}%"
                count_params.extend([like_busqueda, like_busqueda, like_busqueda])
            
            if deuda == "sin":
                count_sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) = 0"
            elif deuda == "pequena":
                count_sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) > 0 AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) < 50000"
            elif deuda == "grande":
                count_sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) >= 50000"
            
            if estado == "activo":
                count_sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) = 0"
            elif estado == "moroso":
                count_sql += " AND COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) > 50000"
            
            cursor.execute(count_sql, count_params)
            total = cursor.fetchone()['total']
            
            logger.info(f"Encontrados {len(clientes)} clientes (total: {total})")
            
            return {
                'clientes': clientes,
                'total': total
            }
            
        except Exception as e:
            logger.error(f"Error en obtener_clientes: {str(e)}")
            return {'clientes': [], 'total': 0}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_estadisticas_globales():
        """Obtener estadísticas globales de clientes y deuda"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT COUNT(*) AS total_clientes FROM cliente")
            total_clientes = cursor.fetchone().get('total_clientes', 0)
            
            cursor.execute("SELECT COALESCE(SUM(saldo_pendiente), 0) AS deuda_total FROM creditos WHERE estado = 'pendiente'")
            deuda_total = float(cursor.fetchone().get('deuda_total', 0) or 0)
            
            cursor.execute("SELECT COUNT(DISTINCT cliente_cedula) AS clientes_morosos FROM creditos WHERE estado = 'pendiente' GROUP BY cliente_cedula HAVING SUM(saldo_pendiente) >= 50000")
            morosos_rows = cursor.fetchall()
            clientes_morosos = len(morosos_rows)
            
            return {
                'total_clientes': total_clientes,
                'deuda_total': deuda_total,
                'clientes_morosos': clientes_morosos
            }
        except Exception as e:
            logger.error(f"Error en obtener_estadisticas_globales: {str(e)}")
            return {
                'total_clientes': 0,
                'deuda_total': 0,
                'clientes_morosos': 0
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_estadisticas_globales():
        """Obtener estadísticas globales de clientes y deuda"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT COUNT(*) AS total_clientes FROM cliente")
            total_clientes = cursor.fetchone().get('total_clientes', 0)
            
            cursor.execute("SELECT COALESCE(SUM(saldo_pendiente), 0) AS deuda_total FROM creditos WHERE estado = 'pendiente'")
            deuda_total = float(cursor.fetchone().get('deuda_total', 0) or 0)
            
            cursor.execute("SELECT COUNT(DISTINCT cliente_cedula) AS clientes_morosos FROM creditos WHERE estado = 'pendiente' GROUP BY cliente_cedula HAVING SUM(saldo_pendiente) >= 50000")
            morosos_rows = cursor.fetchall()
            clientes_morosos = len(morosos_rows)
            
            return {
                'total_clientes': total_clientes,
                'deuda_total': deuda_total,
                'clientes_morosos': clientes_morosos
            }
        except Exception as e:
            logger.error(f"Error en obtener_estadisticas_globales: {str(e)}")
            return {
                'total_clientes': 0,
                'deuda_total': 0,
                'clientes_morosos': 0
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_cliente_por_cedula(cedula):
        """Obtener cliente por cédula con datos completos"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT c.*,
                   COALESCE((SELECT SUM(saldo_pendiente) FROM creditos WHERE cliente_cedula = c.cedula AND estado = 'pendiente'), 0) as deuda_total,
                   COALESCE((SELECT COUNT(*) FROM ventas WHERE cliente_cedula = c.cedula), 0) as total_ventas,
                   COALESCE((SELECT SUM(total) FROM ventas WHERE cliente_cedula = c.cedula), 0) as monto_total_ventas
            FROM cliente c
            WHERE c.cedula = %s
            """
            
            cursor.execute(sql, (cedula,))
            cliente = cursor.fetchone()
            
            if cliente:
                cliente = serializar_datos(cliente)
            
            return cliente
            
        except Exception as e:
            logger.error(f"Error en obtener_cliente_por_cedula: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear_cliente(cedula, nombre, telefono=None, correo=None, direccion=None):
        """Crear un nuevo cliente - versión simplificada"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            sql = """
            INSERT INTO cliente (cedula, nombre, telefono, correo, direccion)
            VALUES (%s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (cedula, nombre, telefono, correo, direccion))
            conn.commit()
            
            logger.info(f"Cliente creado: {cedula} - {nombre}")
            return True, "Cliente creado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al crear cliente: {error_msg}")
            if "Duplicate entry" in error_msg:
                return False, "Ya existe un cliente con esta cédula"
            return False, f"Error al crear cliente: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            
    @staticmethod
    def actualizar_cliente(cedula_original, cedula, nombre, telefono, correo, direccion, fecha_creacion=None):
        """Actualizar información de un cliente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Si no se proporciona fecha_creacion, mantener la existente
            if fecha_creacion is None:
                sql = """
                UPDATE cliente 
                SET cedula = %s, nombre = %s, telefono = %s, correo = %s, direccion = %s
                WHERE cedula = %s
                """
                cursor.execute(sql, (cedula, nombre, telefono, correo, direccion, cedula_original))
            else:
                sql = """
                UPDATE cliente 
                SET cedula = %s, nombre = %s, telefono = %s, correo = %s, direccion = %s, fecha_creacion = %s
                WHERE cedula = %s
                """
                cursor.execute(sql, (cedula, nombre, telefono, correo, direccion, fecha_creacion, cedula_original))
            
            conn.commit()
            
            # Actualizar también en ventas si cambió la cédula
            if cedula != cedula_original:
                update_ventas_sql = """
                UPDATE ventas SET cliente_cedula = %s WHERE cliente_cedula = %s
                """
                cursor.execute(update_ventas_sql, (cedula, cedula_original))
                
                update_creditos_sql = """
                UPDATE creditos SET cliente_cedula = %s WHERE cliente_cedula = %s
                """
                cursor.execute(update_creditos_sql, (cedula, cedula_original))
                
                conn.commit()
            
            logger.info(f"Cliente actualizado: {cedula_original} -> {cedula}")
            return True, "Cliente actualizado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al actualizar cliente: {error_msg}")
            if "Duplicate entry" in error_msg:
                return False, "Ya existe un cliente con esta nueva cédula"
            return False, f"Error al actualizar cliente: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def eliminar_cliente(cedula):
        """Eliminar un cliente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Verificar si tiene ventas asociadas
            cursor.execute("SELECT COUNT(*) as total FROM ventas WHERE cliente_cedula = %s", (cedula,))
            ventas = cursor.fetchone()[0]
            
            if ventas > 0:
                logger.warning(f"No se puede eliminar cliente {cedula} - Tiene {ventas} ventas asociadas")
                return False, "No se puede eliminar el cliente porque tiene ventas asociadas"
            
            # Verificar si tiene créditos pendientes
            cursor.execute("SELECT COUNT(*) as total FROM creditos WHERE cliente_cedula = %s AND estado = 'pendiente'", (cedula,))
            creditos = cursor.fetchone()[0]
            
            if creditos > 0:
                logger.warning(f"No se puede eliminar cliente {cedula} - Tiene {creditos} créditos pendientes")
                return False, "No se puede eliminar el cliente porque tiene créditos pendientes"
            
            # Eliminar cliente
            sql = "DELETE FROM cliente WHERE cedula = %s"
            cursor.execute(sql, (cedula,))
            conn.commit()
            
            logger.info(f"Cliente eliminado: {cedula}")
            return True, "Cliente eliminado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al eliminar cliente {cedula}: {str(e)}")
            return False, f"Error al eliminar cliente: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_historial_cliente(cedula):
        """Obtener historial completo de un cliente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Primero verificar que el cliente existe
            sql_cliente = "SELECT * FROM cliente WHERE cedula = %s"
            cursor.execute(sql_cliente, (cedula,))
            cliente = cursor.fetchone()
            
            if not cliente:
                return None
            
            # Obtener ventas del cliente
            sql_ventas = """
            SELECT 
                v.id,
                v.numero_venta,
                DATE(v.fecha_dia) as fecha_dia,
                TIME(v.fecha_hora) as fecha_hora_str,
                v.nombre_cliente,
                v.tipo_pago,
                v.cliente_cedula,
                v.subtotal,
                v.descuento,
                v.total,
                (SELECT GROUP_CONCAT(p.nombre SEPARATOR ', ') 
                 FROM detalle_venta dv 
                 JOIN productos p ON dv.id_producto = p.id 
                 WHERE dv.id_venta = v.id) as productos,
                (SELECT COUNT(*) FROM detalle_venta dv WHERE dv.id_venta = v.id) as total_productos
            FROM ventas v
            WHERE v.cliente_cedula = %s OR v.nombre_cliente LIKE %s
            ORDER BY v.fecha_dia DESC, v.fecha_hora DESC
            """
            
            cursor.execute(sql_ventas, (cedula, f"%{cliente.get('nombre', '')}%"))
            ventas = cursor.fetchall()
            
            # Obtener créditos del cliente
            sql_creditos = """
            SELECT 
                c.*, 
                v.numero_venta, 
                DATE(v.fecha_dia) as fecha_venta,
                DATE(c.fecha_inicio) as fecha_inicio,
                DATE(c.fecha_vencimiento) as fecha_vencimiento,
                DATE(c.ultimo_pago) as ultimo_pago
            FROM creditos c
            LEFT JOIN ventas v ON c.venta_id = v.id
            WHERE c.cliente_cedula = %s
            ORDER BY v.fecha_dia DESC
            """
            
            cursor.execute(sql_creditos, (cedula,))
            creditos = cursor.fetchall()
            
            # Obtener estadísticas por tipo de pago
            sql_tipos_pago = """
            SELECT 
                v.tipo_pago,
                COUNT(v.id) as cantidad_ventas,
                SUM(v.total) as monto_total,
                SUM(CASE WHEN c.estado = 'pendiente' THEN c.saldo_pendiente ELSE 0 END) as deuda_actual,
                SUM(CASE WHEN c.estado = 'pagado' THEN v.total ELSE 0 END) as monto_pagado
            FROM ventas v
            LEFT JOIN creditos c ON v.id = c.venta_id
            WHERE v.cliente_cedula = %s OR v.nombre_cliente LIKE %s
            GROUP BY v.tipo_pago
            """
            
            cursor.execute(sql_tipos_pago, (cedula, f"%{cliente.get('nombre', '')}%"))
            tipos_pago = cursor.fetchall()
            
            # Calcular deuda total
            sql_deuda = """
            SELECT COALESCE(SUM(saldo_pendiente), 0) as deuda_total 
            FROM creditos 
            WHERE cliente_cedula = %s AND estado = 'pendiente'
            """
            cursor.execute(sql_deuda, (cedula,))
            deuda_result = cursor.fetchone()
            deuda_total = float(deuda_result['deuda_total']) if deuda_result else 0
            
            # Serializar todos los datos
            historial = {
                'cliente': serializar_datos(cliente),
                'ventas': serializar_datos(ventas),
                'creditos': serializar_datos(creditos),
                'tipos_pago': serializar_datos(tipos_pago),
                'resumen': {
                    'total_ventas': len(ventas),
                    'monto_total': sum(float(v['total']) for v in ventas) if ventas else 0,
                    'total_creditos': len(creditos),
                    'deuda_total': deuda_total
                }
            }
            
            return historial
            
        except Exception as e:
            logger.error(f"Error en obtener_historial_cliente: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ===== MÉTODOS PARA VENTAS MANUALES =====
    
    @staticmethod
    def crear_venta_manual_cliente(cedula, fecha, productos, total, anticipo=0, dias_credito=30, observaciones=''):
        """Crear una venta manual a crédito para un cliente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 1. Verificar que el cliente existe
            cursor.execute("SELECT nombre FROM cliente WHERE cedula = %s", (cedula,))
            cliente_result = cursor.fetchone()
            
            if not cliente_result:
                return False, "Cliente no encontrado"
            
            cliente_nombre = cliente_result[0]
            
            # 2. Obtener el siguiente número de venta
            cursor.execute("SELECT COALESCE(MAX(numero_venta), 0) + 1 as next_num FROM ventas")
            next_num = cursor.fetchone()[0]
            
            # 3. Crear la venta
            fecha_venta = datetime.strptime(fecha, '%Y-%m-%d').date()
            hora_actual = datetime.now().time()
            
            sql_venta = """
            INSERT INTO ventas (
                numero_venta, fecha_dia, fecha_hora, nombre_cliente, 
                tipo_pago, cliente_cedula, subtotal, descuento, total,
                dias_credito, estado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql_venta, (
                next_num,
                fecha_venta,
                hora_actual,
                cliente_nombre,
                'credito',
                cedula,
                total,
                0,  # descuento
                total,
                dias_credito,
                'completada'
            ))
            
            venta_id = cursor.lastrowid
            
            # 4. Crear detalles de venta y actualizar inventario
            total_calculado = 0
            
            for producto in productos:
                producto_nombre = producto.get('nombre', '').strip()
                cantidad = int(producto.get('cantidad', 0))
                precio_unitario = float(producto.get('precio_unitario', 0))
                
                if not producto_nombre or cantidad <= 0 or precio_unitario <= 0:
                    continue
                
                # Buscar producto por nombre
                cursor.execute("""
                    SELECT id, cantidad, precio_venta 
                    FROM productos 
                    WHERE nombre LIKE %s 
                    ORDER BY id DESC 
                    LIMIT 1
                """, (f"%{producto_nombre}%",))
                
                producto_db = cursor.fetchone()
                
                if not producto_db:
                    return False, f"Producto no encontrado: {producto_nombre}"
                
                producto_id = producto_db[0]
                stock_actual = producto_db[1]
                precio_db = float(producto_db[2])
                
                # Verificar stock
                if stock_actual < cantidad:
                    return False, f"Stock insuficiente para {producto_nombre}. Disponible: {stock_actual}"
                
                # Usar precio de la base de datos si no se proporcionó
                if precio_unitario <= 0:
                    precio_unitario = precio_db
                
                # Crear detalle de venta
                sql_detalle = """
                INSERT INTO detalle_venta (
                    id_venta, id_producto, fecha_venta, 
                    cantidad_vendida, precio_unidad, precio_neto
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql_detalle, (
                    venta_id,
                    producto_id,
                    fecha_venta,
                    cantidad,
                    precio_unitario,
                    cantidad * precio_unitario
                ))
                
                logger.info(f"Detalle de venta creado: Venta {venta_id}, Producto {producto_id}, Cantidad {cantidad}")
                
                # Actualizar inventario
                cursor.execute("""
                UPDATE productos 
                SET cantidad = cantidad - %s 
                WHERE id = %s
                """, (cantidad, producto_id))
                
                total_calculado += cantidad * precio_unitario
            
            # 5. Crear crédito si hay saldo pendiente
            saldo_pendiente = total - anticipo
            credito_id = None
            
            if saldo_pendiente > 0:
                fecha_inicio = fecha_venta
                fecha_vencimiento = fecha_inicio + timedelta(days=dias_credito)
                
                sql_credito = """
                INSERT INTO creditos (
                    venta_id, cliente_cedula, anticipo, deuda_inicial,
                    saldo_pendiente, dias_credito, fecha_inicio,
                    fecha_vencimiento, estado, observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql_credito, (
                    venta_id,
                    cedula,
                    anticipo,
                    saldo_pendiente,
                    saldo_pendiente,
                    dias_credito,
                    fecha_inicio,
                    fecha_vencimiento,
                    'pendiente',
                    f"Venta manual: {observaciones}"
                ))
                
                credito_id = cursor.lastrowid
            
            # 6. Registrar en reporte_caja si es venta al contado
            if anticipo == total:  # Si se pagó completo
                sql_reporte = """
                INSERT INTO reporte_caja (
                    ingresos, razon_ingreso, fecha_ingreso, categoria
                ) VALUES (%s, %s, %s, %s)
                """
                
                fecha_actual = datetime.now()
                cursor.execute(sql_reporte, (
                    total,
                    f"Venta manual #{venta_id} - Cliente: {cliente_nombre}",
                    fecha_actual,
                    'ventas'
                ))
            
            conn.commit()
            
            logger.info(f"Venta manual creada: Venta #{venta_id} para cliente {cedula}")
            
            return True, {
                'venta_id': venta_id,
                'numero_venta': next_num,
                'credito_id': credito_id
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al crear venta manual: {error_msg}")
            return False, f"Error al crear venta manual: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ===== MÉTODOS PARA ELIMINAR VENTAS Y CRÉDITOS =====
    
    @staticmethod
    def eliminar_venta(venta_id):
        """Eliminar una venta y todo lo relacionado"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Iniciando eliminación de venta {venta_id}")
            
            # 1. Verificar si la venta existe
            cursor.execute("SELECT id, tipo_pago, total, cliente_cedula FROM ventas WHERE id = %s", (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                return False, "Venta no encontrada"
            
            venta_id, tipo_pago, total, cliente_cedula = venta
            
            logger.info(f"Venta encontrada: ID={venta_id}, Tipo={tipo_pago}, Total={total}, Cliente={cliente_cedula}")
            
            # 2. Verificar si tiene crédito asociado
            cursor.execute("SELECT id, estado, saldo_pendiente FROM creditos WHERE venta_id = %s", (venta_id,))
            credito = cursor.fetchone()
            
            if credito:
                credito_id, estado_credito, saldo_pendiente = credito
                logger.info(f"Crédito asociado encontrado: ID={credito_id}, Estado={estado_credito}, Saldo={saldo_pendiente}")
            
            # 3. Si fue una venta a crédito y hay registro de crédito, eliminar el crédito
            if credito:
                cursor.execute("DELETE FROM creditos WHERE venta_id = %s", (venta_id,))
                logger.info(f"Crédito {credito_id} eliminado para venta {venta_id}")
            
            # 4. Eliminar registro de reporte_caja si existe
            cursor.execute("""
                DELETE FROM reporte_caja 
                WHERE razon_ingreso LIKE %s 
                AND ingresos = %s
            """, (f"%Venta #{venta_id}%", float(total)))
            
            rows_affected = cursor.rowcount
            if rows_affected > 0:
                logger.info(f"Registro(s) de reporte_caja eliminado(s) para venta {venta_id}")
            
            # 5. Finalmente eliminar la venta
            cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
            logger.info(f"Venta {venta_id} eliminada")
            
            conn.commit()
            
            mensaje = f"Venta {venta_id} eliminada exitosamente"
            if credito:
                mensaje += f" (incluyendo crédito asociado)"
            
            logger.info(mensaje)
            return True, mensaje
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al eliminar venta {venta_id}: {error_msg}")
            return False, f"Error al eliminar venta: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def eliminar_credito(credito_id):
        """Eliminar un crédito específico"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            logger.info(f"Iniciando eliminación de crédito {credito_id}")
            
            # Verificar si el crédito existe
            cursor.execute("SELECT id, venta_id, estado, saldo_pendiente FROM creditos WHERE id = %s", (credito_id,))
            credito = cursor.fetchone()
            
            if not credito:
                return False, "Crédito no encontrado"
            
            credito_id, venta_id, estado_credito, saldo_pendiente = credito
            
            logger.info(f"Crédito encontrado: ID={credito_id}, Venta={venta_id}, Estado={estado_credito}, Saldo={saldo_pendiente}")
            
            # Verificar el estado del crédito
            if estado_credito != 'pagado' and float(saldo_pendiente) > 0:
                return False, "No se puede eliminar un crédito con saldo pendiente"
            
            # Eliminar el crédito
            cursor.execute("DELETE FROM creditos WHERE id = %s", (credito_id,))
            
            # También eliminar la venta asociada si existe
            if venta_id:
                # Primero eliminar de reporte_caja
                cursor.execute("""
                    SELECT total FROM ventas WHERE id = %s
                """, (venta_id,))
                
                venta_total = cursor.fetchone()
                if venta_total:
                    total = venta_total[0]
                    cursor.execute("""
                        DELETE FROM reporte_caja 
                        WHERE razon_ingreso LIKE %s 
                        AND ingresos = %s
                    """, (f"%Venta #{venta_id}%", float(total)))
                    logger.info(f"Registro de reporte_caja eliminado para venta {venta_id}")
                
                # Eliminar la venta
                cursor.execute("DELETE FROM ventas WHERE id = %s", (venta_id,))
                logger.info(f"Venta {venta_id} eliminada junto con el crédito")
            
            conn.commit()
            
            logger.info(f"Crédito {credito_id} eliminado exitosamente")
            return True, "Crédito eliminado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al eliminar crédito {credito_id}: {error_msg}")
            return False, f"Error al eliminar crédito: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ===== MÉTODOS PARA CRÉDITOS =====
    
    @staticmethod
    def obtener_creditos_cliente(cedula):
        """Obtener todos los créditos de un cliente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT 
                c.*, 
                v.numero_venta, 
                DATE(v.fecha_dia) as fecha_dia, 
                v.total as monto_venta,
                DATE(c.fecha_inicio) as fecha_inicio,
                DATE(c.fecha_vencimiento) as fecha_vencimiento,
                DATE(c.ultimo_pago) as ultimo_pago
            FROM creditos c
            INNER JOIN ventas v ON c.venta_id = v.id
            WHERE c.cliente_cedula = %s
            ORDER BY c.estado, c.fecha_vencimiento
            """
            
            cursor.execute(sql, (cedula,))
            creditos = cursor.fetchall()
            
            creditos = serializar_datos(creditos)
            
            return creditos
            
        except Exception as e:
            logger.error(f"Error en obtener_creditos_cliente: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_credito(credito_id):
        """Obtener información completa de un crédito específico"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT 
                c.*, 
                v.numero_venta, 
                DATE(v.fecha_dia) as fecha_dia,
                v.total as monto_venta,
                DATE(c.fecha_inicio) as fecha_inicio,
                DATE(c.fecha_vencimiento) as fecha_vencimiento,
                DATE(c.ultimo_pago) as ultimo_pago,
                cl.nombre as cliente_nombre,
                cl.cedula as cliente_cedula
            FROM creditos c
            LEFT JOIN ventas v ON c.venta_id = v.id
            LEFT JOIN cliente cl ON c.cliente_cedula = cl.cedula
            WHERE c.id = %s
            """
            
            cursor.execute(sql, (credito_id,))
            credito = cursor.fetchone()
            
            if credito:
                credito = serializar_datos(credito)
            
            return credito
            
        except Exception as e:
            logger.error(f"Error en obtener_credito: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_credito_con_detalle(credito_id):
        """Obtiene información completa de un crédito: cliente, venta y productos"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            # Datos del crédito, cliente y venta - usar LEFT JOIN para que funcione si no hay venta
            sql = """
            SELECT 
                c.*,
                cl.nombre as cliente_nombre,
                cl.telefono as cliente_telefono,
                cl.direccion as cliente_direccion,
                cl.correo as cliente_correo,
                v.numero_venta,
                v.fecha_dia as venta_fecha,
                v.fecha_hora as venta_hora,
                v.total as venta_total,
                v.subtotal as venta_subtotal,
                v.descuento as venta_descuento,
                v.tipo_pago,
                v.nombre_cliente as venta_nombre_cliente,
                v.id as venta_id
            FROM creditos c
            INNER JOIN cliente cl ON c.cliente_cedula = cl.cedula
            LEFT JOIN ventas v ON c.venta_id = v.id
            WHERE c.id = %s
            """
            cursor.execute(sql, (credito_id,))
            credito = cursor.fetchone()
            if not credito:
                return None

            # Productos de la venta - usar LEFT JOIN para que funcione sin productos
            if credito['venta_id']:
                sql_prod = """
                SELECT 
                    dv.cantidad_vendida,
                    dv.precio_unidad,
                    dv.precio_neto,
                    p.nombre as producto_nombre,
                    p.presentacion
                FROM detalle_venta dv
                LEFT JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
                ORDER BY dv.id
                """
                cursor.execute(sql_prod, (credito['venta_id'],))
                productos = cursor.fetchall()
                credito['productos'] = productos if productos else []
            else:
                credito['productos'] = []

            # Serializar
            return serializar_datos(credito)

        except Exception as e:
            logger.error(f"Error en obtener_credito_con_detalle: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def actualizar_credito(credito_id, datos):
        """Actualizar información de un crédito - VERSIÓN CORREGIDA"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # 1. Validar que el crédito existe
            cursor.execute("SELECT id, venta_id FROM creditos WHERE id = %s", (credito_id,))
            credito_existente = cursor.fetchone()
            
            if not credito_existente:
                return False, "Crédito no encontrado"
            
            credito_id_db, venta_id = credito_existente
            
            # 2. Actualizar fecha de la venta si se proporciona fecha_venta
            if 'fecha_venta' in datos and datos['fecha_venta']:
                try:
                    fecha_venta = datos['fecha_venta']
                    if isinstance(fecha_venta, str):
                        fecha_venta = datetime.strptime(fecha_venta, '%Y-%m-%d').date()
                    
                    cursor.execute("""
                        UPDATE ventas 
                        SET fecha_dia = %s
                        WHERE id = %s
                    """, (fecha_venta, venta_id))
                    
                    logger.info(f"Fecha de venta actualizada para venta {venta_id}: {fecha_venta}")
                except Exception as e:
                    logger.warning(f"Error al actualizar fecha de venta: {str(e)}")
            
            # 3. Actualizar el crédito
            sql_update_credito = """
            UPDATE creditos 
            SET anticipo = %s, 
                saldo_pendiente = %s,
                dias_credito = %s,
                fecha_vencimiento = %s,
                estado = %s,
                abonos_realizados = %s,
                ultimo_pago = %s,
                observaciones = %s
            WHERE id = %s
            """
            
            # Preparar valores para la actualización
            anticipo = float(datos.get('anticipo', 0))
            saldo_pendiente = float(datos.get('saldo_pendiente', 0))
            dias_credito = int(datos.get('dias_credito', 30))
            fecha_vencimiento = datos.get('fecha_vencimiento')
            estado = datos.get('estado', 'pendiente')
            abonos_realizados = float(datos.get('abonos_realizados', 0))
            ultimo_pago = datos.get('ultimo_pago')
            observaciones = datos.get('observaciones', '')
            
            # Convertir fechas si es necesario
            if isinstance(fecha_vencimiento, str) and fecha_vencimiento:
                try:
                    fecha_vencimiento = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
                except:
                    pass
            
            if isinstance(ultimo_pago, str) and ultimo_pago:
                try:
                    ultimo_pago = datetime.strptime(ultimo_pago, '%Y-%m-%d').date()
                except:
                    ultimo_pago = None
            
            cursor.execute(sql_update_credito, (
                anticipo,
                saldo_pendiente,
                dias_credito,
                fecha_vencimiento,
                estado,
                abonos_realizados,
                ultimo_pago,
                observaciones,
                credito_id
            ))
            
            conn.commit()
            
            logger.info(f"Crédito {credito_id} actualizado exitosamente")
            return True, "Crédito actualizado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al actualizar crédito {credito_id}: {error_msg}")
            return False, f"Error al actualizar crédito: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def registrar_abono_credito(credito_id, monto_abono, fecha_abono, hora_abono=None, 
                                metodo_pago='efectivo', referencia=None, 
                                usuario_registra=None, observaciones=""):
        """Registrar un abono a un crédito con registro en tabla de abonos"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Obtener crédito actual y datos relacionados
            cursor.execute("""
                SELECT c.saldo_pendiente, c.abonos_realizados, c.venta_id, c.cliente_cedula
                FROM creditos c
                WHERE c.id = %s
            """, (credito_id,))
            credito = cursor.fetchone()
            
            if not credito:
                return False, "Crédito no encontrado"
            
            saldo_pendiente = float(credito[0])
            abonos_realizados = float(credito[1])
            venta_id = credito[2]
            cliente_cedula = credito[3]
            
            nuevo_saldo = saldo_pendiente - monto_abono
            nuevos_abonos = abonos_realizados + monto_abono
            
            if nuevo_saldo < 0:
                return False, "El abono no puede ser mayor al saldo pendiente"
            
            # Determinar estado
            nuevo_estado = 'pagado' if nuevo_saldo <= 0 else 'pendiente'
            
            # Construir fecha y hora para el registro
            fecha_abono_datetime = None
            if isinstance(fecha_abono, str):
                fecha_abono_datetime = datetime.strptime(fecha_abono, '%Y-%m-%d')
            elif isinstance(fecha_abono, date):
                fecha_abono_datetime = fecha_abono
            else:
                fecha_abono_datetime = date.today()
            
            # Si se proporciona hora, combinar con fecha
            if hora_abono:
                try:
                    hora_obj = datetime.strptime(hora_abono, '%H:%M:%S').time()
                    fecha_completa = datetime.combine(fecha_abono_datetime, hora_obj)
                except:
                    fecha_completa = datetime.now()
            else:
                fecha_completa = datetime.now()
            
            # 1. Actualizar crédito
            if hora_abono:
                sql_update = """
                UPDATE creditos 
                SET saldo_pendiente = %s,
                    abonos_realizados = %s,
                    ultimo_pago = %s,
                    ultimo_pago_hora = %s,
                    estado = %s,
                    observaciones = CONCAT(IFNULL(observaciones, ''), ' | Abono: ', %s, ' - ', %s)
                WHERE id = %s
                """
                cursor.execute(sql_update, (
                    nuevo_saldo,
                    nuevos_abonos,
                    fecha_abono_datetime,
                    hora_abono,
                    nuevo_estado,
                    str(monto_abono),
                    observaciones[:50] if observaciones else 'Sin observaciones',
                    credito_id
                ))
            else:
                sql_update = """
                UPDATE creditos 
                SET saldo_pendiente = %s,
                    abonos_realizados = %s,
                    ultimo_pago = %s,
                    estado = %s,
                    observaciones = CONCAT(IFNULL(observaciones, ''), ' | Abono: ', %s, ' - ', %s)
                WHERE id = %s
                """
                cursor.execute(sql_update, (
                    nuevo_saldo,
                    nuevos_abonos,
                    fecha_abono_datetime,
                    nuevo_estado,
                    str(monto_abono),
                    observaciones[:50] if observaciones else 'Sin observaciones',
                    credito_id
                ))
            
            # 2. Insertar registro en tabla abonos
            sql_abono = """
            INSERT INTO abonos (
                credito_id, venta_id, cliente_cedula, monto, 
                fecha, metodo_pago, referencia, usuario_registra, observacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql_abono, (
                credito_id,
                venta_id,
                cliente_cedula,
                monto_abono,
                fecha_completa,
                metodo_pago,
                referencia,
                usuario_registra,
                observaciones
            ))
            
            conn.commit()
            
            logger.info(f"Abono registrado para crédito {credito_id}: {monto_abono} - Método: {metodo_pago}")
            return True, "Abono registrado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al registrar abono para crédito {credito_id}: {str(e)}")
            return False, f"Error al registrar abono: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ===== MÉTODOS PARA PROVEEDORES =====
    
    @staticmethod
    def obtener_proveedores(busqueda="", estado=None, limit=10, offset=0):
        """Obtener proveedores con filtros"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT 
                p.telefono,
                p.nombre_empresa,
                p.nombre_proveedor,
                p.correo,
                p.estado,
                p.producto,
                DATE(p.fecha_registro) as fecha_registro
            FROM proveedor p
            WHERE 1=1
            """
            
            params = []
            
            if busqueda:
                sql += " AND (p.nombre_empresa LIKE %s OR p.nombre_proveedor LIKE %s OR p.telefono LIKE %s OR p.producto LIKE %s)"
                like_busqueda = f"%{busqueda}%"
                params.extend([like_busqueda, like_busqueda, like_busqueda, like_busqueda])
            
            if estado:
                sql += " AND p.estado = %s"
                params.append(estado)
            
            sql += " ORDER BY p.nombre_empresa LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            proveedores = cursor.fetchall()
            
            # Serializar datos
            proveedores = serializar_datos(proveedores)
            
            # Obtener total para paginación
            count_sql = "SELECT COUNT(*) as total FROM proveedor WHERE 1=1"
            count_params = []
            
            if busqueda:
                count_sql += " AND (nombre_empresa LIKE %s OR nombre_proveedor LIKE %s OR telefono LIKE %s OR producto LIKE %s)"
                like_busqueda = f"%{busqueda}%"
                count_params.extend([like_busqueda, like_busqueda, like_busqueda, like_busqueda])
            
            if estado:
                count_sql += " AND estado = %s"
                count_params.append(estado)
            
            cursor.execute(count_sql, count_params)
            total = cursor.fetchone()['total']
            
            logger.info(f"Encontrados {len(proveedores)} proveedores (total: {total})")
            
            return {
                'proveedores': proveedores,
                'total': total
            }
            
        except Exception as e:
            logger.error(f"Error en obtener_proveedores: {str(e)}")
            return {'proveedores': [], 'total': 0}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_proveedor_por_telefono(telefono):
        """Obtener proveedor por teléfono"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT 
                p.telefono,
                p.nombre_empresa,
                p.nombre_proveedor,
                p.correo,
                p.estado,
                p.producto,
                DATE(p.fecha_registro) as fecha_registro
            FROM proveedor p
            WHERE p.telefono = %s
            """
            
            cursor.execute(sql, (telefono,))
            proveedor = cursor.fetchone()
            
            if proveedor:
                proveedor = serializar_datos(proveedor)
            
            return proveedor
            
        except Exception as e:
            logger.error(f"Error en obtener_proveedor_por_telefono: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear_proveedor_con_productos(telefono, nombre_empresa, nombre_proveedor, correo=None, estado='activo', productos=None):
        """Crear un nuevo proveedor con productos asociados"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Si productos es un string (viene del frontend), usarlo directamente
            productos_str = None
            if productos:
                if isinstance(productos, str):
                    productos_str = productos
                elif isinstance(productos, list):
                    # Extraer solo los nombres de los productos
                    nombres_productos = []
                    for p in productos:
                        if isinstance(p, dict) and p.get('nombre'):
                            nombres_productos.append(p['nombre'])
                        elif isinstance(p, str):
                            nombres_productos.append(p)
                    
                    if nombres_productos:
                        productos_str = ", ".join(nombres_productos)
            
            # Crear proveedor
            sql_proveedor = """
            INSERT INTO proveedor (telefono, nombre_empresa, nombre_proveedor, correo, estado, producto, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """
            
            cursor.execute(sql_proveedor, (telefono, nombre_empresa, nombre_proveedor, correo, estado, productos_str))
            
            conn.commit()
            
            logger.info(f"Proveedor creado: {telefono} - {nombre_empresa}")
            return True, "Proveedor creado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al crear proveedor: {error_msg}")
            if "Duplicate entry" in error_msg:
                return False, "Ya existe un proveedor con este teléfono"
            return False, f"Error al crear proveedor: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear_proveedor(telefono, nombre_empresa, nombre_proveedor, correo=None, estado='activo'):
        """Crear un nuevo proveedor (método original para compatibilidad)"""
        return ClienteProveedorModel.crear_proveedor_con_productos(
            telefono, nombre_empresa, nombre_proveedor, correo, estado, None
        )
    
    @staticmethod
    def actualizar_proveedor(telefono_original, telefono, nombre_empresa, nombre_proveedor, correo, estado, producto=None):
        """Actualizar información de un proveedor"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Si se proporciona producto, actualizarlo
            if producto is not None:
                sql = """
                UPDATE proveedor 
                SET telefono = %s, nombre_empresa = %s, nombre_proveedor = %s, 
                    correo = %s, estado = %s, producto = %s
                WHERE telefono = %s
                """
                cursor.execute(sql, (telefono, nombre_empresa, nombre_proveedor, correo, estado, producto, telefono_original))
            else:
                sql = """
                UPDATE proveedor 
                SET telefono = %s, nombre_empresa = %s, nombre_proveedor = %s, 
                    correo = %s, estado = %s
                WHERE telefono = %s
                """
                cursor.execute(sql, (telefono, nombre_empresa, nombre_proveedor, correo, estado, telefono_original))
            
            conn.commit()
            
            logger.info(f"Proveedor actualizado: {telefono_original} -> {telefono}")
            return True, "Proveedor actualizado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            error_msg = str(e)
            logger.error(f"Error al actualizar proveedor: {error_msg}")
            if "Duplicate entry" in error_msg:
                return False, "Ya existe un proveedor con este nuevo teléfono"
            return False, f"Error al actualizar proveedor: {error_msg}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def eliminar_proveedor(telefono):
        """Eliminar un proveedor"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # Verificar si tiene productos asociados
            cursor.execute("SELECT COUNT(*) as total FROM productos WHERE proveedor = %s", (telefono,))
            productos = cursor.fetchone()[0]
            
            if productos > 0:
                logger.warning(f"No se puede eliminar proveedor {telefono} - Tiene {productos} productos asociados")
                return False, "No se puede eliminar el proveedor porque tiene productos asociados"
            
            sql = "DELETE FROM proveedor WHERE telefono = %s"
            cursor.execute(sql, (telefono,))
            conn.commit()
            
            logger.info(f"Proveedor eliminado: {telefono}")
            return True, "Proveedor eliminado exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al eliminar proveedor {telefono}: {str(e)}")
            return False, f"Error al eliminar proveedor: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_historial_proveedor(telefono):
        """Obtener historial completo de un proveedor"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Obtener información básica del proveedor
            proveedor_info = ClienteProveedorModel.obtener_proveedor_por_telefono(telefono)
            if not proveedor_info:
                return None
            
            # Obtener solo nombres de productos suministrados
            sql_productos = """
            SELECT p.nombre
            FROM productos p
            WHERE p.proveedor = %s
            ORDER BY p.nombre
            """
            
            cursor.execute(sql_productos, (telefono,))
            productos = cursor.fetchall()
            
            # Solo necesitamos los nombres
            nombres_productos = [p['nombre'] for p in productos]
            
            historial = {
                'proveedor': proveedor_info,
                'productos_nombres': nombres_productos,
                'resumen': {
                    'total_productos': len(nombres_productos),
                    'estado': proveedor_info.get('estado', 'activo')
                }
            }
            
            return serializar_datos(historial)
            
        except Exception as e:
            logger.error(f"Error en obtener_historial_proveedor: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ===== MÉTODOS PARA PRODUCTOS DE PROVEEDORES =====
    
    @staticmethod
    def obtener_productos_para_asignar():
        """Obtener lista de productos disponibles para asignar a proveedores"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT id, nombre, categoria, presentacion, precio_costo
            FROM productos
            WHERE proveedor IS NULL OR proveedor = ''
            ORDER BY nombre
            """
            
            cursor.execute(sql)
            productos = cursor.fetchall()
            
            productos = serializar_datos(productos)
            
            return productos
            
        except Exception as e:
            logger.error(f"Error en obtener_productos_para_asignar: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def asignar_productos_a_proveedor(telefono_proveedor, ids_productos):
        """Asignar productos a un proveedor"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            if not ids_productos:
                return True, "No hay productos para asignar"
            
            # Actualizar cada producto
            for id_producto in ids_productos:
                sql = """
                UPDATE productos 
                SET proveedor = %s 
                WHERE id = %s
                """
                cursor.execute(sql, (telefono_proveedor, id_producto))
            
            conn.commit()
            
            logger.info(f"Asignados {len(ids_productos)} productos al proveedor {telefono_proveedor}")
            return True, f"{len(ids_productos)} productos asignados exitosamente"
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al asignar productos: {str(e)}")
            return False, f"Error al asignar productos: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()