# En modelo/venta_model.py, actualizar la función crear_venta
from database import db
from datetime import datetime, date, time, timedelta
from decimal import Decimal

class VentaModel:
    @staticmethod
    def crear_venta(datos_venta):
        """Crear una nueva venta en la base de datos con registro de crédito si aplica"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obtener número de venta (ticket)
            numero_venta = VentaModel.obtener_ultimo_ticket()
            
            # 2. Obtener datos del cliente si es específico
            nombre_cliente = "CLIENTE FINAL"
            direccion_cliente = None
            telefono_cliente = None
            cliente_cedula = None
            nombre_cliente_completo = "CLIENTE FINAL"
            
            if datos_venta.get('cliente_cedula') and datos_venta['cliente_cedula'] != 'final':
                sql_cliente = "SELECT nombre, direccion, telefono FROM cliente WHERE cedula = %s"
                cursor.execute(sql_cliente, (datos_venta['cliente_cedula'],))
                cliente = cursor.fetchone()
                
                if cliente:
                    nombre_cliente = cliente['nombre']
                    nombre_cliente_completo = cliente['nombre']
                    direccion_cliente = cliente.get('direccion')
                    telefono_cliente = cliente.get('telefono')
                    cliente_cedula = datos_venta['cliente_cedula']
            
            # 3. Determinar tipo de pago
            tipo_pago = datos_venta['metodo_pago']
            if datos_venta.get('es_mixta', False):
                tipo_pago = 'mixto'
            
            # 4. Insertar venta principal
            sql_venta = """
            INSERT INTO ventas 
            (numero_venta, fecha_dia, fecha_hora, nombre_cliente, direccion_cliente, 
             telefono_cliente, tipo_pago, cliente_cedula, subtotal, descuento, total,
             dias_credito, submetodo_banco, usuario_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            fecha_actual = date.today()
            hora_actual = datetime.now().time()
            
            # Para ventas mixtas, usar valores de la primera parte de contado
            dias_credito_valor = None
            submetodo_banco_valor = None
            
            # Obtener ID de usuario
            usuario_id = 1  # Valor por defecto
            
            cursor.execute(sql_venta, (
                numero_venta,
                fecha_actual,
                hora_actual,
                nombre_cliente_completo,
                direccion_cliente,
                telefono_cliente,
                tipo_pago,
                cliente_cedula,
                datos_venta['subtotal'],
                datos_venta.get('descuento', 0),
                datos_venta['total'],
                dias_credito_valor,
                submetodo_banco_valor,
                usuario_id,
                'completada'
            ))
            
            venta_id = cursor.lastrowid
            
            # 5. Insertar productos en detalle_venta
            for producto in datos_venta['productos']:
                sql_detalle = """
                INSERT INTO detalle_venta 
                (id_venta, id_producto, fecha_venta, cantidad_vendida, 
                 precio_unidad, precio_neto)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                precio_neto = producto['cantidad'] * producto['precio']
                
                cursor.execute(sql_detalle, (
                    venta_id,
                    producto['id'],
                    fecha_actual,
                    producto['cantidad'],
                    producto['precio'],
                    precio_neto
                ))
                
                # Actualizar stock del producto
                sql_update_stock = """
                UPDATE productos 
                SET cantidad = cantidad - %s 
                WHERE id = %s AND cantidad >= %s
                """
                cursor.execute(sql_update_stock, (producto['cantidad'], producto['id'], producto['cantidad']))
                
                if cursor.rowcount == 0:
                    raise Exception(f"Stock insuficiente para el producto ID {producto['id']}")
            
            # 6. SI ES VENTA MIXTA, CREAR REGISTROS EN VENTAS_MIXTAS
            if datos_venta.get('es_mixta', False):
                metodos_mixtos = datos_venta.get('metodos_mixtos', [])
                
                for i, metodo in enumerate(metodos_mixtos, 1):
                    sql_mixta = """
                    INSERT INTO ventas_mixtas 
                    (id_venta, identificador, categoria, metodo_pago, submetodo, 
                     monto, dinero_entregado, cambio, anticipo, dias_credito, cliente_cedula)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    identificador = f"{venta_id}-{i}"
                    categoria = metodo.get('categoria', metodo['metodo'].upper())
                    
                    cursor.execute(sql_mixta, (
                        venta_id,
                        identificador,
                        categoria,
                        metodo['metodo'],
                        metodo.get('submetodo'),
                        metodo['monto'],
                        metodo.get('dinero_entregado', 0),
                        metodo.get('cambio', 0),
                        metodo.get('anticipo', 0),
                        metodo.get('dias_credito'),
                        metodo.get('cliente_cedula')
                    ))
            
            # 7. SI ES VENTA A CRÉDITO (normal), CREAR REGISTRO EN CRÉDITOS
            elif tipo_pago == 'credito' and cliente_cedula:
                total_venta = float(datos_venta['total'])
                anticipo_venta = float(datos_venta.get('anticipo', 0))
                deuda_inicial = total_venta - anticipo_venta
                dias_credito = datos_venta.get('dias_credito', 30)
                
                # Calcular fecha de vencimiento
                fecha_vencimiento = fecha_actual + timedelta(days=dias_credito)
                
                # Insertar en tabla créditos
                sql_credito = """
                INSERT INTO creditos 
                (venta_id, cliente_cedula, anticipo, deuda_inicial, saldo_pendiente,
                 dias_credito, fecha_inicio, fecha_vencimiento, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pendiente')
                """
                
                cursor.execute(sql_credito, (
                    venta_id,
                    cliente_cedula,
                    anticipo_venta,
                    deuda_inicial,
                    deuda_inicial,  # Saldo pendiente inicial = deuda_inicial
                    dias_credito,
                    fecha_actual,
                    fecha_vencimiento
                ))
            
            conn.commit()
            print(f"DEBUG - Transacción completada: Venta ID {venta_id}, Tipo: {tipo_pago}")
            
            return {
                'success': True,
                'venta_id': venta_id,
                'ticket_numero': numero_venta
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"ERROR en crear_venta: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_venta_para_factura(venta_id):
        """Obtener una venta completa para factura con información de crédito y mixta"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Obtener datos de la venta
            sql_venta = """
            SELECT v.*, 
                   DATE_FORMAT(v.fecha_dia, '%%d/%%m/%%Y') as fecha_formateada,
                   TIME_FORMAT(v.fecha_hora, '%%H:%%i') as hora_formateada,
                   DAYNAME(v.fecha_dia) as dia_semana
            FROM ventas v
            WHERE v.id = %s
            """
            
            cursor.execute(sql_venta, (venta_id,))
            venta = cursor.fetchone()
            
            if not venta:
                return None
            
            # Obtener información de crédito si existe (solo para crédito normal)
            if venta['tipo_pago'] == 'credito' and venta['cliente_cedula']:
                sql_credito = """
                SELECT c.anticipo, c.deuda_inicial, c.saldo_pendiente, c.dias_credito,
                       c.fecha_inicio, c.fecha_vencimiento, c.estado,
                       DATE_FORMAT(c.fecha_vencimiento, '%%d/%%m/%%Y') as vencimiento_formateado
                FROM creditos c
                WHERE c.venta_id = %s
                """
                cursor.execute(sql_credito, (venta_id,))
                credito = cursor.fetchone()
                
                if credito:
                    venta['credito_info'] = credito
            
            # Obtener información de venta mixta si existe
            if venta['tipo_pago'] == 'mixto':
                sql_mixta = """
                SELECT categoria, metodo_pago, submetodo, monto, 
                       dinero_entregado, cambio, anticipo, dias_credito
                FROM ventas_mixtas
                WHERE id_venta = %s
                ORDER BY identificador
                """
                cursor.execute(sql_mixta, (venta_id,))
                venta_mixta = cursor.fetchall()
                
                if venta_mixta:
                    venta['mixta_info'] = venta_mixta
            
            # Obtener productos de la venta
            sql_productos = """
            SELECT dv.*, p.nombre as producto_nombre, p.presentacion
            FROM detalle_venta dv
            JOIN productos p ON dv.id_producto = p.id
            WHERE dv.id_venta = %s
            """
            
            cursor.execute(sql_productos, (venta_id,))
            productos = cursor.fetchall()
            
            venta['productos'] = productos
            
            return venta
            
        except Exception as e:
            print(f"Error en obtener_venta_para_factura: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_ultimo_ticket():
        """Obtener el último número de ticket"""
        # (Mantener igual)
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT COALESCE(MAX(numero_venta), 0) as ultimo_numero FROM ventas")
            resultado = cursor.fetchone()
            return (resultado['ultimo_numero'] if resultado else 0) + 1
            
        except Exception as e:
            print(f"Error en obtener_ultimo_ticket: {str(e)}")
            return 1
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()