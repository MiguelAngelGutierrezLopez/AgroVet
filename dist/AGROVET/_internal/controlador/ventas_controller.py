from flask import Blueprint, request, jsonify, render_template, send_file
from modelo.venta_model import VentaModel
from modelo.producto_model import ProductoModel
from modelo.cliente_model import ClienteModel
from config import Config
import pdfkit
from jinja2 import Template
from io import BytesIO
import os
import logging

# Configurar logger
logger = logging.getLogger(__name__)

ventas_bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')

@ventas_bp.route('/nueva', methods=['POST'])
def crear_venta():
    """Crear una nueva venta (normal o mixta)"""
    try:
        datos = request.get_json()
        logger.info(f"Recibiendo nueva venta: {len(datos.get('productos', []))} productos")
        
        # Validar datos mínimos
        if not datos or 'productos' not in datos or len(datos['productos']) == 0:
            return jsonify({
                'success': False,
                'message': 'Debe agregar al menos un producto'
            }), 400
        
        # Determinar tipo de venta
        es_mixta = datos.get('es_mixta', False)
        
        if es_mixta:
            # Validar venta mixta
            metodos_mixtos = datos.get('metodos_mixtos', [])
            
            if len(metodos_mixtos) != 2:
                return jsonify({
                    'success': False,
                    'message': 'Venta mixta requiere exactamente 2 métodos de pago'
                }), 400
            
            # Validar que haya un contado y un banco
            metodos = [m['metodo'] for m in metodos_mixtos]
            if not ('contado' in metodos and 'banco' in metodos):
                return jsonify({
                    'success': False,
                    'message': 'Venta mixta debe incluir contado y banco'
                }), 400
            
            # Validar que la suma sea igual al total
            suma_montos = sum(m['monto'] for m in metodos_mixtos)
            total = datos.get('total', 0)
            
            if abs(suma_montos - total) > 0.01:  # Tolerancia de 1 centavo
                return jsonify({
                    'success': False,
                    'message': f'La suma de montos (${suma_montos:,.2f}) no coincide con el total (${total:,.2f})'
                }), 400
            
            # Validar dinero entregado vs monto contado
            for metodo in metodos_mixtos:
                if metodo['metodo'] == 'contado':
                    dinero_entregado = metodo.get('dinero_entregado', 0)
                    monto_contado = metodo['monto']
                    
                    if dinero_entregado < monto_contado:
                        return jsonify({
                            'success': False,
                            'message': 'El dinero entregado debe ser mayor o igual al monto en contado'
                        }), 400
                    
                    # Calcular cambio
                    metodo['cambio'] = dinero_entregado - monto_contado
                elif metodo['metodo'] == 'banco':
                    # Validar submetodo para banco
                    if not metodo.get('submetodo'):
                        return jsonify({
                            'success': False,
                            'message': 'Debe seleccionar un medio bancario (Nequi, Transacción o Tarjeta)'
                        }), 400
        
        else:
            # Validar venta normal
            metodo_pago = datos.get('metodo_pago', 'contado')
            if metodo_pago not in ['contado', 'credito', 'banco']:
                return jsonify({
                    'success': False,
                    'message': 'Método de pago no válido'
                }), 400
            
            cliente_cedula = datos.get('cliente_cedula', 'final')
            
            # Validaciones para crédito
            if metodo_pago == 'credito':
                if cliente_cedula == 'final':
                    return jsonify({
                        'success': False,
                        'message': 'Para venta a crédito debe seleccionar un cliente específico'
                    }), 400
                
                # Validar días de crédito
                dias_credito = datos.get('dias_credito', 30)
                if dias_credito <= 0:
                    return jsonify({
                        'success': False,
                        'message': 'Debe especificar los días de crédito válidos'
                    }), 400
                
                # Validar anticipo
                anticipo = datos.get('anticipo', 0)
                total = datos.get('total', 0)
                
                if anticipo > total:
                    return jsonify({
                        'success': False,
                        'message': 'El anticipo no puede ser mayor al total de la venta'
                    }), 400
        
        # Estructurar datos para el modelo
        datos_venta = {
            'productos': datos['productos'],
            'subtotal': datos['subtotal'],
            'descuento': datos.get('descuento', 0),
            'total': datos.get('total', 0),
            'metodo_pago': datos.get('metodo_pago', 'contado'),
            'cliente_cedula': datos.get('cliente_cedula', 'final'),
            'dias_credito': datos.get('dias_credito'),
            'submetodo_banco': datos.get('submetodo_banco'),
            'anticipo': datos.get('anticipo', 0),
            'dinero_entregado': datos.get('dinero_entregado', 0),
            'es_mixta': es_mixta
        }
        
        # Agregar métodos mixtos si aplica
        if es_mixta:
            datos_venta['metodos_mixtos'] = datos['metodos_mixtos']
        
        # Crear venta en base de datos
        resultado = VentaModel.crear_venta(datos_venta)
        
        if resultado['success']:
            logger.info(f"Venta creada exitosamente: ID {resultado['venta_id']}, Ticket #{resultado['ticket_numero']}")
            
            return jsonify({
                'success': True,
                'message': 'Venta registrada exitosamente',
                'venta_id': resultado['venta_id'],
                'ticket_numero': resultado['ticket_numero']
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Error al crear la venta en la base de datos'
            }), 500
        
    except Exception as e:
        logger.error(f"Error al crear la venta: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al crear la venta: {str(e)}'
        }), 500
@ventas_bp.route('/ultimo-ticket', methods=['GET'])
def obtener_ultimo_ticket():
    """Obtener el último número de ticket"""
    try:
        ultimo_ticket = VentaModel.obtener_ultimo_ticket()
        logger.debug(f"Último ticket obtenido: {ultimo_ticket}")
        return jsonify({
            'success': True,
            'ticket_numero': ultimo_ticket
        })
    except Exception as e:
        logger.error(f"Error al obtener ticket: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener ticket: {str(e)}'
        }), 500

@ventas_bp.route('/<int:venta_id>/factura', methods=['GET'])
def generar_factura(venta_id):
    """Redirigir a la función de PDF"""
    try:
        # Obtener parámetros de la venta
        cajero = request.args.get('cajero', 'SISTEMA')
        dias_credito = request.args.get('dias_credito', '30')
        anticipo = request.args.get('anticipo', '0')
        pago_recibido = request.args.get('pago_recibido', '0')
        
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Redirigiendo...</title>
            <script>
                window.location.href = '/api/ventas/{venta_id}/factura-pdf?cajero={cajero}&dias_credito={dias_credito}&anticipo={anticipo}&pago_recibido={pago_recibido}';
            </script>
        </head>
        <body>
            <h3>Generando factura en formato PDF...</h3>
            <p>Si no es redirigido automáticamente, <a href="/api/ventas/{venta_id}/factura-pdf?cajero={cajero}&dias_credito={dias_credito}&anticipo={anticipo}&pago_recibido={pago_recibido}">haga clic aquí</a></p>
        </body>
        </html>
        ''', 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        logger.error(f"Error en redirección: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@ventas_bp.route('/productos/buscar', methods=['GET'])
def buscar_productos():
    """Buscar productos disponibles"""
    try:
        busqueda = request.args.get('q', '')
        logger.debug(f"Buscando productos para ventas: '{busqueda}'")
        
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

@ventas_bp.route('/clientes/buscar', methods=['GET'])
def buscar_clientes():
    """Buscar clientes"""
    try:
        busqueda = request.args.get('q', '')
        logger.debug(f"Buscando clientes: '{busqueda}'")
        
        clientes = ClienteModel.buscar_clientes(busqueda)
        
        return jsonify({
            'success': True,
            'clientes': clientes
        })
        
    except Exception as e:
        logger.error(f"Error al buscar clientes: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al buscar clientes: {str(e)}'
        }), 500

@ventas_bp.route('/test', methods=['GET'])
def test_ventas():
    """Ruta de prueba para ventas"""
    return jsonify({
        'success': True,
        'message': 'API de ventas funcionando',
        'status': 'active'
    })