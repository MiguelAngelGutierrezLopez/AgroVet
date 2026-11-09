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

    @staticmethod
    def ensure_compras_proveedor_table():
        """Crear la tabla de compras por proveedor si no existe."""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS compras_proveedor (
                    id INT NOT NULL AUTO_INCREMENT,
                    proveedor_telefono VARCHAR(15) NOT NULL,
                    producto_id INT NOT NULL,
                    producto_id_historico INT NULL,
                    producto_nombre_historico VARCHAR(100) NULL,
                    producto_categoria_historica VARCHAR(50) NULL,
                    producto_presentacion_historica VARCHAR(50) NULL,
                    fecha_compra DATE NOT NULL,
                    cantidad INT NOT NULL DEFAULT 0,
                    precio_costo_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                    precio_venta_unitario DECIMAL(12,2) DEFAULT 0.00,
                    total_compra DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                    observaciones TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (id),
                    KEY idx_proveedor_fecha (proveedor_telefono, fecha_compra),
                    KEY idx_producto (producto_id),
                    CONSTRAINT fk_compras_proveedor FOREIGN KEY (proveedor_telefono) REFERENCES proveedor (telefono) ON UPDATE CASCADE ON DELETE CASCADE,
                    CONSTRAINT fk_compras_producto FOREIGN KEY (producto_id) REFERENCES productos (id) ON UPDATE CASCADE ON DELETE RESTRICT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
            """)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creando tabla compras_proveedor: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def _normalizar_productos_ids(productos):
        """Normalizar una lista de productos a IDs únicos"""
        ids = []
        if productos is None:
            return ids

        if isinstance(productos, str):
            productos = [productos]

        for item in productos:
            if isinstance(item, dict):
                valor = item.get('id') if item.get('id') is not None else item.get('producto_id')
            elif isinstance(item, (int, float)):
                valor = int(item)
            else:
                valor = item

            if valor is None:
                continue

            if isinstance(valor, str):
                valor = valor.strip()
                if not valor:
                    continue
                if valor.isdigit():
                    ids.append(int(valor))
                    continue
                if valor.startswith('[') and valor.endswith(']'):
                    try:
                        valor = eval(valor, {"__builtins__": {}}, {})
                    except Exception:
                        valor = []
                elif ',' in valor:
                    for parte in valor.split(','):
                        parte = parte.strip()
                        if parte and parte.isdigit():
                            ids.append(int(parte))
                    continue

            if isinstance(valor, list):
                for subvalor in valor:
                    if isinstance(subvalor, (int, float)):
                        ids.append(int(subvalor))
                    elif isinstance(subvalor, str) and subvalor.strip().isdigit():
                        ids.append(int(subvalor.strip()))
                continue

            if isinstance(valor, (int, float)):
                ids.append(int(valor))
                continue

            if isinstance(valor, str) and valor.isdigit():
                ids.append(int(valor))

        ids = list(dict.fromkeys(ids))
        return [int(id_producto) for id_producto in ids if id_producto is not None]

    @staticmethod
    def _sincronizar_productos_proveedor(telefono_proveedor, productos_ids):
        """Asigna los productos seleccionados al proveedor usando la tabla junction proveedor_productos.
        También actualiza el campo resumen 'producto' en la tabla proveedor."""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            productos_ids = ClienteProveedorModel._normalizar_productos_ids(productos_ids)

            # 1. ELIMINAR TODAS LAS ASIGNACIONES PREVIAS DE ESTE PROVEEDOR EN LA TABLA JUNCTION
            cursor.execute("DELETE FROM proveedor_productos WHERE proveedor_telefono = %s", (telefono_proveedor,))

            # El campo productos.proveedor representa un único proveedor por producto.
            # Al reasignar, se retiran primero las referencias anteriores.
            cursor.execute("UPDATE productos SET proveedor = NULL WHERE proveedor = %s", (telefono_proveedor,))

            # 2. INSERTAR LAS NUEVAS ASIGNACIONES EN LA TABLA JUNCTION
            if productos_ids:
                placeholders = ', '.join(['%s'] * len(productos_ids))

                # Evita que la tabla junction conserve otro proveedor para un producto
                # cuyo FK solo puede apuntar a un proveedor.
                cursor.execute(
                    f"DELETE FROM proveedor_productos WHERE producto_id IN ({placeholders}) AND proveedor_telefono <> %s",
                    (*productos_ids, telefono_proveedor)
                )

                for producto_id in productos_ids:
                    cursor.execute(
                        "INSERT INTO proveedor_productos (proveedor_telefono, producto_id) VALUES (%s, %s) "
                        "ON DUPLICATE KEY UPDATE fecha_asignacion = CURRENT_TIMESTAMP",
                        (telefono_proveedor, producto_id)
                    )

                # Mantiene actualizada la llave foránea existente en productos.
                cursor.execute(
                    f"UPDATE productos SET proveedor = %s WHERE id IN ({placeholders})",
                    (telefono_proveedor, *productos_ids)
                )

                # 3. OBTENER LOS NOMBRES DE LOS PRODUCTOS PARA EL RESUMEN TEXTO
                cursor.execute(
                    f"SELECT nombre FROM productos WHERE id IN ({placeholders}) ORDER BY nombre",
                    tuple(productos_ids)
                )
                nombres = [row[0] for row in cursor.fetchall() if row and row[0]]
                producto_texto = ', '.join(nombres)
                
                # 4. ACTUALIZAR CAMPO RESUMEN EN TABLA PROVEEDOR
                cursor.execute(
                    "UPDATE proveedor SET producto = %s WHERE telefono = %s",
                    (producto_texto, telefono_proveedor)
                )
            else:
                # Si no hay productos, limpiar el campo resumen
                cursor.execute(
                    "UPDATE proveedor SET producto = NULL WHERE telefono = %s",
                    (telefono_proveedor,)
                )

            conn.commit()
            logger.info(f"Productos sincronizados para proveedor {telefono_proveedor}: {len(productos_ids)} asignados via tabla junction")
            return True, "Productos actualizados correctamente"
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error al sincronizar productos del proveedor {telefono_proveedor}: {str(e)}")
            return False, f"Error al sincronizar productos: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
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
                (SELECT GROUP_CONCAT(
                            COALESCE(dv.producto_nombre_historico, p.nombre)
                            SEPARATOR ', '
                        )
                 FROM detalle_venta dv 
                 LEFT JOIN productos p ON dv.id_producto = p.id
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
                      SELECT id, cantidad, precio_venta, nombre, categoria,
                          presentacion, precio_costo
                    FROM productos 
                    WHERE nombre LIKE %s 
                    ORDER BY id DESC 
                    LIMIT 1
                """, (f"%{producto_nombre}%",))
                
                producto_db = cursor.fetchone()
                
                if not producto_db:
                    return False, f"Producto no encontrado: {producto_nombre}"
                
                producto_id = producto_db[0]
                stock_actual = int(producto_db[1] or 0)
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
                    id_venta, id_producto, producto_id_historico,
                    producto_nombre_historico, producto_categoria_historica,
                    producto_presentacion_historica, costo_unitario_historico,
                    fecha_venta, cantidad_vendida, precio_unidad, precio_neto
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(sql_detalle, (
                    venta_id,
                    producto_id,
                    producto_id,
                    producto_db[3],
                    producto_db[4],
                    producto_db[5],
                    producto_db[6] or 0,
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
                    COALESCE(dv.producto_nombre_historico, p.nombre) as producto_nombre,
                    COALESCE(dv.producto_presentacion_historica, p.presentacion) as presentacion
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

            productos_ids = ClienteProveedorModel._normalizar_productos_ids(productos)

            sql_proveedor = """
            INSERT INTO proveedor (telefono, nombre_empresa, nombre_proveedor, correo, estado, producto, fecha_registro)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """

            producto_texto = None
            if productos_ids:
                placeholders = ', '.join(['%s'] * len(productos_ids))
                cursor.execute(f"SELECT nombre FROM productos WHERE id IN ({placeholders}) ORDER BY nombre", tuple(productos_ids))
                nombres = [row[0] for row in cursor.fetchall() if row and row[0]]
                producto_texto = ', '.join(nombres)

            cursor.execute(sql_proveedor, (telefono, nombre_empresa, nombre_proveedor, correo, estado, producto_texto))
            conn.commit()

            if productos_ids:
                success, message = ClienteProveedorModel._sincronizar_productos_proveedor(telefono, productos_ids)
                if not success:
                    return False, message

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
        """Actualizar información de un proveedor y sincronizar productos reales."""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor()

            productos_ids = ClienteProveedorModel._normalizar_productos_ids(producto)

            sql = """
            UPDATE proveedor 
            SET telefono = %s, nombre_empresa = %s, nombre_proveedor = %s, 
                correo = %s, estado = %s
            WHERE telefono = %s
            """
            cursor.execute(sql, (telefono, nombre_empresa, nombre_proveedor, correo, estado, telefono_original))

            producto_texto = None
            if productos_ids:
                placeholders = ', '.join(['%s'] * len(productos_ids))
                cursor.execute(
                    f"SELECT nombre FROM productos WHERE id IN ({placeholders}) ORDER BY nombre",
                    tuple(productos_ids)
                )
                nombres = [row[0] for row in cursor.fetchall() if row and row[0]]
                producto_texto = ', '.join(nombres)

            cursor.execute(
                "UPDATE proveedor SET producto = %s WHERE telefono = %s",
                (producto_texto, telefono)
            )

            conn.commit()

            success, message = ClienteProveedorModel._sincronizar_productos_proveedor(telefono, productos_ids)
            if not success:
                return False, message

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
    def obtener_historial_proveedor(telefono, fecha_inicio=None, fecha_fin=None):
        """Obtener historial completo de un proveedor con métricas por producto y filtro por fechas."""
        conn = None
        cursor = None
        try:
            ClienteProveedorModel.ensure_compras_proveedor_table()
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            proveedor_info = ClienteProveedorModel.obtener_proveedor_por_telefono(telefono)
            if not proveedor_info:
                return None

            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date() if fecha_fin else date.today()
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date() if fecha_inicio else fecha_fin_obj.replace(day=1)
            if fecha_inicio_obj > fecha_fin_obj:
                fecha_inicio_obj, fecha_fin_obj = fecha_fin_obj, fecha_inicio_obj

            mes_inicio = fecha_fin_obj.replace(day=1)
            mes_fin = fecha_fin_obj
            anio_inicio = date(fecha_fin_obj.year, 1, 1)
            anio_fin = date(fecha_fin_obj.year, 12, 31)

            sql_productos = """
                SELECT p.id,
                       p.nombre,
                       p.categoria,
                       p.presentacion,
                       p.precio_costo,
                       p.precio_venta,
                       COALESCE(SUM(CASE
                           WHEN cp.fecha_compra BETWEEN %s AND %s THEN cp.cantidad
                           ELSE 0
                       END), 0) AS cantidad_total_periodo,
                       COALESCE(SUM(CASE
                           WHEN cp.fecha_compra BETWEEN %s AND %s THEN cp.total_compra
                           ELSE 0
                       END), 0) AS costo_total_periodo,
                       COUNT(CASE
                           WHEN cp.fecha_compra >= %s AND cp.fecha_compra <= %s THEN 1
                       END) AS cantidad_comprada_mes,
                       COALESCE(SUM(CASE
                           WHEN cp.fecha_compra >= %s AND cp.fecha_compra <= %s THEN cp.total_compra
                           ELSE 0
                       END), 0) AS costo_total_mes,
                       COUNT(CASE
                           WHEN cp.fecha_compra >= %s AND cp.fecha_compra <= %s THEN 1
                       END) AS cantidad_comprada_anio,
                       COALESCE(SUM(CASE
                           WHEN cp.fecha_compra >= %s AND cp.fecha_compra <= %s THEN cp.total_compra
                           ELSE 0
                       END), 0) AS costo_total_anio,
                       COALESCE(MAX(cp.fecha_compra), NULL) AS ultima_compra
                FROM productos p
                LEFT JOIN compras_proveedor cp
                    ON cp.producto_id = p.id
                   AND cp.proveedor_telefono = %s
                WHERE p.proveedor = %s
                   OR EXISTS (
                       SELECT 1
                       FROM proveedor_productos pp
                       WHERE pp.producto_id = p.id
                         AND pp.proveedor_telefono = %s
                   )
                GROUP BY p.id, p.nombre, p.categoria, p.presentacion, p.precio_costo, p.precio_venta
                ORDER BY p.nombre
            """

            params = (
                fecha_inicio_obj.isoformat(), fecha_fin_obj.isoformat(),
                fecha_inicio_obj.isoformat(), fecha_fin_obj.isoformat(),
                mes_inicio.isoformat(), mes_fin.isoformat(),
                mes_inicio.isoformat(), mes_fin.isoformat(),
                anio_inicio.isoformat(), anio_fin.isoformat(),
                anio_inicio.isoformat(), anio_fin.isoformat(),
                telefono, telefono, telefono
            )
            cursor.execute(sql_productos, params)
            productos = cursor.fetchall()

            for producto in productos:
                producto['cantidad_total_periodo'] = float(producto.get('cantidad_total_periodo') or 0)
                producto['cantidad_comprada_mes'] = float(producto.get('cantidad_comprada_mes') or 0)
                producto['cantidad_comprada_anio'] = float(producto.get('cantidad_comprada_anio') or 0)
                producto['costo_total_periodo'] = float(producto.get('costo_total_periodo') or 0)
                producto['costo_total_mes'] = float(producto.get('costo_total_mes') or 0)
                producto['costo_total_anio'] = float(producto.get('costo_total_anio') or 0)
                producto['precio_costo'] = float(producto.get('precio_costo') or 0)
                producto['precio_venta'] = float(producto.get('precio_venta') or 0)
                producto['margen_estimado'] = producto['precio_venta'] - producto['precio_costo']
                producto['margen_total_estimado'] = producto['margen_estimado'] * producto['cantidad_total_periodo']

            total_periodo = sum(float(p.get('costo_total_periodo') or 0) for p in productos)
            total_mes = sum(float(p.get('costo_total_mes') or 0) for p in productos)
            total_anio = sum(float(p.get('costo_total_anio') or 0) for p in productos)
            cantidad_periodo = sum(float(p.get('cantidad_total_periodo') or 0) for p in productos)
            cantidad_mes = sum(float(p.get('cantidad_comprada_mes') or 0) for p in productos)
            cantidad_anio = sum(float(p.get('cantidad_comprada_anio') or 0) for p in productos)

            historial = {
                'proveedor': proveedor_info,
                'productos': serializar_datos(productos),
                'productos_nombres': [p['nombre'] for p in productos],
                'resumen': {
                    'total_productos': len(productos),
                    'estado': proveedor_info.get('estado', 'activo'),
                    'cantidad_total_periodo': cantidad_periodo,
                    'cantidad_comprada_mes': cantidad_mes,
                    'cantidad_comprada_anio': cantidad_anio,
                    'total_gastado_periodo': total_periodo,
                    'total_gastado_mes': total_mes,
                    'total_gastado_anio': total_anio,
                    'fecha_inicio': fecha_inicio_obj.isoformat(),
                    'fecha_fin': fecha_fin_obj.isoformat(),
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

    @staticmethod
    def registrar_compra_proveedor(telefono_proveedor, producto_id, cantidad, precio_costo=None, precio_venta=None, fecha_compra=None, observaciones=None):
        """Registrar compra de un producto a un proveedor usando los precios actuales del producto."""
        try:
            ClienteProveedorModel.ensure_compras_proveedor_table()
            if not telefono_proveedor or not producto_id:
                return False, 'Faltan datos del proveedor o del producto'

            try:
                cantidad_num = float(cantidad or 0)
            except (TypeError, ValueError):
                return False, 'La cantidad debe ser un número entero válido'

            if not cantidad_num.is_integer():
                return False, 'La cantidad debe ser un entero, sin decimales'

            cantidad = int(cantidad_num)
            if cantidad <= 0:
                return False, 'La cantidad debe ser mayor a cero'

            fecha_compra = fecha_compra or date.today().isoformat()

            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                  SELECT p.id, p.nombre, p.categoria, p.presentacion,
                      p.proveedor, p.precio_costo, p.precio_venta
                FROM productos p
                WHERE p.id = %s
                """,
                (producto_id,)
            )
            producto = cursor.fetchone()
            if not producto:
                return False, 'No existe el producto indicado'

            if producto.get('proveedor') and producto.get('proveedor') != telefono_proveedor:
                cursor.execute(
                    "SELECT 1 FROM proveedor_productos WHERE proveedor_telefono = %s AND producto_id = %s",
                    (telefono_proveedor, producto_id)
                )
                if cursor.fetchone() is None:
                    return False, 'El producto no está asociado a este proveedor'

            precio_costo_actual = float(producto.get('precio_costo') or 0)
            precio_venta_actual = float(producto.get('precio_venta') or 0)
            total_compra = cantidad * precio_costo_actual

            cursor.execute(
                """
                INSERT INTO compras_proveedor (
                    proveedor_telefono, producto_id, producto_id_historico,
                    producto_nombre_historico, producto_categoria_historica,
                    producto_presentacion_historica, fecha_compra, cantidad,
                    precio_costo_unitario, precio_venta_unitario, total_compra,
                    observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    telefono_proveedor,
                    producto_id,
                    producto_id,
                    producto.get('nombre'),
                    producto.get('categoria'),
                    producto.get('presentacion'),
                    fecha_compra,
                    cantidad,
                    precio_costo_actual,
                    precio_venta_actual,
                    total_compra,
                    observaciones
                )
            )

            conn.commit()
            return True, 'Compra del proveedor registrada correctamente'
        except Exception as e:
            logger.error(f"Error registrando compra del proveedor {telefono_proveedor}: {str(e)}")
            return False, f"Error al registrar la compra: {str(e)}"
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()

    @staticmethod
    def eliminar_compra_proveedor(compra_id, telefono_proveedor=None):
        """Eliminar una compra registrada a un proveedor. Permite validación por teléfono para seguridad."""
        conn = None
        cursor = None
        try:
            if compra_id is None:
                return False, 'Falta el identificador de la compra'

            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            query = "SELECT proveedor_telefono FROM compras_proveedor WHERE id = %s"
            params = (compra_id,)
            cursor.execute(query, params)
            compra = cursor.fetchone()

            if not compra:
                return False, 'La compra no existe'

            if telefono_proveedor and compra.get('proveedor_telefono') != telefono_proveedor:
                return False, 'La compra no pertenece a este proveedor'

            cursor.execute("DELETE FROM compras_proveedor WHERE id = %s", (compra_id,))
            conn.commit()
            return True, 'Compra eliminada correctamente'
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error eliminando compra {compra_id}: {str(e)}")
            return False, f"Error al eliminar la compra: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def obtener_declaracion_renta_resumen(fecha_inicio=None, fecha_fin=None, proveedor_telefono=None):
        """Resumen fiscal completo del negocio para declaración de renta.

        Combina las fuentes financieras relevantes del sistema:
        - ventas y detalle_venta para ingresos y costo de ventas
        - compras_proveedor para gastos de proveedores
        - creditos y abonos para cartera y cobros
        - reporte_caja para caja y egresos operativos
        """
        conn = None
        cursor = None
        try:
            ClienteProveedorModel.ensure_compras_proveedor_table()
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            if not fecha_fin:
                fecha_fin = date.today().isoformat()
            if not fecha_inicio:
                fecha_inicio = date.today().replace(day=1).isoformat()

            filtro_ventas = " WHERE v.fecha_dia BETWEEN %s AND %s "
            params_ventas = [fecha_inicio, fecha_fin]
            if proveedor_telefono:
                filtro_ventas += " AND v.cliente_cedula = %s "
                params_ventas.append(proveedor_telefono)

            query_ventas = f"""
                SELECT
                    COALESCE(SUM(v.total), 0) AS ingresos_brutos,
                    COALESCE(SUM(CASE WHEN v.tipo_pago != 'CRÉDITO' THEN v.total ELSE 0 END), 0) AS ventas_contado,
                    COALESCE(SUM(CASE WHEN v.tipo_pago = 'CRÉDITO' THEN v.total ELSE 0 END), 0) AS ventas_credito,
                    COALESCE(SUM(CASE WHEN c.anticipo IS NOT NULL THEN c.anticipo ELSE 0 END), 0) AS anticipos,
                    COALESCE(SUM(CASE WHEN c.abonos_realizados IS NOT NULL THEN c.abonos_realizados ELSE 0 END), 0) AS abonos_cobrados,
                    COALESCE(SUM(CASE WHEN c.saldo_pendiente IS NOT NULL THEN c.saldo_pendiente ELSE 0 END), 0) AS saldo_pendiente,
                    COUNT(DISTINCT v.id) AS total_ventas
                FROM ventas v
                LEFT JOIN creditos c ON c.venta_id = v.id
                {filtro_ventas}
            """
            cursor.execute(query_ventas, tuple(params_ventas))
            ventas_summary = cursor.fetchone() or {}

            filtro_costo = " WHERE v.fecha_dia BETWEEN %s AND %s "
            params_costo = [fecha_inicio, fecha_fin]
            if proveedor_telefono:
                filtro_costo += " AND v.cliente_cedula = %s "
                params_costo.append(proveedor_telefono)

            query_costo = f"""
                SELECT
                    COALESCE(SUM(
                        dv.cantidad_vendida * COALESCE(
                            dv.costo_unitario_historico, p.precio_costo, 0
                        )
                    ), 0) AS costo_ventas
                FROM detalle_venta dv
                LEFT JOIN productos p ON p.id = dv.id_producto
                JOIN ventas v ON v.id = dv.id_venta
                {filtro_costo}
            """
            cursor.execute(query_costo, tuple(params_costo))
            costo_ventas = cursor.fetchone() or {}

            filtro_compra = " WHERE cp.fecha_compra BETWEEN %s AND %s "
            params_compra = [fecha_inicio, fecha_fin]
            if proveedor_telefono:
                filtro_compra += " AND cp.proveedor_telefono = %s "
                params_compra.append(proveedor_telefono)

            query_compras = f"""
                SELECT
                    COALESCE(SUM(cp.total_compra), 0) AS gastos_totales,
                    COALESCE(COUNT(DISTINCT cp.proveedor_telefono), 0) AS total_proveedores,
                    COALESCE(COUNT(cp.id), 0) AS total_compras,
                    COALESCE(SUM(CASE WHEN cp.precio_venta_unitario IS NOT NULL THEN cp.cantidad * (cp.precio_venta_unitario - cp.precio_costo_unitario) ELSE 0 END), 0) AS margen_estimado,
                    COALESCE(SUM(CASE WHEN cp.precio_costo_unitario > 0 THEN cp.cantidad * cp.precio_costo_unitario ELSE 0 END), 0) AS base_gasto
                FROM compras_proveedor cp
                {filtro_compra}
            """
            cursor.execute(query_compras, tuple(params_compra))
            compras_summary = cursor.fetchone() or {}

            query_caja = """
                SELECT
                    COALESCE(SUM(egresos), 0) AS egresos_caja,
                    COALESCE(SUM(ingresos), 0) AS ingresos_caja
                FROM reporte_caja
                WHERE DATE(fecha_egreso) BETWEEN %s AND %s OR DATE(fecha_ingreso) BETWEEN %s AND %s
            """
            cursor.execute(query_caja, (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin))
            caja_summary = cursor.fetchone() or {}

            query_por_mes = f"""
                SELECT MONTH(cp.fecha_compra) AS mes, COALESCE(SUM(cp.total_compra), 0) AS total
                FROM compras_proveedor cp
                {filtro_compra}
                GROUP BY MONTH(cp.fecha_compra)
                ORDER BY MONTH(cp.fecha_compra)
            """
            cursor.execute(query_por_mes, tuple(params_compra))
            por_mes = cursor.fetchall() or []

            query_top_proveedores = f"""
                SELECT cp.proveedor_telefono, p.nombre_empresa, p.nombre_proveedor,
                       COALESCE(SUM(cp.total_compra), 0) AS total_compra
                FROM compras_proveedor cp
                LEFT JOIN proveedor p ON p.telefono = cp.proveedor_telefono
                {filtro_compra}
                GROUP BY cp.proveedor_telefono, p.nombre_empresa, p.nombre_proveedor
                ORDER BY total_compra DESC
                LIMIT 10
            """
            cursor.execute(query_top_proveedores, tuple(params_compra))
            top_proveedores = cursor.fetchall() or []

            ingreso_bruto = float(ventas_summary.get('ingresos_brutos') or 0)
            venta_contado = float(ventas_summary.get('ventas_contado') or 0)
            venta_credito = float(ventas_summary.get('ventas_credito') or 0)
            anticipos = float(ventas_summary.get('anticipos') or 0)
            abonos_cobrados = float(ventas_summary.get('abonos_cobrados') or 0)
            saldo_pendiente = float(ventas_summary.get('saldo_pendiente') or 0)
            costo_ventas_total = float(costo_ventas.get('costo_ventas') or 0)
            gastos_totales = float(compras_summary.get('gastos_totales') or 0)
            egresos_caja = float(caja_summary.get('egresos_caja') or 0)
            ingresos_caja = float(caja_summary.get('ingresos_caja') or 0)
            utilidad_bruta = ingreso_bruto - costo_ventas_total
            utilidad_neta = utilidad_bruta - gastos_totales
            empresa_egresos = gastos_totales + egresos_caja
            mes_actual = date.today().replace(day=1)
            total_mes_actual = sum(float(item.get('total') or 0) for item in por_mes if int(item.get('mes') or 0) == mes_actual.month)

            resultado = {
                'periodo': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'anio': date.fromisoformat(fecha_fin).year
                },
                'resumen': {
                    'ingresos_brutos': ingreso_bruto,
                    'ventas_contado': venta_contado,
                    'ventas_credito': venta_credito,
                    'anticipos': anticipos,
                    'abonos_cobrados': abonos_cobrados,
                    'saldo_pendiente': saldo_pendiente,
                    'cobros_reales': venta_contado + anticipos + abonos_cobrados,
                    'costo_ventas': costo_ventas_total,
                    'gastos_totales': gastos_totales,
                    'egresos_caja': egresos_caja,
                    'total_gastado': gastos_totales,
                    'total_proveedores': int(compras_summary.get('total_proveedores') or 0),
                    'total_compras': int(compras_summary.get('total_compras') or 0),
                    'margen_estimado': float(compras_summary.get('margen_estimado') or 0),
                    'base_gasto': float(compras_summary.get('base_gasto') or 0),
                    'utilidad_bruta': utilidad_bruta,
                    'utilidad_neta': utilidad_neta,
                    'total_mes_actual': total_mes_actual,
                    'ingresos_caja': ingresos_caja,
                    'flujo_caja': ingresos_caja - empresa_egresos,
                    'empresa_egresos': empresa_egresos,
                    'ingresos_netos': ingreso_bruto - gastos_totales
                },
                'por_mes': [
                    {'mes': int(item.get('mes') or 0), 'total': float(item.get('total') or 0)}
                    for item in por_mes
                ],
                'top_proveedores': [
                    {
                        'proveedor_telefono': item.get('proveedor_telefono'),
                        'nombre': item.get('nombre_empresa') or item.get('nombre_proveedor') or 'Proveedor',
                        'total': float(item.get('total_compra') or 0)
                    }
                    for item in top_proveedores
                ]
            }

            return serializar_datos(resultado)
        except Exception as e:
            logger.error(f"Error en obtener_declaracion_renta_resumen: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    @staticmethod
    def obtener_declaracion_renta_proveedores(fecha_inicio=None, fecha_fin=None):
        """Lista consolidada por proveedor para la pantalla de declaración de renta."""
        try:
            if not fecha_fin:
                fecha_fin = date.today().isoformat()
            if not fecha_inicio:
                fecha_inicio = date.today().replace(day=1).isoformat()

            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = """
                SELECT
                    cp.proveedor_telefono AS telefono,
                    p.nombre_empresa,
                    p.nombre_proveedor,
                    p.estado,
                    COALESCE(SUM(cp.total_compra), 0) AS total_compras,
                    COALESCE(SUM(cp.cantidad), 0) AS cantidad_total,
                    COALESCE(COUNT(cp.id), 0) AS total_registros,
                    COALESCE(MAX(cp.fecha_compra), NULL) AS ultima_compra
                FROM compras_proveedor cp
                LEFT JOIN proveedor p ON p.telefono = cp.proveedor_telefono
                WHERE cp.fecha_compra BETWEEN %s AND %s
                GROUP BY cp.proveedor_telefono, p.nombre_empresa, p.nombre_proveedor, p.estado
                ORDER BY total_compras DESC
            """
            cursor.execute(sql, (fecha_inicio, fecha_fin))
            rows = cursor.fetchall() or []

            proveedores = []
            for row in rows:
                proveedores.append({
                    'telefono': row.get('telefono'),
                    'nombre_empresa': row.get('nombre_empresa') or 'Sin empresa',
                    'nombre_proveedor': row.get('nombre_proveedor') or 'Sin nombre',
                    'estado': row.get('estado') or 'activo',
                    'total_compras': float(row.get('total_compras') or 0),
                    'cantidad_total': float(row.get('cantidad_total') or 0),
                    'total_registros': int(row.get('total_registros') or 0),
                    'ultima_compra': row.get('ultima_compra')
                })

            return serializar_datos(proveedores)
        except Exception as e:
            logger.error(f"Error en obtener_declaracion_renta_proveedores: {str(e)}")
            return []
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
                conn.close()

    @staticmethod
    def obtener_declaracion_renta_detalle_proveedor(telefono, fecha_inicio=None, fecha_fin=None):
        """Devuelve el detalle de compras de un proveedor para respaldo fiscal y revisión."""
        try:
            if not fecha_fin:
                fecha_fin = date.today().isoformat()
            if not fecha_inicio:
                fecha_inicio = date.today().replace(day=1).isoformat()

            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)

            proveedor = None
            cursor.execute(
                "SELECT telefono, nombre_empresa, nombre_proveedor, estado FROM proveedor WHERE telefono = %s",
                (telefono,)
            )
            proveedor_row = cursor.fetchone()
            if proveedor_row:
                proveedor = {
                    'telefono': proveedor_row.get('telefono'),
                    'nombre_empresa': proveedor_row.get('nombre_empresa') or 'Sin empresa',
                    'nombre_proveedor': proveedor_row.get('nombre_proveedor') or 'Sin nombre',
                    'estado': proveedor_row.get('estado') or 'activo'
                }

            cursor.execute(
                """
                SELECT
                    cp.id,
                    cp.fecha_compra,
                    COALESCE(cp.producto_nombre_historico, p.nombre) AS producto,
                    cp.cantidad,
                    cp.precio_costo_unitario,
                    cp.precio_venta_unitario,
                    cp.total_compra,
                    cp.observaciones
                FROM compras_proveedor cp
                LEFT JOIN productos p ON p.id = cp.producto_id
                WHERE cp.proveedor_telefono = %s
                  AND cp.fecha_compra BETWEEN %s AND %s
                ORDER BY cp.fecha_compra DESC, cp.id DESC
                """,
                (telefono, fecha_inicio, fecha_fin)
            )
            compras = cursor.fetchall() or []

            resumen = {
                'total_compras': sum(float(item.get('total_compra') or 0) for item in compras),
                'cantidad_total': sum(float(item.get('cantidad') or 0) for item in compras),
                'registros': len(compras),
                'ultima_compra': max((item.get('fecha_compra') for item in compras if item.get('fecha_compra')), default=None)
            }

            return serializar_datos({
                'proveedor': proveedor,
                'resumen': resumen,
                'compras': [{
                    'id': item.get('id'),
                    'fecha_compra': item.get('fecha_compra'),
                    'producto': item.get('producto') or 'Producto sin nombre',
                    'cantidad': float(item.get('cantidad') or 0),
                    'precio_costo_unitario': float(item.get('precio_costo_unitario') or 0),
                    'precio_venta_unitario': float(item.get('precio_venta_unitario') or 0),
                    'total_compra': float(item.get('total_compra') or 0),
                    'observaciones': item.get('observaciones') or ''
                } for item in compras]
            })
        except Exception as e:
            logger.error(f"Error en obtener_declaracion_renta_detalle_proveedor: {str(e)}")
            return {'proveedor': None, 'resumen': {'total_compras': 0, 'cantidad_total': 0, 'registros': 0, 'ultima_compra': None, 'iva_soportado': 0}, 'compras': []}
        finally:
            if 'cursor' in locals() and cursor:
                cursor.close()
            if 'conn' in locals() and conn:
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
    def obtener_resumen_compras_producto(telefono, producto_id):
        """Obtiene el resumen histórico de un producto sin filtro de fechas."""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT COALESCE(
                           MAX(cp.producto_nombre_historico), MAX(p.nombre)
                       ) AS producto,
                       COUNT(cp.id) AS total_compras,
                       COALESCE(SUM(cp.cantidad), 0) AS cantidad_total,
                       COALESCE(SUM(cp.total_compra), 0) AS total_gastado,
                       COALESCE(MIN(cp.fecha_compra), NULL) AS primera_compra,
                       COALESCE(MAX(cp.fecha_compra), NULL) AS ultima_compra
                                FROM compras_proveedor cp
                                LEFT JOIN productos p ON p.id = cp.producto_id
                                WHERE cp.proveedor_telefono = %s
                                    AND cp.producto_id_historico = %s
                                GROUP BY cp.producto_id_historico
                """,
                (telefono, producto_id)
            )
            resumen = cursor.fetchone()
            if not resumen:
                return None
            cursor.execute(
                """
                SELECT cp.id, cp.fecha_compra, cp.cantidad,
                       cp.precio_costo_unitario, cp.total_compra,
                                             cp.observaciones, cp.producto_nombre_historico
                FROM compras_proveedor cp
                                WHERE cp.proveedor_telefono = %s
                                    AND cp.producto_id_historico = %s
                ORDER BY cp.fecha_compra DESC, cp.id DESC
                """,
                (telefono, producto_id)
            )
            compras = cursor.fetchall() or []
            return serializar_datos({
                'producto': resumen.get('producto') or 'Producto sin nombre',
                'total_compras': int(resumen.get('total_compras') or 0),
                'cantidad_total': float(resumen.get('cantidad_total') or 0),
                'total_gastado': float(resumen.get('total_gastado') or 0),
                'primera_compra': resumen.get('primera_compra'),
                'ultima_compra': resumen.get('ultima_compra'),
                'compras': [{
                    'id': item.get('id'),
                    'fecha_compra': item.get('fecha_compra'),
                    'cantidad': float(item.get('cantidad') or 0),
                    'precio_costo_unitario': float(item.get('precio_costo_unitario') or 0),
                    'total_compra': float(item.get('total_compra') or 0),
                    'observaciones': item.get('observaciones') or ''
                } for item in compras]
            })
        except Exception as e:
            logger.error(f"Error obteniendo resumen del producto {producto_id}: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def asignar_productos_a_proveedor(telefono_proveedor, ids_productos):
        """Asignar productos a un proveedor"""
        return ClienteProveedorModel._sincronizar_productos_proveedor(telefono_proveedor, ids_productos)