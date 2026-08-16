"""
Controlador para gestión de clientes y proveedores - VERSIÓN COMPLETA CORREGIDA
"""
from datetime import date, datetime, timedelta
import decimal
import os
from flask import Blueprint, request, jsonify, render_template
from modelo.cliente_proveedor_modelo import ClienteProveedorModel
from database import db
import logging

logger = logging.getLogger(__name__)

cliente_proveedor_bp = Blueprint('cliente_proveedor', __name__)

# ===== FUNCIONES AUXILIARES =====

def serializar_datos(datos):
    """Recursivamente serializar datos para JSON - VERSIÓN CORREGIDA"""
    if isinstance(datos, dict):
        return {k: serializar_datos(v) for k, v in datos.items()}
    elif isinstance(datos, list):
        return [serializar_datos(v) for v in datos]
    elif isinstance(datos, (datetime, date)):
        return datos.isoformat()
    elif isinstance(datos, timedelta):  # NUEVO: Manejar timedelta
        return str(datos)
    elif isinstance(datos, decimal.Decimal):
        return float(datos)
    elif hasattr(datos, 'isoformat'):
        return datos.isoformat()
    else:
        return datos

# ===== RUTA DE DEBUG =====

@cliente_proveedor_bp.route('/debug/tablas', methods=['GET'])
def debug_tablas():
    """Verificar estructura de tablas"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Verificar estructura de tabla proveedor
        cursor.execute("DESCRIBE proveedor")
        estructura_proveedor = cursor.fetchall()
        
        # Verificar estructura de tabla cliente
        cursor.execute("DESCRIBE cliente")
        estructura_cliente = cursor.fetchall()
        
        # Verificar estructura de tabla productos
        cursor.execute("DESCRIBE productos")
        estructura_productos = cursor.fetchall()
        
        # Verificar datos de muestra
        cursor.execute("SELECT * FROM proveedor LIMIT 5")
        muestra_proveedores = cursor.fetchall()
        
        cursor.execute("SELECT * FROM cliente LIMIT 5")
        muestra_clientes = cursor.fetchall()
        
        cursor.execute("SELECT COUNT(*) as total FROM ventas WHERE cliente_cedula IS NOT NULL")
        ventas_con_cliente = cursor.fetchone()
        
        # Verificar si hay productos relacionados con proveedores
        cursor.execute("""
            SELECT p.nombre, p.proveedor, pr.nombre_empresa 
            FROM productos p 
            LEFT JOIN proveedor pr ON p.proveedor = pr.telefono 
            WHERE p.proveedor IS NOT NULL 
            LIMIT 5
        """)
        productos_proveedores = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'proveedor_estructura': estructura_proveedor,
            'cliente_estructura': estructura_cliente,
            'productos_estructura': estructura_productos,
            'muestra_proveedores': muestra_proveedores,
            'muestra_clientes': muestra_clientes,
            'productos_proveedores': productos_proveedores,
            'ventas_con_cliente': ventas_con_cliente['total'] if ventas_con_cliente else 0
        })
        
    except Exception as e:
        logger.error(f"Error en debug_tablas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

# ===== RUTAS PARA OBTENER VENTA =====

@cliente_proveedor_bp.route('/venta/<int:venta_id>', methods=['GET'])
def obtener_venta(venta_id):
    """Obtener información de una venta específica"""
    try:
        logger.info(f"Solicitando venta: {venta_id}")
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                v.*,
                c.nombre as cliente_nombre,
                c.cedula as cliente_cedula,
                DATE(v.fecha_dia) as fecha_dia_str
            FROM ventas v
            LEFT JOIN cliente c ON v.cliente_cedula = c.cedula
            WHERE v.id = %s
        """, (venta_id,))
        
        venta = cursor.fetchone()
        
        # Intentar obtener productos de la venta (si existe la tabla detalle_venta)
        try:
            cursor.execute("""
                SELECT p.nombre, dv.cantidad_vendida
                FROM detalle_venta dv
                JOIN productos p ON dv.id_producto = p.id
                WHERE dv.id_venta = %s
            """, (venta_id,))
            
            detalles = cursor.fetchall()
            
            if detalles:
                productos_text = []
                for detalle in detalles:
                    productos_text.append(f"{detalle['nombre']} x{detalle['cantidad_vendida']}")
                venta['productos'] = ", ".join(productos_text)
            else:
                venta['productos'] = "Sin información"
        except:
            venta['productos'] = "Sin información"
        
        cursor.close()
        conn.close()
        
        if venta:
            return jsonify({
                'success': True,
                'venta': serializar_datos(venta)
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Venta {venta_id} no encontrada'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener venta: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener venta: {str(e)}"
        }), 500

# ===== RUTAS PARA CLIENTES =====

@cliente_proveedor_bp.route('/clientes', methods=['GET'])
def obtener_clientes():
    """Obtener lista de clientes con filtros y paginación"""
    try:
        logger.info(f"Solicitando clientes con parámetros: {request.args}")
        
        # Parámetros de filtro
        busqueda = request.args.get('busqueda', '')
        estado = request.args.get('estado')
        deuda = request.args.get('deuda')
        
        # Parámetros de paginación
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        # Obtener clientes
        resultado = ClienteProveedorModel.obtener_clientes(
            busqueda=busqueda,
            estado=estado,
            deuda=deuda,
            limit=per_page,
            offset=offset
        )
        
        logger.info(f"Encontrados {len(resultado.get('clientes', []))} clientes (total: {resultado.get('total', 0)})")
        
        return jsonify({
            'success': True,
            'clientes': resultado.get('clientes', []),
            'total': resultado.get('total', 0),
            'page': page,
            'per_page': per_page,
            'total_pages': (resultado.get('total', 0) + per_page - 1) // per_page if resultado.get('total', 0) > 0 else 1
        })
        
    except Exception as e:
        logger.error(f"Error al obtener clientes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener clientes: {str(e)}",
            'clientes': [],
            'total': 0
        }), 500

@cliente_proveedor_bp.route('/estadisticas', methods=['GET'])
def obtener_estadisticas_clientes():
    """Obtener estadísticas globales de clientes y deuda"""
    try:
        logger.info("Solicitando estadísticas globales de clientes")
        estadisticas = ClienteProveedorModel.obtener_estadisticas_globales()
        return jsonify({
            'success': True,
            'estadisticas': estadisticas
        })
    except Exception as e:
        logger.error(f"Error al obtener estadísticas globales: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener estadísticas globales: {str(e)}",
            'estadisticas': {
                'total_clientes': 0,
                'deuda_total': 0,
                'clientes_morosos': 0
            }
        }), 500

@cliente_proveedor_bp.route('/cliente/<cedula>', methods=['GET'])
def obtener_cliente(cedula):
    """Obtener información de un cliente específico"""
    try:
        logger.info(f"Solicitando cliente con cédula: {cedula}")
        
        cliente = ClienteProveedorModel.obtener_cliente_por_cedula(cedula)
        
        if cliente:
            return jsonify({
                'success': True,
                'cliente': cliente
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Cliente con cédula {cedula} no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener cliente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener cliente: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/cliente', methods=['POST'])
def crear_cliente():
    """Crear un nuevo cliente"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Creando cliente con datos: {data}")
        
        # Validar datos requeridos
        if not data.get('cedula'):
            return jsonify({
                'success': False,
                'message': 'Cédula es requerida'
            }), 400
        
        if not data.get('nombre'):
            return jsonify({
                'success': False,
                'message': 'Nombre es requerido'
            }), 400
        
        # Crear cliente SIN fecha_creacion (la BD usará DEFAULT CURRENT_TIMESTAMP)
        success, message = ClienteProveedorModel.crear_cliente(
            cedula=data['cedula'],
            nombre=data['nombre'],
            telefono=data.get('telefono'),
            correo=data.get('correo'),
            direccion=data.get('direccion')
            # No enviar fecha_creacion - dejar que MySQL use el DEFAULT
        )
        
        if success:
            logger.info(f"Cliente creado exitosamente: {data['cedula']}")
            return jsonify({
                'success': True,
                'message': message,
                'cedula': data['cedula']
            })
        else:
            logger.warning(f"Error al crear cliente: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al crear cliente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al crear cliente: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/cliente/<cedula>', methods=['PUT'])
def actualizar_cliente(cedula):
    """Actualizar información de un cliente"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Actualizando cliente {cedula} con datos: {data}")
        
        # Validar datos requeridos
        if not data.get('cedula'):
            return jsonify({
                'success': False,
                'message': 'Cédula es requerida'
            }), 400
        
        if not data.get('nombre'):
            return jsonify({
                'success': False,
                'message': 'Nombre es requerido'
            }), 400
        
        # Actualizar cliente
        success, message = ClienteProveedorModel.actualizar_cliente(
            cedula_original=cedula,
            cedula=data['cedula'],
            nombre=data['nombre'],
            telefono=data.get('telefono'),
            correo=data.get('correo'),
            direccion=data.get('direccion')
        )
        
        if success:
            logger.info(f"Cliente actualizado exitosamente: {cedula}")
            return jsonify({
                'success': True,
                'message': message,
                'nueva_cedula': data['cedula'] if data['cedula'] != cedula else cedula
            })
        else:
            logger.warning(f"Error al actualizar cliente: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al actualizar cliente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al actualizar cliente: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/cliente/<cedula>', methods=['DELETE'])
def eliminar_cliente(cedula):
    """Eliminar un cliente"""
    try:
        logger.info(f"Intentando eliminar cliente: {cedula}")
        
        success, message = ClienteProveedorModel.eliminar_cliente(cedula)
        
        if success:
            logger.info(f"Cliente eliminado exitosamente: {cedula}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al eliminar cliente: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al eliminar cliente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al eliminar cliente: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/cliente/<cedula>/historial', methods=['GET'])
def obtener_historial_cliente(cedula):
    """Obtener historial completo de un cliente"""
    try:
        logger.info(f"Solicitando historial del cliente: {cedula}")
        
        historial = ClienteProveedorModel.obtener_historial_cliente(cedula)
        
        if historial:
            return jsonify({
                'success': True,
                'historial': historial
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Cliente con cédula {cedula} no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener historial: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener historial: {str(e)}"
        }), 500

# ===== NUEVA RUTA PARA VENTA MANUAL =====

@cliente_proveedor_bp.route('/cliente/<cedula>/venta-manual', methods=['POST'])
def crear_venta_manual_cliente(cedula):
    """Crear una venta manual a crédito para un cliente"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Creando venta manual para cliente {cedula}: {data}")
        
        # Validar datos requeridos
        required_fields = ['fecha', 'productos', 'total']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        # Crear venta manual
        success, result = ClienteProveedorModel.crear_venta_manual_cliente(
            cedula=cedula,
            fecha=data['fecha'],
            productos=data['productos'],
            total=data['total'],
            anticipo=data.get('anticipo', 0),
            dias_credito=data.get('dias_credito', 30),
            observaciones=data.get('observaciones', '')
        )
        
        if success:
            logger.info(f"Venta manual creada exitosamente para cliente {cedula}")
            return jsonify({
                'success': True,
                'message': 'Venta manual registrada exitosamente',
                'venta_id': result.get('venta_id'),
                'numero_venta': result.get('numero_venta'),
                'credito_id': result.get('credito_id')
            })
        else:
            logger.warning(f"Error al crear venta manual: {result}")
            return jsonify({
                'success': False,
                'message': result
            }), 400
            
    except Exception as e:
        logger.error(f"Error al crear venta manual: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500

# ===== NUEVAS RUTAS PARA ELIMINAR VENTAS Y CRÉDITOS =====

@cliente_proveedor_bp.route('/venta/<int:venta_id>', methods=['DELETE'])
def eliminar_venta(venta_id):
    """Eliminar una venta específica"""
    try:
        logger.info(f"Intentando eliminar venta: {venta_id}")
        
        success, message = ClienteProveedorModel.eliminar_venta(venta_id)
        
        if success:
            logger.info(f"Venta eliminada exitosamente: {venta_id}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al eliminar venta: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al eliminar venta: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al eliminar venta: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/credito/<int:credito_id>', methods=['DELETE'])
def eliminar_credito(credito_id):
    """Eliminar un crédito específico"""
    try:
        logger.info(f"Intentando eliminar crédito: {credito_id}")
        
        success, message = ClienteProveedorModel.eliminar_credito(credito_id)
        
        if success:
            logger.info(f"Crédito eliminado exitosamente: {credito_id}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al eliminar crédito: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al eliminar crédito: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al eliminar crédito: {str(e)}"
        }), 500

# ===== RUTAS PARA CRÉDITOS =====

@cliente_proveedor_bp.route('/cliente/<cedula>/creditos', methods=['GET'])
def obtener_creditos_cliente(cedula):
    """Obtener créditos de un cliente"""
    try:
        logger.info(f"Solicitando créditos del cliente: {cedula}")
        
        creditos = ClienteProveedorModel.obtener_creditos_cliente(cedula)
        
        return jsonify({
            'success': True,
            'creditos': creditos,
            'total': len(creditos)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener créditos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener créditos: {str(e)}",
            'creditos': []
        }), 500

@cliente_proveedor_bp.route('/credito/<int:credito_id>', methods=['GET'])
def obtener_credito(credito_id):
    """Obtener información de un crédito específico con detalles de venta"""
    try:
        logger.info(f"Solicitando crédito: {credito_id}")
        
        # Usar obtener_credito_con_detalle para traer también los productos
        credito = ClienteProveedorModel.obtener_credito_con_detalle(credito_id)
        
        if credito:
            return jsonify({
                'success': True,
                'credito': credito
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Crédito {credito_id} no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener crédito: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener crédito: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/credito/<int:credito_id>', methods=['PUT'])
def actualizar_credito(credito_id):
    """Actualizar información de un crédito - VERSIÓN CORREGIDA"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Actualizando crédito {credito_id} con datos: {data}")
        
        # Validar datos requeridos
        required_fields = ['anticipo', 'saldo_pendiente', 'dias_credito', 'fecha_vencimiento', 'estado']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        success, message = ClienteProveedorModel.actualizar_credito(credito_id, data)
        
        if success:
            logger.info(f"Crédito actualizado exitosamente: {credito_id}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al actualizar crédito: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al actualizar crédito: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al actualizar crédito: {str(e)}"
        }), 500

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

@cliente_proveedor_bp.route('/proveedores', methods=['GET'])
def obtener_proveedores():
    """Obtener lista de proveedores con filtros y paginación"""
    try:
        logger.info(f"Solicitando proveedores con parámetros: {request.args}")
        
        # Parámetros de filtro
        busqueda = request.args.get('busqueda', '')
        estado = request.args.get('estado')
        
        # Parámetros de paginación
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        offset = (page - 1) * per_page
        
        # Obtener proveedores
        resultado = ClienteProveedorModel.obtener_proveedores(
            busqueda=busqueda,
            estado=estado,
            limit=per_page,
            offset=offset
        )
        
        logger.info(f"Encontrados {len(resultado.get('proveedores', []))} proveedores (total: {resultado.get('total', 0)})")
        
        return jsonify({
            'success': True,
            'proveedores': resultado.get('proveedores', []),
            'total': resultado.get('total', 0),
            'page': page,
            'per_page': per_page,
            'total_pages': (resultado.get('total', 0) + per_page - 1) // per_page if resultado.get('total', 0) > 0 else 1
        })
        
    except Exception as e:
        logger.error(f"Error al obtener proveedores: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener proveedores: {str(e)}",
            'proveedores': [],
            'total': 0
        }), 500

@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['GET'])
def obtener_proveedor(telefono):
    """Obtener información de un proveedor específico"""
    try:
        logger.info(f"Solicitando proveedor con teléfono: {telefono}")
        
        proveedor = ClienteProveedorModel.obtener_proveedor_por_telefono(telefono)
        
        if proveedor:
            return jsonify({
                'success': True,
                'proveedor': proveedor
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Proveedor con teléfono {telefono} no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener proveedor: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener proveedor: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/proveedor/completo', methods=['POST'])
def crear_proveedor_completo():
    """Crear un nuevo proveedor con productos"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Creando proveedor completo con datos: {data}")
        
        # Validar datos requeridos
        if not data.get('telefono'):
            return jsonify({
                'success': False,
                'message': 'Teléfono es requerido'
            }), 400
        
        if not data.get('nombre_empresa'):
            return jsonify({
                'success': False,
                'message': 'Nombre de empresa es requerido'
            }), 400
        
        if not data.get('nombre_proveedor'):
            return jsonify({
                'success': False,
                'message': 'Nombre del proveedor es requerido'
            }), 400
        
        # Extraer productos si se proporcionaron
        productos = data.get('productos', '')
        
        # Crear proveedor con productos
        success, message = ClienteProveedorModel.crear_proveedor_con_productos(
            telefono=data['telefono'],
            nombre_empresa=data['nombre_empresa'],
            nombre_proveedor=data['nombre_proveedor'],
            correo=data.get('correo'),
            estado=data.get('estado', 'activo'),
            productos=productos
        )
        
        if success:
            logger.info(f"Proveedor creado exitosamente: {data['telefono']}")
            return jsonify({
                'success': True,
                'message': message,
                'telefono': data['telefono']
            })
        else:
            logger.warning(f"Error al crear proveedor: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al crear proveedor completo: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al crear proveedor: {str(e)}"
        }), 500
    
@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['PUT'])
def actualizar_proveedor(telefono):
    """Actualizar información de un proveedor"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Actualizando proveedor {telefono} con datos: {data}")
        
        # Validar datos requeridos
        if not data.get('telefono'):
            return jsonify({
                'success': False,
                'message': 'Teléfono es requerido'
            }), 400
        
        if not data.get('nombre_empresa'):
            return jsonify({
                'success': False,
                'message': 'Nombre de empresa es requerido'
            }), 400
        
        if not data.get('nombre_proveedor'):
            return jsonify({
                'success': False,
                'message': 'Nombre del proveedor es requerido'
            }), 400
        
        # Extraer productos si se proporcionaron
        productos = data.get('productos', None)
        
        # Actualizar proveedor con producto
        success, message = ClienteProveedorModel.actualizar_proveedor(
            telefono_original=telefono,
            telefono=data['telefono'],
            nombre_empresa=data['nombre_empresa'],
            nombre_proveedor=data['nombre_proveedor'],
            correo=data.get('correo'),
            estado=data.get('estado', 'activo'),
            producto=productos
        )
        
        if success:
            logger.info(f"Proveedor actualizado exitosamente: {telefono}")
            return jsonify({
                'success': True,
                'message': message,
                'nuevo_telefono': data['telefono'] if data['telefono'] != telefono else telefono
            })
        else:
            logger.warning(f"Error al actualizar proveedor: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al actualizar proveedor: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al actualizar proveedor: {str(e)}"
        }), 500
    
@cliente_proveedor_bp.route('/proveedor/<telefono>', methods=['DELETE'])
def eliminar_proveedor(telefono):
    """Eliminar un proveedor"""
    try:
        logger.info(f"Intentando eliminar proveedor: {telefono}")
        
        success, message = ClienteProveedorModel.eliminar_proveedor(telefono)
        
        if success:
            logger.info(f"Proveedor eliminado exitosamente: {telefono}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al eliminar proveedor: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al eliminar proveedor: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al eliminar proveedor: {str(e)}"
        }), 500

@cliente_proveedor_bp.route('/proveedor/<telefono>/historial', methods=['GET'])
def obtener_historial_proveedor(telefono):
    """Obtener historial completo de un proveedor"""
    try:
        logger.info(f"Solicitando historial del proveedor: {telefono}")
        
        historial = ClienteProveedorModel.obtener_historial_proveedor(telefono)
        
        if historial:
            return jsonify({
                'success': True,
                'historial': historial
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Proveedor con teléfono {telefono} no encontrado'
            }), 404
            
    except Exception as e:
        logger.error(f"Error al obtener historial: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener historial: {str(e)}"
        }), 500

# ===== NUEVAS RUTAS PARA GESTIÓN DE PRODUCTOS DE PROVEEDORES =====

@cliente_proveedor_bp.route('/productos/disponibles', methods=['GET'])
def obtener_productos_disponibles():
    """Obtener productos disponibles para asignar a proveedores"""
    try:
        logger.info("Solicitando productos disponibles para proveedores")
        
        productos = ClienteProveedorModel.obtener_productos_para_asignar()
        
        return jsonify({
            'success': True,
            'productos': productos,
            'total': len(productos)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener productos disponibles: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener productos disponibles: {str(e)}",
            'productos': []
        }), 500

@cliente_proveedor_bp.route('/proveedor/<telefono>/productos', methods=['GET'])
def obtener_productos_proveedor(telefono):
    """Obtener productos asignados a un proveedor"""
    try:
        logger.info(f"Solicitando productos del proveedor: {telefono}")
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT p.id, p.nombre, p.categoria, p.presentacion, p.precio_costo
        FROM productos p
        WHERE p.proveedor = %s
        ORDER BY p.nombre
        """
        
        cursor.execute(sql, (telefono,))
        productos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Serializar datos
        productos = serializar_datos(productos)
        
        return jsonify({
            'success': True,
            'productos': productos,
            'total': len(productos)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener productos del proveedor: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener productos: {str(e)}",
            'productos': []
        }), 500

@cliente_proveedor_bp.route('/proveedor/<telefono>/asignar-productos', methods=['POST'])
def asignar_productos_proveedor(telefono):
    """Asignar productos a un proveedor"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Asignando productos al proveedor {telefono}: {data}")
        
        ids_productos = data.get('productos_ids', [])
        
        if not ids_productos:
            return jsonify({
                'success': False,
                'message': 'No se proporcionaron IDs de productos'
            }), 400
        
        success, message = ClienteProveedorModel.asignar_productos_a_proveedor(telefono, ids_productos)
        
        if success:
            logger.info(f"Productos asignados exitosamente al proveedor {telefono}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al asignar productos: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al asignar productos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al asignar productos: {str(e)}"
        }), 500

# ===== RUTA PARA LA VISTA PRINCIPAL =====

@cliente_proveedor_bp.route('/gestion', methods=['GET'])
def gestion_clientes_proveedores():
    """Renderizar la vista principal de gestión"""
    try:
        # Buscar el archivo HTML
        posibles_rutas = [
            'vista/clientes_proveedores.html',
            'templates/clientes_proveedores.html',
            'vista/gestion_clientes.html'
        ]
        
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                logger.info(f"Sirviendo vista desde: {ruta}")
                with open(ruta, 'r', encoding='utf-8') as f:
                    return f.read()
        
        # Vista por defecto si no encuentra el archivo
        logger.warning("No se encontró el archivo HTML de clientes/proveedores")
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Gestión de Clientes y Proveedores</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                .container { max-width: 1200px; margin: 0 auto; }
                h1 { color: #2c3e50; }
                .api-info { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
                .endpoint { margin: 10px 0; padding: 10px; background: white; border-left: 4px solid #3498db; }
                code { background: #eef; padding: 2px 5px; border-radius: 3px; }
                .debug-btn { 
                    display: inline-block; 
                    padding: 10px 15px; 
                    margin: 5px; 
                    background: #17a2b8; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Gestión de Clientes y Proveedores</h1>
                <p>Esta funcionalidad está configurada correctamente en el backend.</p>
                
                <div style="margin: 20px 0;">
                    <a href="/clientes-proveedores/debug/tablas" class="debug-btn">🔧 Debug Tablas</a>
                    <a href="/clientes-proveedores/test" class="debug-btn">🧪 Test API</a>
                    <a href="/api/debug/estado" class="debug-btn">📊 Estado Sistema</a>
                </div>
                
                <div class="api-info">
                    <h2>API Endpoints Disponibles</h2>
                    
                    <h3>Clientes</h3>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/clientes</code> - Listar clientes
                    </div>
                    <div class="endpoint">
                        <code>POST /clientes-proveedores/cliente</code> - Crear cliente
                    </div>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/cliente/[cedula]</code> - Obtener cliente
                    </div>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/cliente/[cedula]/historial</code> - Historial cliente
                    </div>
                    <div class="endpoint">
                        <code>POST /clientes-proveedores/cliente/[cedula]/venta-manual</code> - Nueva venta manual
                    </div>
                    
                    <h3>Proveedores</h3>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/proveedores</code> - Listar proveedores
                    </div>
                    <div class="endpoint">
                        <code>POST /clientes-proveedores/proveedor/completo</code> - Crear proveedor con productos
                    </div>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/proveedor/[telefono]</code> - Obtener proveedor
                    </div>
                    <div class="endpoint">
                        <code>GET /clientes-proveedores/proveedor/[telefono]/historial</code> - Historial proveedor
                    </div>
                    
                    <p><strong>Nota:</strong> Asegúrate de que el archivo <code>clientes_proveedores.html</code> existe en la carpeta <code>vista/</code></p>
                </div>
                
                <a href="/">← Volver al inicio</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error al servir vista de gestión: {str(e)}")
        return f"Error: {str(e)}", 500

# ===== RUTA DE PRUEBA PARA VERIFICAR QUE EL BLUEPRINT FUNCIONA =====

@cliente_proveedor_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint de prueba para verificar que el blueprint funciona"""
    return jsonify({
        'success': True,
        'message': 'Blueprint de clientes/proveedores funcionando correctamente',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'debug': '/clientes-proveedores/debug/tablas',
            'clientes': '/clientes-proveedores/clientes',
            'proveedores': '/clientes-proveedores/proveedores',
            'productos_disponibles': '/clientes-proveedores/productos/disponibles',
            'venta_manual': '/clientes-proveedores/cliente/[cedula]/venta-manual',
            'test': '/clientes-proveedores/test'
        }
    })


@cliente_proveedor_bp.route('/credito/<int:credito_id>/abonos', methods=['GET'])
def obtener_abonos_credito(credito_id):
    """Obtener historial de abonos de un crédito"""
    try:
        logger.info(f"Solicitando historial de abonos para crédito: {credito_id}")
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT 
            a.id,
            a.monto,
            a.fecha,
            a.metodo_pago,
            a.referencia,
            a.usuario_registra,
            a.observacion,
            a.fecha_registro,
            c.cliente_cedula,
            cl.nombre as cliente_nombre,
            v.numero_venta
        FROM abonos a
        INNER JOIN creditos c ON a.credito_id = c.id
        INNER JOIN cliente cl ON a.cliente_cedula = cl.cedula
        LEFT JOIN ventas v ON a.venta_id = v.id
        WHERE a.credito_id = %s
        ORDER BY a.fecha DESC, a.fecha_registro DESC
        """
        
        cursor.execute(sql, (credito_id,))
        abonos = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Serializar datos
        abonos = serializar_datos(abonos)
        
        return jsonify({
            'success': True,
            'abonos': abonos,
            'total': len(abonos),
            'credito_id': credito_id
        })
        
    except Exception as e:
        logger.error(f"Error al obtener abonos del crédito: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener abonos: {str(e)}",
            'abonos': []
        }), 500


@cliente_proveedor_bp.route('/cliente/<cedula>/abonos', methods=['GET'])
def obtener_abonos_cliente(cedula):
    """Obtener todos los abonos de un cliente"""
    try:
        logger.info(f"Solicitando abonos del cliente: {cedula}")
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT 
            a.id,
            a.credito_id,
            a.venta_id,
            a.monto,
            a.fecha,
            a.metodo_pago,
            a.referencia,
            a.usuario_registra,
            a.observacion,
            a.fecha_registro,
            v.numero_venta,
            c.saldo_pendiente as saldo_credito_actual,
            c.estado as estado_credito
        FROM abonos a
        INNER JOIN creditos c ON a.credito_id = c.id
        LEFT JOIN ventas v ON a.venta_id = v.id
        WHERE a.cliente_cedula = %s
        ORDER BY a.fecha DESC, a.fecha_registro DESC
        """
        
        cursor.execute(sql, (cedula,))
        abonos = cursor.fetchall()
        
        # Calcular total abonado
        total_abonado = sum(float(a['monto']) for a in abonos) if abonos else 0
        
        cursor.close()
        conn.close()
        
        # Serializar datos
        abonos = serializar_datos(abonos)
        
        return jsonify({
            'success': True,
            'abonos': abonos,
            'total_abonos': len(abonos),
            'total_abonado': total_abonado,
            'cliente_cedula': cedula
        })
        
    except Exception as e:
        logger.error(f"Error al obtener abonos del cliente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al obtener abonos: {str(e)}",
            'abonos': []
        }), 500

# Agregar al final del controlador, antes de @cliente_proveedor_bp.route('/gestion', methods=['GET'])

@cliente_proveedor_bp.route('/credito/<int:credito_id>/abono', methods=['POST'])
def registrar_abono(credito_id):
    """Registrar un abono a un crédito"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
        
        logger.info(f"Registrando abono para crédito {credito_id}: {data}")
        
        monto_abono = float(data.get('monto_abono', 0))
        fecha_abono = data.get('fecha_abono')
        hora_abono = data.get('hora_abono')
        observaciones = data.get('observaciones', '')
        
        if monto_abono <= 0:
            return jsonify({
                'success': False,
                'message': 'El monto del abono debe ser mayor a 0'
            }), 400
        
        success, message = ClienteProveedorModel.registrar_abono_credito(
            credito_id=credito_id,
            monto_abono=monto_abono,
            fecha_abono=fecha_abono,
            hora_abono=hora_abono,
            metodo_pago='efectivo',
            usuario_registra='SISTEMA',
            observaciones=observaciones
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'nuevo_saldo': None  # Se puede obtener del modelo si es necesario
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al registrar abono: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}"
        }), 500