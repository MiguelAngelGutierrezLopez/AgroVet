from flask import Blueprint, request, jsonify
from modelo.producto_model import ProductoModel
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Crear blueprint para productos
productos_bp = Blueprint('productos', __name__, url_prefix='/api/productos')

# ============================================
# RUTAS API PARA PRODUCTOS
# ============================================

@productos_bp.route('/proveedores', methods=['GET'])
def obtener_proveedores():
    """Obtener lista de proveedores"""
    try:
        logger.info("Obteniendo lista de proveedores")
        
        proveedores = ProductoModel.obtener_proveedores()
        
        # Formatear para el select (mostrar empresa + nombre del contacto)
        proveedores_formateados = [
            {
                'telefono': p['telefono'],
                'nombre': f"{p['nombre_empresa']} - {p['nombre_proveedor']}"
            }
            for p in proveedores
        ]
        
        return jsonify({
            'success': True,
            'proveedores': proveedores_formateados
        })
        
    except Exception as e:
        logger.error(f"Error al obtener proveedores: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener proveedores: {str(e)}'
        }), 500
    
@productos_bp.route('/', methods=['GET'])
def obtener_productos():
    """Obtener todos los productos con filtros"""
    try:
        # Obtener parámetros de filtro
        busqueda = request.args.get('busqueda', '')
        categoria = request.args.get('categoria', '')
        estado = request.args.get('estado', '')
        stock = request.args.get('stock', '')
        
        filtros = {}
        if busqueda:
            filtros['busqueda'] = busqueda
        if categoria:
            filtros['categoria'] = categoria
        if estado:
            filtros['estado'] = estado
        if stock:
            filtros['stock'] = stock
        
        logger.info(f"Obteniendo productos con filtros: {filtros}")
        
        # Obtener productos del modelo actualizado
        productos = ProductoModel.obtener_todos_productos(filtros)
        
        return jsonify({
            'success': True,
            'productos': productos,
            'total': len(productos)
        })
        
    except Exception as e:
        logger.error(f"Error al obtener productos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener productos: {str(e)}'
        }), 500

@productos_bp.route('/<int:producto_id>', methods=['GET'])
def obtener_producto(producto_id):
    """Obtener un producto específico por ID"""
    try:
        logger.info(f"Obteniendo producto ID: {producto_id}")
        
        producto = ProductoModel.obtener_producto_por_id(producto_id)
        
        if not producto:
            return jsonify({
                'success': False,
                'message': 'Producto no encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'producto': producto
        })
        
    except Exception as e:
        logger.error(f"Error al obtener producto: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener producto: {str(e)}'
        }), 500

@productos_bp.route('/', methods=['POST'])
def crear_producto():
    """Crear un nuevo producto"""
    try:
        datos = request.get_json()
        logger.info(f"Creando nuevo producto: {datos.get('nombre', 'Sin nombre')}")
        
        # Validar datos requeridos
        if not datos or 'nombre' not in datos:
            return jsonify({
                'success': False,
                'message': 'El nombre del producto es requerido'
            }), 400
        
        if 'categoria' not in datos:
            return jsonify({
                'success': False,
                'message': 'La categoría del producto es requerida'
            }), 400
        
        # Validar precios
        if 'precio_venta' in datos:
            try:
                precio_venta = float(datos['precio_venta'])
                if precio_venta < 0:
                    return jsonify({
                        'success': False,
                        'message': 'El precio de venta no puede ser negativo'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Precio de venta inválido'
                }), 400
        
        if 'precio_costo' in datos:
            try:
                precio_costo = float(datos['precio_costo'])
                if precio_costo < 0:
                    return jsonify({
                        'success': False,
                        'message': 'El precio de costo no puede ser negativo'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Precio de costo inválido'
                }), 400
        
        # Validar cantidad
        if 'cantidad' in datos:
            try:
                cantidad = int(datos['cantidad'])
                if cantidad < 0:
                    return jsonify({
                        'success': False,
                        'message': 'La cantidad no puede ser negativa'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Cantidad inválida'
                }), 400
        
        # Crear producto en la base de datos usando el modelo actualizado
        resultado = ProductoModel.crear_producto(datos)
        
        if resultado['success']:
            logger.info(f"Producto creado exitosamente: ID {resultado['producto_id']}")
            return jsonify({
                'success': True,
                'message': 'Producto creado exitosamente',
                'producto_id': resultado['producto_id']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': f'Error al crear producto: {resultado.get("error", "Error desconocido")}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error al crear producto: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al crear producto: {str(e)}'
        }), 500

@productos_bp.route('/<int:producto_id>', methods=['PUT'])
def actualizar_producto(producto_id):
    """Actualizar un producto existente"""
    try:
        datos = request.get_json()
        logger.info(f"Actualizando producto ID: {producto_id}")
        
        # Verificar si el producto existe usando el modelo actualizado
        producto_existente = ProductoModel.obtener_producto_por_id(producto_id)
        if not producto_existente:
            return jsonify({
                'success': False,
                'message': 'Producto no encontrado'
            }), 404
        
        # Validar precios si se proporcionan
        if 'precio_venta' in datos:
            try:
                precio_venta = float(datos['precio_venta'])
                if precio_venta < 0:
                    return jsonify({
                        'success': False,
                        'message': 'El precio de venta no puede ser negativo'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Precio de venta inválido'
                }), 400
        
        if 'precio_costo' in datos:
            try:
                precio_costo = float(datos['precio_costo'])
                if precio_costo < 0:
                    return jsonify({
                        'success': False,
                        'message': 'El precio de costo no puede ser negativo'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Precio de costo inválido'
                }), 400
        
        # Validar cantidad
        if 'cantidad' in datos:
            try:
                cantidad = int(datos['cantidad'])
                if cantidad < 0:
                    return jsonify({
                        'success': False,
                        'message': 'La cantidad no puede ser negativa'
                    }), 400
            except:
                return jsonify({
                    'success': False,
                    'message': 'Cantidad inválida'
                }), 400
        
        # Actualizar producto en la base de datos usando el modelo actualizado
        resultado = ProductoModel.actualizar_producto(producto_id, datos)
        
        if resultado['success']:
            logger.info(f"Producto actualizado exitosamente: ID {producto_id}")
            return jsonify({
                'success': True,
                'message': 'Producto actualizado exitosamente'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Error al actualizar producto: {resultado.get("error", "Error desconocido")}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error al actualizar producto: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar producto: {str(e)}'
        }), 500

@productos_bp.route('/<int:producto_id>', methods=['DELETE'])
def eliminar_producto(producto_id):
    """Eliminar un producto"""
    try:
        logger.info(f"Eliminando producto ID: {producto_id}")
        
        # Verificar si el producto existe usando el modelo actualizado
        producto_existente = ProductoModel.obtener_producto_por_id(producto_id)
        if not producto_existente:
            return jsonify({
                'success': False,
                'message': 'Producto no encontrado'
            }), 404
        
        # Eliminar producto de la base de datos usando el modelo actualizado
        resultado = ProductoModel.eliminar_producto(producto_id)
        
        if resultado['success']:
            if resultado['rows_affected'] > 0:
                logger.info(f"Producto eliminado exitosamente: ID {producto_id}")
                return jsonify({
                    'success': True,
                    'message': 'Producto eliminado exitosamente'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No se pudo eliminar el producto'
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': f'Error al eliminar producto: {resultado.get("error", "Error desconocido")}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error al eliminar producto: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al eliminar producto: {str(e)}'
        }), 500

@productos_bp.route('/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas de productos"""
    try:
        logger.info("Obteniendo estadísticas de productos")
        
        stats = ProductoModel.obtener_estadisticas()
        
        if stats:
            return jsonify({
                'success': True,
                'estadisticas': stats
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Error al obtener estadísticas'
            }), 500
        
    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener estadísticas: {str(e)}'
        }), 500

@productos_bp.route('/categorias', methods=['GET'])
def obtener_categorias():
    """Obtener lista de categorías"""
    try:
        logger.info("Obteniendo categorías de productos")
        
        categorias = ProductoModel.obtener_categorias()
        
        return jsonify({
            'success': True,
            'categorias': categorias
        })
        
    except Exception as e:
        logger.error(f"Error al obtener categorías: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener categorías: {str(e)}'
        }), 500

@productos_bp.route('/buscar', methods=['GET'])
def buscar_productos_venta():
    """Buscar productos para ventas - Ruta duplicada para compatibilidad"""
    try:
        busqueda = request.args.get('q', '')
        logger.debug(f"Buscando productos para ventas (ruta productos/buscar): '{busqueda}'")
        
        productos = ProductoModel.buscar_productos(busqueda)
        
        return jsonify({
            'success': True,
            'productos': productos
        })
        
    except Exception as e:
        logger.error(f"Error al buscar productos: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al buscar productos: {str(e)}'
        }), 500

@productos_bp.route('/test', methods=['GET'])
def test_productos():
    """Ruta de prueba para productos"""
    return jsonify({
        'success': True,
        'message': 'API de productos funcionando',
        'endpoints': [
            {'method': 'GET', 'path': '/api/productos/', 'desc': 'Obtener todos los productos'},
            {'method': 'GET', 'path': '/api/productos/<id>', 'desc': 'Obtener producto por ID'},
            {'method': 'POST', 'path': '/api/productos/', 'desc': 'Crear nuevo producto'},
            {'method': 'PUT', 'path': '/api/productos/<id>', 'desc': 'Actualizar producto'},
            {'method': 'DELETE', 'path': '/api/productos/<id>', 'desc': 'Eliminar producto'},
            {'method': 'GET', 'path': '/api/productos/estadisticas', 'desc': 'Obtener estadísticas'},
            {'method': 'GET', 'path': '/api/productos/categorias', 'desc': 'Obtener categorías'},
            {'method': 'GET', 'path': '/api/productos/proveedores', 'desc': 'Obtener proveedores'},
            {'method': 'GET', 'path': '/api/productos/buscar?q=texto', 'desc': 'Buscar productos para ventas'}
        ]
    })