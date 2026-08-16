"""
Controlador para gestión de clientes y proveedores - VERSIÓN CORREGIDA
"""
from datetime import datetime
import os
from flask import Blueprint, request, jsonify, render_template
from modelo.cliente_proveedor_modelo import ClienteProveedorModel
from database import db
import logging

logger = logging.getLogger(__name__)

cliente_proveedor_bp = Blueprint('cliente_proveedor', __name__)

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
        
        # Crear cliente
        success, message = ClienteProveedorModel.crear_cliente(
            cedula=data['cedula'],
            nombre=data['nombre'],
            telefono=data.get('telefono'),
            correo=data.get('correo'),
            direccion=data.get('direccion')
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
    """Obtener información de un crédito específico"""
    try:
        logger.info(f"Solicitando crédito: {credito_id}")
        
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT c.*, v.numero_venta, v.total as monto_venta
            FROM creditos c
            LEFT JOIN ventas v ON c.venta_id = v.id
            WHERE c.id = %s
        """, (credito_id,))
        
        credito = cursor.fetchone()
        cursor.close()
        conn.close()
        
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
    """Actualizar información de un crédito"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Actualizando crédito {credito_id} con datos: {data}")
        
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

@cliente_proveedor_bp.route('/credito/<int:credito_id>/abono', methods=['POST'])
def registrar_abono_credito(credito_id):
    """Registrar un abono a un crédito"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Registrando abono para crédito {credito_id}: {data}")
        
        # Validar datos
        if not data.get('monto_abono'):
            return jsonify({
                'success': False,
                'message': 'Monto del abono es requerido'
            }), 400
        
        success, message = ClienteProveedorModel.registrar_abono_credito(
            credito_id=credito_id,
            monto_abono=data['monto_abono'],
            fecha_abono=data.get('fecha_abono'),
            observaciones=data.get('observaciones', '')
        )
        
        if success:
            logger.info(f"Abono registrado exitosamente para crédito: {credito_id}")
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            logger.warning(f"Error al registrar abono: {message}")
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error al registrar abono: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al registrar abono: {str(e)}"
        }), 500

# ===== RUTAS PARA PROVEEDORES =====

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

@cliente_proveedor_bp.route('/proveedor', methods=['POST'])
def crear_proveedor():
    """Crear un nuevo proveedor"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No se recibieron datos JSON'
            }), 400
            
        logger.info(f"Creando proveedor con datos: {data}")
        
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
        
        # Crear proveedor
        success, message = ClienteProveedorModel.crear_proveedor(
            telefono=data['telefono'],
            nombre_empresa=data['nombre_empresa'],
            nombre_proveedor=data['nombre_proveedor'],
            correo=data.get('correo'),
            estado=data.get('estado', 'activo')
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
        logger.error(f"Error al crear proveedor: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error al crear proveedor: {str(e)}"
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
        
        # Extraer productos si se proporcionaron (ahora es campo 'productos' del JSON)
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
        
        # Extraer productos si se proporcionaron (ahora es campo 'productos' del JSON)
        productos = data.get('productos', None)
        
        # Actualizar proveedor con producto
        success, message = ClienteProveedorModel.actualizar_proveedor(
            telefono_original=telefono,
            telefono=data['telefono'],
            nombre_empresa=data['nombre_empresa'],
            nombre_proveedor=data['nombre_proveedor'],
            correo=data.get('correo'),
            estado=data.get('estado', 'activo'),
            producto=productos  # Cambié de 'producto' a 'productos' para coincidir con el frontend
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
        from modelo.cliente_proveedor_modelo import serializar_datos
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
            'test': '/clientes-proveedores/test'
        }
    })