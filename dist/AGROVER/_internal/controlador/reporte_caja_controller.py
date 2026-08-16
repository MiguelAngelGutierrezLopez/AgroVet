from flask import Blueprint, request, jsonify
from modelo.reporte_caja_model import ReporteCajaModel
import logging
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

# Crear Blueprint
reporte_caja_bp = Blueprint('reporte_caja', __name__)
model = ReporteCajaModel()

# ✅ RUTAS PARA MOVIMIENTOS
@reporte_caja_bp.route('/reporte-caja/movimientos', methods=['GET'])
@reporte_caja_bp.route('/api/reporte-caja/movimientos', methods=['GET'])
def obtener_movimientos():
    """Obtiene movimientos con filtros"""
    try:
        logger.info(f"Obteniendo movimientos - Params: {dict(request.args)}")
        
        # Parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo = request.args.get('tipo')  # 'ingreso' o 'egreso'
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        logger.info(f"Filtros: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, tipo={tipo}, page={page}, per_page={per_page}")
        
        result = model.obtener_movimientos(fecha_inicio, fecha_fin, tipo, page, per_page)
        
        logger.info(f"Resultado obtener_movimientos: success={result.get('success')}, total={result.get('total', 0)}")
        
        if result['success']:
            return jsonify({
                'success': True,
                'data': result.get('data', []),
                'total': result.get('total', 0),
                'page': result.get('page', page),
                'per_page': result.get('per_page', per_page),
                'pages': result.get('pages', 0),
                'filters_applied': {
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'tipo': tipo
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error en obtener_movimientos: {error_msg}")
            return jsonify({
                'success': False, 
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en obtener_movimientos: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500

@reporte_caja_bp.route('/reporte-caja/movimiento', methods=['POST'])
@reporte_caja_bp.route('/api/reporte-caja/movimiento', methods=['POST'])
def crear_movimiento():
    """Crea un nuevo movimiento"""
    try:
        logger.info(f"Creando movimiento - Headers: {dict(request.headers)}")
        
        if not request.is_json:
            logger.error("Solicitud no es JSON")
            return jsonify({
                'success': False, 
                'error': 'Content-Type debe ser application/json',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        data = request.get_json()
        logger.info(f"Datos recibidos para crear movimiento: {data}")
        
        if not data:
            logger.error("Datos JSON vacíos")
            return jsonify({'success': False, 'error': 'Datos JSON requeridos'}), 400
        
        # Validaciones
        required_fields = ['monto', 'razon', 'tipo']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            logger.error(f"Campos requeridos faltantes: {missing_fields}")
            return jsonify({
                'success': False, 
                'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400
        
        try:
            monto = float(data['monto'])
            if monto <= 0:
                logger.error(f"Monto inválido: {monto}")
                return jsonify({'success': False, 'error': 'El monto debe ser mayor a 0'}), 400
        except (ValueError, TypeError) as e:
            logger.error(f"Error en monto: {e}")
            return jsonify({'success': False, 'error': 'El monto debe ser un número válido'}), 400
        
        if data['tipo'] not in ['ingreso', 'egreso']:
            logger.error(f"Tipo inválido: {data['tipo']}")
            return jsonify({'success': False, 'error': 'El tipo debe ser "ingreso" o "egreso"'}), 400
        
        if not data['razon'] or data['razon'].strip() == '':
            logger.error("Razón vacía")
            return jsonify({'success': False, 'error': 'La razón no puede estar vacía'}), 400
        
        # Convertir fecha si viene del formulario
        if 'fecha' in data and data['fecha']:
            try:
                # Convertir de formato datetime-local a formato MySQL
                fecha_str = data['fecha']
                if 'T' in fecha_str:
                    fecha_obj = datetime.fromisoformat(fecha_str.replace('T', ' '))
                else:
                    fecha_obj = datetime.fromisoformat(fecha_str)
                data['fecha'] = fecha_obj.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Fecha convertida: {data['fecha']}")
            except Exception as e:
                logger.error(f"Error convirtiendo fecha {fecha_str}: {e}")
                # Si no se puede convertir, usar fecha actual
                data['fecha'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Usando fecha actual: {data['fecha']}")
        
        logger.info(f"Datos procesados para guardar: {data}")
        
        result = model.crear_movimiento(data)
        
        if result['success']:
            logger.info(f"Movimiento creado exitosamente: ID {result.get('id')}")
            return jsonify({
                'success': True, 
                'id': result['id'], 
                'data': result.get('data'),
                'message': 'Movimiento creado exitosamente',
                'timestamp': datetime.now().isoformat()
            }), 201
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error del modelo al crear movimiento: {error_msg}")
            return jsonify({
                'success': False, 
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en crear_movimiento: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500

@reporte_caja_bp.route('/reporte-caja/movimiento/<int:movimiento_id>', methods=['GET'])
@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['GET'])
def obtener_movimiento(movimiento_id):
    """Obtiene un movimiento por ID"""
    try:
        logger.info(f"Obteniendo movimiento ID: {movimiento_id}")
        
        result = model.obtener_movimiento_por_id(movimiento_id)
        
        if result['success']:
            if result['data']:
                logger.info(f"Movimiento {movimiento_id} encontrado")
                return jsonify({
                    'success': True,
                    'data': result['data'],
                    'timestamp': datetime.now().isoformat()
                }), 200
            else:
                logger.warning(f"Movimiento {movimiento_id} no encontrado")
                return jsonify({
                    'success': False,
                    'error': 'Movimiento no encontrado',
                    'timestamp': datetime.now().isoformat()
                }), 404
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error del modelo: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en obtener_movimiento: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@reporte_caja_bp.route('/reporte-caja/movimiento/<int:movimiento_id>', methods=['PUT'])
@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['PUT'])
def actualizar_movimiento(movimiento_id):
    """Actualiza un movimiento existente"""
    try:
        logger.info(f"Actualizando movimiento ID: {movimiento_id}")
        
        if not request.is_json:
            logger.error("Solicitud no es JSON")
            return jsonify({
                'success': False,
                'error': 'Content-Type debe ser application/json',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        data = request.get_json()
        logger.info(f"Datos recibidos para actualizar movimiento {movimiento_id}: {data}")
        
        if not data:
            logger.error("Datos JSON vacíos")
            return jsonify({
                'success': False,
                'error': 'Datos JSON requeridos',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Validaciones básicas
        if 'monto' in data:
            try:
                monto = float(data['monto'])
                if monto <= 0:
                    logger.error(f"Monto inválido: {monto}")
                    return jsonify({
                        'success': False,
                        'error': 'El monto debe ser mayor a 0',
                        'timestamp': datetime.now().isoformat()
                    }), 400
            except (ValueError, TypeError) as e:
                logger.error(f"Error en monto: {e}")
                return jsonify({
                    'success': False,
                    'error': 'El monto debe ser un número válido',
                    'timestamp': datetime.now().isoformat()
                }), 400
        
        if 'razon' in data and (not data['razon'] or data['razon'].strip() == ''):
            logger.error("Razón vacía")
            return jsonify({
                'success': False,
                'error': 'La razón no puede estar vacía',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        if 'tipo' in data and data['tipo'] not in ['ingreso', 'egreso']:
            logger.error(f"Tipo inválido: {data['tipo']}")
            return jsonify({
                'success': False,
                'error': 'El tipo debe ser "ingreso" o "egreso"',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        # Procesar fecha si viene del formulario
        if 'fecha' in data and data['fecha']:
            try:
                fecha_str = data['fecha']
                if 'T' in fecha_str:
                    fecha_obj = datetime.fromisoformat(fecha_str.replace('T', ' '))
                else:
                    fecha_obj = datetime.fromisoformat(fecha_str)
                data['fecha'] = fecha_obj.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Fecha convertida: {data['fecha']}")
            except Exception as e:
                logger.warning(f"Error convirtiendo fecha {fecha_str}: {e}")
                data['fecha'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"Usando fecha actual: {data['fecha']}")
        
        result = model.actualizar_movimiento(movimiento_id, data)
        
        if result['success']:
            affected_rows = result.get('affected_rows', 0)
            logger.info(f"Movimiento {movimiento_id} actualizado exitosamente. Filas afectadas: {affected_rows}")
            return jsonify({
                'success': True,
                'affected_rows': affected_rows,
                'message': 'Movimiento actualizado exitosamente',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error del modelo: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en actualizar_movimiento: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

@reporte_caja_bp.route('/reporte-caja/movimiento/<int:movimiento_id>', methods=['DELETE'])
@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['DELETE'])
def eliminar_movimiento(movimiento_id):
    """Elimina un movimiento"""
    try:
        logger.info(f"Eliminando movimiento ID: {movimiento_id}")
        
        result = model.eliminar_movimiento(movimiento_id)
        
        if result['success']:
            affected_rows = result.get('affected_rows', 0)
            logger.info(f"Movimiento {movimiento_id} eliminado exitosamente. Filas afectadas: {affected_rows}")
            return jsonify({
                'success': True,
                'affected_rows': affected_rows,
                'message': 'Movimiento eliminado exitosamente',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error del modelo: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en eliminar_movimiento: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# ✅ RUTAS PARA RESUMEN Y ESTADÍSTICAS
@reporte_caja_bp.route('/reporte-caja/resumen', methods=['GET'])
@reporte_caja_bp.route('/api/reporte-caja/resumen', methods=['GET'])
def obtener_resumen():
    """Obtiene resumen financiero"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')  # 'hoy', 'semana', 'mes', 'anio'
        
        logger.info(f"Obteniendo resumen: periodo={periodo}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        
        if periodo:
            result = model.obtener_estadisticas_periodo(periodo)
        else:
            result = model.obtener_resumen(fecha_inicio, fecha_fin)
        
        if result['success']:
            resumen = result.get('resumen', {})
            distribucion = result.get('distribucion', [])
            flujo = result.get('flujo', [])
            
            logger.info(f"Resumen obtenido: ingresos={resumen.get('total_ingresos', 0)}, egresos={resumen.get('total_egresos', 0)}")
            
            return jsonify({
                'success': True,
                'resumen': {
                    'total_ingresos': float(resumen.get('total_ingresos', 0)),
                    'total_egresos': float(resumen.get('total_egresos', 0)),
                    'saldo_neto': float(resumen.get('saldo_neto', 0)),
                    'cantidad_ingresos': int(resumen.get('cantidad_ingresos', 0)),
                    'cantidad_egresos': int(resumen.get('cantidad_egresos', 0))
                },
                'distribucion': distribucion,
                'flujo': flujo,
                'filters_applied': {
                    'periodo': periodo,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                },
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error en obtener_resumen: {error_msg}")
            return jsonify({
                'success': False, 
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en obtener_resumen: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500

@reporte_caja_bp.route('/reporte-caja/estadisticas', methods=['GET'])
@reporte_caja_bp.route('/api/reporte-caja/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtiene estadísticas avanzadas para gráficos"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')
        
        logger.info(f"Obteniendo estadísticas: periodo={periodo}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        
        if periodo:
            result = model.obtener_estadisticas_periodo(periodo)
        else:
            result = model.obtener_resumen(fecha_inicio, fecha_fin)
        
        if not result['success']:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error del modelo en obtener_estadisticas: {error_msg}")
            return jsonify({
                'success': False, 
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        # Procesar datos para gráficos
        resumen = result.get('resumen', {})
        distribucion = result.get('distribucion', [])
        flujo = result.get('flujo', [])
        
        logger.info(f"Datos procesados: resumen={bool(resumen)}, distribucion={len(distribucion)}, flujo={len(flujo)}")
        
        return jsonify({
            'success': True,
            'resumen': {
                'total_ingresos': float(resumen.get('total_ingresos', 0)),
                'total_egresos': float(resumen.get('total_egresos', 0)),
                'saldo_neto': float(resumen.get('saldo_neto', 0)),
                'cantidad_ingresos': resumen.get('cantidad_ingresos', 0),
                'cantidad_egresos': resumen.get('cantidad_egresos', 0)
            },
            'distribucion_egresos': distribucion,
            'flujo_caja': flujo,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Excepción en obtener_estadisticas: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False, 
            'error': f'Error interno: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500

# ✅ RUTA DE PRUEBA Y DIAGNÓSTICO
@reporte_caja_bp.route('/reporte-caja/test', methods=['GET'])
@reporte_caja_bp.route('/api/reporte-caja/test', methods=['GET'])
def test_reporte_caja():
    """Ruta de prueba para verificar que el blueprint funciona"""
    try:
        logger.info("Test de reporte caja ejecutado")
        
        # Obtener conteo de movimientos
        movimientos = model.obtener_movimientos()
        total_movimientos = movimientos.get('total', 0) if movimientos.get('success') else 0
        
        return jsonify({
            'success': True,
            'message': 'API de Reporte de Caja funcionando correctamente',
            'blueprint': 'reporte_caja',
            'endpoints': {
                'GET /api/reporte-caja/movimientos': 'Listar movimientos',
                'POST /api/reporte-caja/movimiento': 'Crear movimiento',
                'GET /api/reporte-caja/movimiento/<id>': 'Obtener movimiento',
                'PUT /api/reporte-caja/movimiento/<id>': 'Actualizar movimiento',
                'DELETE /api/reporte-caja/movimiento/<id>': 'Eliminar movimiento',
                'GET /api/reporte-caja/resumen': 'Obtener resumen',
                'GET /api/reporte-caja/estadisticas': 'Obtener estadísticas'
            },
            'stats': {
                'total_movimientos': total_movimientos
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error en test_reporte_caja: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }), 500

# ✅ RUTA PARA INICIALIZAR DATOS DE EJEMPLO
@reporte_caja_bp.route('/reporte-caja/inicializar-ejemplo', methods=['POST'])
@reporte_caja_bp.route('/api/reporte-caja/inicializar-ejemplo', methods=['POST'])
def inicializar_datos_ejemplo():
    """Inicializa datos de ejemplo para pruebas"""
    try:
        logger.info("Inicializando datos de ejemplo para reporte caja")
        
        result = model.inicializar_datos_ejemplo()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': result.get('mensaje', 'Datos inicializados exitosamente'),
                'total_movimientos': result.get('total_movimientos', 0),
                'periodo': result.get('periodo', 'Últimos 30 días'),
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            error_msg = result.get('error', 'Error desconocido')
            logger.error(f"Error inicializando datos: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Excepción en inicializar_datos_ejemplo: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'Error interno: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500