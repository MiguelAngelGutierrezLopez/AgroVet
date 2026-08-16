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
            
            # 3. Insertar venta principal (SIN CAMPO ANTICIPO)
            sql_venta = """
            INSERT INTO ventas 
            (numero_venta, fecha_dia, fecha_hora, nombre_cliente, direccion_cliente, 
             telefono_cliente, tipo_pago, cliente_cedula, subtotal, descuento, total,
             dias_credito, submetodo_banco, usuario_id, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            fecha_actual = date.today()
            hora_actual = datetime.now().time()
            anticipo_venta = datos_venta.get('anticipo', 0)
            
            # Obtener ID de usuario (puedes ajustar esto según tu sistema)
            usuario_id = 1  # Valor por defecto, deberías obtenerlo de la sesión
            
            cursor.execute(sql_venta, (
                numero_venta,
                fecha_actual,
                hora_actual,
                nombre_cliente_completo,
                direccion_cliente,
                telefono_cliente,
                datos_venta['metodo_pago'],
                cliente_cedula,
                datos_venta['subtotal'],
                datos_venta.get('descuento', 0),
                datos_venta['total'],
                datos_venta.get('dias_credito'),
                datos_venta.get('submetodo_banco'),
                usuario_id,
                'completada'
            ))
            
            venta_id = cursor.lastrowid
            
            # 4. Insertar productos en detalle_venta
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
            
            # 5. SI ES VENTA A CRÉDITO, CREAR REGISTRO EN TABLA CRÉDITOS
            if datos_venta['metodo_pago'] == 'credito' and cliente_cedula:
                total_venta = float(datos_venta['total'])
                deuda_inicial = total_venta - float(anticipo_venta)
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
                
                print(f"DEBUG - Crédito creado: Venta {venta_id}, Cliente {cliente_cedula}, Deuda: {deuda_inicial}")
            
            # 6. SI ES VENTA AL CONTADO CON DINERO ENTREGADO
            elif datos_venta['metodo_pago'] == 'contado':
                # Registrar cambio si aplica (esto se maneja en la factura)
                dinero_entregado = datos_venta.get('dinero_entregado', datos_venta['total'])
                cambio = float(dinero_entregado) - float(datos_venta['total'])
                if cambio > 0:
                    print(f"DEBUG - Venta contado con cambio: {cambio}")
            
            conn.commit()
            print(f"DEBUG - Transacción completada: Venta ID {venta_id}")
            
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
    def obtener_ultimo_ticket():
        """Obtener el último número de ticket"""
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
    
    @staticmethod
    def obtener_venta_para_factura(venta_id):
        """Obtener una venta completa para factura con información de crédito"""
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
            
            # Obtener información de crédito si existe
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