# controlador/reporte_caja_controller.py
from flask import Blueprint, jsonify, request, session
from modelo.reporte_caja_model import model
import logging

logger = logging.getLogger(__name__)

reporte_caja_bp = Blueprint('reporte_caja', __name__)

@reporte_caja_bp.route('/api/reporte-caja/movimientos', methods=['GET'])
def obtener_movimientos():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        tipo = request.args.get('tipo')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        filtros = {
            'page': page,
            'per_page': per_page,
            'tipo': tipo,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
        
        resultado = model.obtener_movimientos(filtros)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'data': {
                    'movimientos': resultado['movimientos'],
                    'paginacion': resultado['paginacion']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error al obtener movimientos')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en obtener_movimientos: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener movimientos: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/resumen', methods=['GET'])
def obtener_resumen():
    try:
        periodo = request.args.get('periodo', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        resultado = model.obtener_resumen_financiero(periodo, fecha_inicio, fecha_fin)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'data': resultado['resumen']
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error al obtener resumen')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en obtener_resumen: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener resumen: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        periodo = request.args.get('periodo', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        resultado_estadisticas = model.obtener_estadisticas_graficos(periodo, fecha_inicio, fecha_fin)
        
        if not resultado_estadisticas['success']:
            return jsonify({
                'success': False,
                'message': resultado_estadisticas.get('message', 'Error al obtener estadísticas')
            }), 500
        
        resultado_resumen = model.obtener_resumen_financiero(periodo, fecha_inicio, fecha_fin)
        
        if resultado_resumen['success']:
            return jsonify({
                'success': True,
                'data': {
                    'graficos': {
                        'flujo_caja': resultado_estadisticas['flujo_caja'],
                        'distribucion_egresos': resultado_estadisticas['distribucion_egresos']
                    },
                    'resumen': resultado_resumen['resumen']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado_resumen.get('message', 'Error al obtener resumen')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener estadísticas: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/movimiento', methods=['POST'])
def crear_movimiento():
    try:
        data = request.json
        
        required_fields = ['tipo', 'monto', 'razon']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        try:
            monto = float(data['monto'])
            if monto <= 0:
                return jsonify({
                    'success': False,
                    'message': 'El monto debe ser mayor a 0'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Monto inválido'
            }), 400
        
        resultado = model.crear_movimiento(data)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': resultado['message'],
                'data': {
                    'id': resultado['movimiento_id']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error al crear movimiento')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en crear_movimiento: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al crear movimiento: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['GET'])
def obtener_movimiento(movimiento_id):
    try:
        resultado = model.obtener_movimiento_por_id(movimiento_id)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'data': resultado['movimiento']
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Movimiento no encontrado')
            }), 404
            
    except Exception as e:
        logger.error(f"Error en obtener_movimiento: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener movimiento: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['PUT'])
def actualizar_movimiento(movimiento_id):
    try:
        data = request.json
        
        required_fields = ['tipo', 'monto', 'razon']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'Campo requerido faltante: {field}'
                }), 400
        
        try:
            monto = float(data['monto'])
            if monto <= 0:
                return jsonify({
                    'success': False,
                    'message': 'El monto debe ser mayor a 0'
                }), 400
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Monto inválido'
            }), 400
        
        resultado = model.actualizar_movimiento(movimiento_id, data)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': resultado['message']
            })
        else:
            if resultado.get('message') == 'Movimiento no encontrado':
                return jsonify({
                    'success': False,
                    'message': resultado['message']
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('message', 'Error al actualizar movimiento')
                }), 500
            
    except Exception as e:
        logger.error(f"Error en actualizar_movimiento: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al actualizar movimiento: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/movimiento/<int:movimiento_id>', methods=['DELETE'])
def eliminar_movimiento(movimiento_id):
    try:
        resultado = model.eliminar_movimiento(movimiento_id)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'message': resultado['message']
            })
        else:
            if resultado.get('message') == 'Movimiento no encontrado':
                return jsonify({
                    'success': False,
                    'message': resultado['message']
                }), 404
            else:
                return jsonify({
                    'success': False,
                    'message': resultado.get('message', 'Error al eliminar movimiento')
                }), 500
            
    except Exception as e:
        logger.error(f"Error en eliminar_movimiento: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al eliminar movimiento: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/abonos-detalle', methods=['GET'])
def obtener_abonos_detalle():
    try:
        periodo = request.args.get('periodo', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        resultado = model.obtener_abonos_detalle(periodo, fecha_inicio, fecha_fin)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'data': {
                    'detalle': resultado['detalle'],
                    'resumen': resultado['resumen']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error al obtener detalle de abonos')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en obtener_abonos_detalle: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener detalle de abonos: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/dinero-banco', methods=['GET'])
def obtener_dinero_banco():
    try:
        periodo = request.args.get('periodo', 'hoy')
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        
        resultado = model.obtener_dinero_banco(periodo, fecha_inicio, fecha_fin)
        
        if resultado['success']:
            return jsonify({
                'success': True,
                'data': resultado
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error al obtener dinero por banco')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en obtener_dinero_banco: {e}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener dinero por banco: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/cierre-actual', methods=['GET'])
def obtener_cierre_actual():
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'Solo el administrador puede consultar el baúl.'}), 403

    resultado = model.obtener_cierre_actual()
    if not resultado['success']:
        return jsonify({'success': False, 'message': resultado.get('message', 'Error al obtener el cierre')}), 500
    return jsonify({'success': True, 'data': resultado['cierre']})

@reporte_caja_bp.route('/api/reporte-caja/cierres', methods=['GET'])
def listar_cierres():
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'Solo el administrador puede consultar los cierres.'}), 403
    anio = request.args.get('anio', type=int)
    mes = request.args.get('mes', type=int)
    if not anio or not mes:
        return jsonify({'success': False, 'message': 'Debe indicar año y mes.'}), 400
    resultado = model.listar_cierres_mes(anio, mes)
    status = 400 if resultado.get('error_code') == 'validation' else 500
    if not resultado['success']:
        return jsonify({'success': False, 'message': resultado.get('message', 'Error al listar cierres')}), status
    return jsonify({'success': True, 'data': resultado})

@reporte_caja_bp.route('/api/reporte-caja/cierres/<fecha_cierre>', methods=['GET', 'PUT'])
def gestionar_cierre_fecha(fecha_cierre):
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'Solo el administrador puede editar cierres.'}), 403
    if request.method == 'GET':
        resultado = model.obtener_cierre_fecha(fecha_cierre)
    else:
        datos = request.get_json(silent=True) or {}
        resultado = model.editar_cierre(fecha_cierre, datos)
    if not resultado['success']:
        status = 404 if resultado.get('error_code') == 'not_found' else 400 if resultado.get('error_code') == 'validation' else 500
        return jsonify({'success': False, 'message': resultado.get('message', 'Error con el cierre')}), status
    return jsonify({'success': True, 'data': resultado.get('cierre'), 'message': resultado.get('message')})

@reporte_caja_bp.route('/api/reporte-caja/cierre', methods=['POST'])
def aplicar_cierre():
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'Solo el administrador puede aplicar el cierre.'}), 403

    datos = request.get_json(silent=True) or {}
    resultado = model.aplicar_cierre(datos)
    if not resultado['success']:
        status = 400 if resultado.get('error_code') == 'validation' else 500
        return jsonify({'success': False, 'message': resultado.get('message', 'Error al aplicar el cierre')}), status
    return jsonify({
        'success': True,
        'message': resultado.get('message', 'Cierre de caja guardado.'),
        'data': resultado['cierre'],
    })

@reporte_caja_bp.route('/api/reporte-caja/cierres/<fecha_cierre>/ajustes', methods=['POST'])
@reporte_caja_bp.route('/api/reporte-caja/cierres/<fecha_cierre>/ajustes/<int:ajuste_id>', methods=['PUT', 'DELETE'])
def gestionar_ajuste_banco(fecha_cierre, ajuste_id=None):
    if session.get('rol') != 'admin':
        return jsonify({'success': False, 'message': 'Solo el administrador puede gestionar ajustes bancarios.'}), 403

    if request.method == 'DELETE':
        resultado = model.eliminar_ajuste_banco(fecha_cierre, ajuste_id)
    else:
        datos = request.get_json(silent=True) or {}
        resultado = model.crear_actualizar_ajuste_banco(fecha_cierre, datos, ajuste_id)

    if not resultado['success']:
        status = 404 if resultado.get('error_code') == 'not_found' else 400 if resultado.get('error_code') == 'validation' else 500
        return jsonify({'success': False, 'message': resultado.get('message', 'Error en el ajuste bancario')}), status
    message = 'Ajuste eliminado.' if request.method == 'DELETE' else resultado.get('message')
    return jsonify({'success': True, 'message': message, 'data': resultado.get('cierre')})

@reporte_caja_bp.route('/api/reporte-caja/diagnostico', methods=['GET'])
def ejecutar_diagnostico():
    try:
        resultado = model.ejecutar_diagnostico()
        
        if resultado['success']:
            from datetime import datetime
            return jsonify({
                'success': True,
                'data': {
                    'diagnosticos': resultado['diagnosticos'],
                    'timestamp': datetime.now().isoformat(),
                    'total_checks': resultado['total_checks'],
                    'checks_ok': resultado['checks_ok'],
                    'checks_error': resultado['checks_error'],
                    'checks_warning': resultado['checks_warning']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error ejecutando diagnóstico')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en ejecutar_diagnostico: {e}")
        return jsonify({
            'success': False,
            'message': f'Error ejecutando diagnóstico: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/inicializar-ejemplo', methods=['POST'])
def inicializar_datos_ejemplo():
    try:
        resultado = model.inicializar_datos_ejemplo()
        
        if resultado['success']:
            from datetime import datetime
            return jsonify({
                'success': True,
                'message': resultado['message'],
                'data': {
                    'ingresos_creados': resultado['ingresos_creados'],
                    'egresos_creados': resultado['egresos_creados'],
                    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': resultado.get('message', 'Error inicializando datos')
            }), 500
            
    except Exception as e:
        logger.error(f"Error en inicializar_datos_ejemplo: {e}")
        return jsonify({
            'success': False,
            'message': f'Error inicializando datos: {str(e)}'
        }), 500

@reporte_caja_bp.route('/api/reporte-caja/test', methods=['GET'])
def test():
    return jsonify({
        'success': True,
        'message': 'Controlador de reporte de caja funcionando correctamente',
        'model': 'ReporteCajaModel',
        'endpoints': [
            'GET  /api/reporte-caja/movimientos',
            'GET  /api/reporte-caja/resumen',
            'GET  /api/reporte-caja/estadisticas',
            'POST /api/reporte-caja/movimiento',
            'GET  /api/reporte-caja/movimiento/<id>',
            'PUT  /api/reporte-caja/movimiento/<id>',
            'DELETE /api/reporte-caja/movimiento/<id>',
            'GET  /api/reporte-caja/abonos-detalle',
            'GET  /api/reporte-caja/dinero-banco',
            'GET  /api/reporte-caja/diagnostico',
            'POST /api/reporte-caja/inicializar-ejemplo'
        ]
    })