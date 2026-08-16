"""
Controlador para generación de PDFs de facturas - VERSIÓN COMPLETA
con soporte para facturas de venta, créditos y comprobantes de abono
"""
from flask import Blueprint, request, jsonify, make_response
from modelo.venta_model import VentaModel
from modelo.cliente_proveedor_modelo import ClienteProveedorModel
from config import Config
import os
import logging
from datetime import datetime
import locale
from io import BytesIO

# Configurar logger
logger = logging.getLogger(__name__)

# Intentar importar xhtml2pdf para PDF
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
    logger.info("xhtml2pdf está disponible para generar PDFs")
except ImportError:
    XHTML2PDF_AVAILABLE = False
    logger.warning("xhtml2pdf no está instalado. Para generar PDFs, instale: pip install xhtml2pdf")

# Configurar locale para formato de moneda
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'es_ES')
    except:
        pass

# Crear blueprint para PDF
ventas_pdf_bp = Blueprint('ventas_pdf', __name__, url_prefix='/api/ventas')

# ===== FUNCIONES AUXILIARES =====

def formato_moneda(valor):
    """Formatear valor a moneda colombiana"""
    try:
        valor_float = float(valor)
        return f"${valor_float:,.2f}"
    except:
        return "$0.00"

def obtener_fecha_formateada(fecha_input):
    """
    Formatear fecha en español.
    Si fecha_input es dict, espera 'fecha_dia' y 'fecha_hora'
    Si es string, se asume que es una fecha
    """
    try:
        if isinstance(fecha_input, dict):
            fecha_dia = fecha_input.get('fecha_dia')
            hora = fecha_input.get('fecha_hora')
        else:
            # Asumimos que es un string de fecha
            fecha_dia = fecha_input
            hora = None

        if fecha_dia:
            if isinstance(fecha_dia, str):
                fecha_dia = datetime.strptime(fecha_dia, '%Y-%m-%d').date()
            if hora and isinstance(hora, str):
                try:
                    hora = datetime.strptime(hora, '%H:%M:%S').time()
                except:
                    hora = datetime.strptime(hora, '%H:%M').time()
                fecha_completa = datetime.combine(fecha_dia, hora)
            else:
                fecha_completa = datetime.combine(fecha_dia, datetime.min.time())
        else:
            fecha_completa = datetime.now()

        # Días en español
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        # Meses en español
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        dia_semana = dias[fecha_completa.weekday()]
        mes = meses[fecha_completa.month - 1]
        
        fecha_formateada = f"{dia_semana}, {fecha_completa.day} de {mes} de {fecha_completa.year}"
        hora_formateada = fecha_completa.strftime('%H:%M') if hora else ""
        
        return fecha_formateada, hora_formateada
        
    except Exception as e:
        logger.error(f"Error formateando fecha: {e}")
        # Fallback a fecha actual
        ahora = datetime.now()
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        fecha_formateada = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month - 1]} de {ahora.year}"
        hora_formateada = ahora.strftime('%H:%M')
        return fecha_formateada, hora_formateada

def convert_html_to_pdf(source_html):
    """Convertir HTML a PDF usando xhtml2pdf"""
    try:
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(source_html.encode("UTF-8")), result)
        
        if not pdf.err:
            return result.getvalue()
        else:
            logger.error(f"Error generando PDF: {pdf.err}")
            return None
    except Exception as e:
        logger.error(f"Error en convert_html_to_pdf: {e}")
        return None

def generar_html_fallback(html_content, nombre_archivo):
    """Generar HTML con opción de imprimir cuando no hay xhtml2pdf"""
    html_fallback = html_content.replace('</body>', f'''
    <script>
        // Auto-abrir diálogo de impresión después de cargar
        window.onload = function() {{
            // Esperar 1 segundo para que se cargue todo
            setTimeout(function() {{
                // Mostrar instrucciones primero
                alert("Para guardar como PDF:\\n1. Presione Ctrl+P\\n2. En 'Destino' seleccione 'Guardar como PDF'\\n3. Haga clic en 'Guardar'\\n\\nPresione OK para abrir el diálogo de impresión.");
                
                // Abrir diálogo de impresión
                window.print();
            }}, 1000);
        }};
        
        // También agregar botón de impresión visible
        document.addEventListener('DOMContentLoaded', function() {{
            // Agregar botón de impresión flotante
            const printBtn = document.createElement('div');
            printBtn.style.position = 'fixed';
            printBtn.style.bottom = '20px';
            printBtn.style.right = '20px';
            printBtn.style.backgroundColor = '#4CAF50';
            printBtn.style.color = 'white';
            printBtn.style.padding = '10px 20px';
            printBtn.style.borderRadius = '5px';
            printBtn.style.cursor = 'pointer';
            printBtn.style.zIndex = '9999';
            printBtn.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
            printBtn.innerHTML = '<i class="fas fa-print"></i> Imprimir / Guardar PDF';
            printBtn.onclick = function() {{ 
                alert("Para guardar como PDF:\\n1. Presione Ctrl+P\\n2. En 'Destino' seleccione 'Guardar como PDF'\\n3. Haga clic en 'Guardar'");
                window.print(); 
            }};
            document.body.appendChild(printBtn);
        }});
    </script>
    </body>
    ''')
    
    response = make_response(html_fallback)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

# ===== FACTURA DE VENTA (EXISTENTE) =====

@ventas_pdf_bp.route('/<int:venta_id>/factura-pdf', methods=['GET'])
def generar_factura_pdf(venta_id):
    """Generar PDF de factura con diseño profesional (solo negro para impresoras)"""
    try:
        logger.info(f"Generando factura PDF para venta ID: {venta_id}")
        
        # Obtener datos de la venta
        venta = VentaModel.obtener_venta_para_factura(venta_id)
        
        if not venta:
            logger.warning(f"Venta no encontrada: {venta_id}")
            return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
        
        # Obtener parámetros del usuario
        cajero = request.args.get('cajero', 'SISTEMA')
        dias_credito = request.args.get('dias_credito', '30')
        anticipo = request.args.get('anticipo', '0')
        pago_recibido = request.args.get('pago_recibido', '0')
        
        # Obtener tipo de pago de la venta
        tipo_pago = venta.get('tipo_pago', 'contado')
        
        # Formatear fecha
        fecha_formateada, hora_formateada = obtener_fecha_formateada(venta)
        
        # Variables para manejar diferentes tipos de pago
        total_float = float(venta.get('total', 0))
        mostrar_mixta = False
        componentes_mixta_html = ""
        
        # Si es venta mixta, procesar componentes
        if tipo_pago == 'mixto' and 'mixta_info' in venta:
            mostrar_mixta = True
            componentes_mixta = venta['mixta_info']
            
            # Generar HTML para cada componente
            for i, comp in enumerate(componentes_mixta, 1):
                metodo_html = ""
                
                if comp['categoria'] == 'CONTADO':
                    dinero_entregado = comp.get('dinero_entregado', comp['monto'])
                    cambio = comp.get('cambio', 0)
                    
                    metodo_html = f"""
                    <div style="margin-bottom: 10px; padding: 8px; background-color: #f0f0f0; border-radius: 4px;">
                        <div style="font-weight: bold; text-decoration: underline;">CONTADO: {formato_moneda(comp['monto'])}</div>
                        <div style="font-size: 9px; margin-left: 15px;">
                            <div>Dinero Entregado: {formato_moneda(dinero_entregado)}</div>
                            <div>Cambio: {formato_moneda(cambio)}</div>
                        </div>
                    </div>
                    """
                elif comp['categoria'] == 'BANCO':
                    submetodo = comp.get('submetodo', '').upper()
                    metodo_html = f"""
                    <div style="margin-bottom: 10px; padding: 8px; background-color: #f0f0f0; border-radius: 4px;">
                        <div style="font-weight: bold; text-decoration: underline;">BANCO ({submetodo}): {formato_moneda(comp['monto'])}</div>
                    </div>
                    """
                
                componentes_mixta_html += metodo_html
        
        # Determinar qué secciones mostrar según tipo de pago
        mostrar_pago_efectivo = tipo_pago == 'contado' and float(pago_recibido or 0) > 0
        mostrar_credito = tipo_pago == 'credito'
        mostrar_banco = tipo_pago == 'banco'
        
        # Calcular valores según tipo de pago
        if not mostrar_mixta:
            try:
                total_float = float(venta.get('total', 0))
                anticipo_float = float(anticipo)
                
                if tipo_pago == 'contado':
                    pago_recibido_float = float(pago_recibido) if pago_recibido and float(pago_recibido) > 0 else total_float
                    cambio = max(0, pago_recibido_float - total_float) if pago_recibido_float > 0 else 0
                    saldo_pendiente = 0
                elif tipo_pago == 'credito':
                    pago_recibido_float = anticipo_float
                    cambio = 0
                    saldo_pendiente = max(0, total_float - anticipo_float)
                else:  # banco
                    pago_recibido_float = total_float
                    cambio = 0
                    saldo_pendiente = 0
            except Exception as e:
                logger.error(f"Error calculando valores: {e}")
                total_float = 0
                pago_recibido_float = 0
                cambio = 0
                saldo_pendiente = 0
        
        # Preparar productos HTML
        productos_html = ""
        for producto in venta.get('productos', []):
            productos_html += f"""
            <tr>
                <td style="width: 15%; text-align: center; border-bottom: 1px dashed #000; padding: 5px;">{producto['cantidad_vendida']}</td>
                <td style="width: 55%; border-bottom: 1px dashed #000; padding: 5px;">
                    {producto['producto_nombre']}
                    <div style="font-size: 9px; color: #000;">({producto.get('presentacion', '')})</div>
                </td>
                <td style="width: 30%; text-align: right; border-bottom: 1px dashed #000; padding: 5px;">{formato_moneda(producto['precio_neto'])}</td>
            </tr>
            """
        
        # Crear HTML para el PDF (TODO EN NEGRO)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Factura #{venta_id} - {Config.EMPRESA['nombre']}</title>
            <style>
                @page {{
                    size: 80mm auto;
                    margin: 2mm;
                }}
                
                body {{
                    font-family: 'Arial', 'Helvetica', sans-serif;
                    font-size: 10px;
                    width: 76mm;
                    margin: 0 auto;
                    padding: 0;
                    line-height: 1.2;
                    color: #000000 !important;
                }}
                
                /* TODOS LOS COLORES EN NEGRO */
                * {{
                    color: #000000 !important;
                }}
                
                /* Encabezado */
                .header {{
                    text-align: center;
                    margin-bottom: 10px;
                    padding-bottom: 8px;
                    border-bottom: 2px solid #000;
                }}
                
                .empresa-nombre {{
                    font-weight: bold;
                    font-size: 13px;
                    margin: 5px 0;
                    text-transform: uppercase;
                }}
                
                .empresa-info {{
                    font-size: 9px;
                    margin: 2px 0;
                }}
                
                /* Información del ticket */
                .ticket-header {{
                    text-align: center;
                    margin: 10px 0;
                    padding: 8px 0;
                }}
                
                .ticket-title {{
                    font-weight: bold;
                    font-size: 12px;
                    margin: 5px 0;
                }}
                
                .ticket-numero {{
                    font-size: 14px;
                    font-weight: bold;
                    margin: 5px 0;
                }}
                
                .ticket-info {{
                    font-size: 9px;
                    margin: 3px 0;
                }}
                
                /* Información de cliente y cajero */
                .info-section {{
                    margin: 8px 0;
                    padding: 6px;
                    background-color: #f0f0f0;
                    border-radius: 3px;
                    border: 1px solid #000;
                }}
                
                .info-row {{
                    margin: 4px 0;
                }}
                
                .info-label {{
                    font-weight: bold;
                    display: inline-block;
                    width: 40%;
                }}
                
                .info-value {{
                    display: inline-block;
                    width: 58%;
                    text-align: right;
                }}
                
                /* Tabla de productos */
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                
                th {{
                    text-align: left;
                    padding: 5px 3px;
                    border-bottom: 2px solid #000;
                    font-weight: bold;
                    background-color: #e0e0e0;
                }}
                
                /* Totales */
                .totales-section {{
                    margin-top: 15px;
                    padding-top: 10px;
                    border-top: 2px solid #000;
                }}
                
                .total-row {{
                    margin: 5px 0;
                    padding: 3px 0;
                }}
                
                .total-label {{
                    font-weight: bold;
                    display: inline-block;
                    width: 60%;
                }}
                
                .total-value {{
                    font-weight: bold;
                    display: inline-block;
                    width: 38%;
                    text-align: right;
                }}
                
                .total-grande {{
                    font-size: 12px;
                    border-top: 2px solid #000;
                    border-bottom: 2px solid #000;
                    padding: 8px 0;
                    margin: 10px 0;
                }}
                
                /* Información de pago */
                .pago-section {{
                    margin: 12px 0;
                    padding: 8px;
                    background-color: #f0f0f0;
                    border: 1px solid #000;
                    border-radius: 4px;
                }}
                
                .saldo-pendiente {{
                    font-weight: bold;
                }}
                
                /* Footer */
                .footer {{
                    text-align: center;
                    margin-top: 15px;
                    padding-top: 10px;
                    border-top: 1px dashed #000;
                    font-size: 8px;
                }}
                
                .footer-line {{
                    margin: 2px 0;
                }}
                
                /* Líneas divisorias */
                .divider {{
                    border-bottom: 1px dashed #000;
                    margin: 10px 0;
                }}
                
                .double-divider {{
                    border-bottom: 3px double #000;
                    margin: 15px 0;
                }}
                
                /* Utilidades */
                .text-center {{ text-align: center; }}
                .text-right {{ text-align: right; }}
                .text-bold {{ font-weight: bold; }}
                .text-small {{ font-size: 8px; }}
                .text-underline {{ text-decoration: underline; }}
                .text-bolder {{ font-weight: bolder; }}
                
                /* Solo para impresión térmica */
                @media print {{
                    body {{
                        color: #000000 !important;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                    
                    .pago-section, .info-section {{
                        background-color: #f0f0f0 !important;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                    
                    th {{
                        background-color: #e0e0e0 !important;
                        -webkit-print-color-adjust: exact;
                        print-color-adjust: exact;
                    }}
                }}
            </style>
        </head>
        <body>
            <!-- Encabezado -->
            <div class="header">
                <div class="empresa-nombre">{Config.EMPRESA['nombre']}</div>
                <div class="empresa-info">Teléfono: {Config.EMPRESA['telefono']}</div>
                {f'<div class="empresa-info">{Config.EMPRESA.get("direccion", "")}</div>' if Config.EMPRESA.get('direccion') else ''}
                {f'<div class="empresa-info">NIT: {Config.EMPRESA.get("nit", "")}</div>' if Config.EMPRESA.get('nit') else ''}
            </div>
            
            <div class="double-divider"></div>
            
            <!-- Información del ticket -->
            <div class="ticket-header">
                <div class="ticket-title">TICKET DE VENTA</div>
                <div class="ticket-numero">#{venta_id:04d}</div>
                <div class="ticket-info">{fecha_formateada}</div>
                <div class="ticket-info">{hora_formateada}</div>
            </div>
            
            <div class="divider"></div>
            
            <!-- Información del cajero y cliente -->
            <div class="info-section">
                <div class="info-row">
                    <span class="info-label">Cajero(a):</span>
                    <span class="info-value">{cajero}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Cliente:</span>
                    <span class="info-value">{venta.get('nombre_cliente', 'CLIENTE FINAL')}</span>
                </div>
                {f'<div class="info-row"><span class="info-label">Identificador:</span><span class="info-value">{venta.get("cliente_cedula", "")}</span></div>' if venta.get('cliente_cedula') and venta['cliente_cedula'] != 'final' else ''}
                {f'<div class="info-row"><span class="info-label">Tipo de Venta:</span><span class="info-value">{tipo_pago.upper()}</span></div>'}
            </div>
            
            <div class="divider"></div>
            
            <!-- Tabla de productos -->
            <table>
                <thead>
                    <tr>
                        <th style="width: 15%; text-align: center;">Cant.</th>
                        <th style="width: 55%;">Producto</th>
                        <th style="width: 30%; text-align: right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {productos_html}
                </tbody>
            </table>
            
            <div class="divider"></div>
            
            <!-- Totales -->
            <div class="totales-section">
                <div class="total-row">
                    <span class="total-label">Sub Total:</span>
                    <span class="total-value">{formato_moneda(venta.get('subtotal', 0))}</span>
                </div>
                
                <div class="total-row">
                    <span class="total-label">Descuento:</span>
                    <span class="total-value">{formato_moneda(venta.get('descuento', 0))}</span>
                </div>
                
                <!-- Sección de métodos de pago Mixtos -->
                {f'''
                <div class="pago-section">
                    <div style="font-weight: bold; text-align: center; margin-bottom: 8px; text-decoration: underline;">DESGLOSE DE PAGO MIXTO</div>
                    {componentes_mixta_html}
                </div>
                ''' if mostrar_mixta else ''}
                
                <!-- Mostrar anticipo solo para crédito normal -->
                {f'''
                <div class="total-row">
                    <span class="total-label">Anticipo:</span>
                    <span class="total-value">-{formato_moneda(anticipo)}</span>
                </div>
                ''' if mostrar_credito and float(anticipo) > 0 else ''}
                
                <!-- Mostrar dinero entregado y cambio si es contado normal -->
                {f'''
                <div class="pago-section">
                    <div class="total-row">
                        <span class="total-label">Dinero Entregado:</span>
                        <span class="total-value">{formato_moneda(pago_recibido_float)}</span>
                    </div>
                    
                    <div class="total-row">
                        <span class="total-label">Cambio:</span>
                        <span class="total-value">{formato_moneda(cambio)}</span>
                    </div>
                </div>
                ''' if mostrar_pago_efectivo and not mostrar_mixta else ''}
                
                <div class="total-row total-grande">
                    <span class="total-label">TOTAL:</span>
                    <span class="total-value">{formato_moneda(venta.get('total', 0))}</span>
                </div>
                
                <!-- Mostrar saldo pendiente si es crédito normal -->
                {f'''
                <div class="pago-section saldo-pendiente">
                    <div class="total-row">
                        <span class="total-label">SALDO PENDIENTE:</span>
                        <span class="total-value">{formato_moneda(saldo_pendiente)}</span>
                    </div>
                </div>
                ''' if mostrar_credito and saldo_pendiente > 0 else ''}
                
                <!-- Información de método de pago para ventas normales -->
                {f'''
                <div class="info-section">
                    <div class="info-row">
                        <span class="info-label">Método de Pago:</span>
                        <span class="info-value">{tipo_pago.upper()}</span>
                    </div>
                    
                    {f'<div class="info-row"><span class="info-label">Días de Crédito:</span><span class="info-value">{dias_credito} días</span></div>' if mostrar_credito else ''}
                    
                    {f'<div class="info-row"><span class="info-label">Medio Bancario:</span><span class="info-value">{venta.get("submetodo_banco", "").upper()}</span></div>' if mostrar_banco and venta.get('submetodo_banco') else ''}
                </div>
                ''' if not mostrar_mixta else ''}
            </div>
            
            <div class="double-divider"></div>
            
            <!-- QR Placeholder -->
            <div class="text-center">
                <div class="text-small text-bold">CÓDIGO DE VERIFICACIÓN</div>
                <div class="text-small">Venta #{venta_id} - {datetime.now().strftime('%d/%m/%Y')}</div>
            </div>
            
            <!-- Footer -->
            <div class="footer">
                <div class="footer-line">¡Gracias por su compra!</div>
                <div class="footer-line">Vuelva pronto</div>
                <div class="footer-line text-bold">--- {Config.EMPRESA['nombre']} ---</div>
                <div class="footer-line">Sistema POS - Agrovet Yacuanquer</div>
                <div class="footer-line">Tel: {Config.EMPRESA['telefono']}</div>
                <div class="footer-line">Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </body>
        </html>
        """
        
        # Generar PDF con xhtml2pdf si está disponible
        if XHTML2PDF_AVAILABLE:
            try:
                pdf_bytes = convert_html_to_pdf(html_content)
                
                if pdf_bytes:
                    # Crear respuesta con PDF
                    response = make_response(pdf_bytes)
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = f'inline; filename="factura_{venta_id}.pdf"'
                    
                    logger.info(f"PDF generado exitosamente para venta {venta_id}")
                    return response
                else:
                    # Si falla la generación de PDF, devolver HTML
                    return generar_html_fallback(html_content, f"factura_{venta_id}")
                
            except Exception as pdf_error:
                logger.error(f"Error generando PDF con xhtml2pdf: {pdf_error}")
                # Fallback a HTML con opción de imprimir
                return generar_html_fallback(html_content, f"factura_{venta_id}")
        else:
            # xhtml2pdf no está disponible, devolver HTML con opción de imprimir
            logger.warning("xhtml2pdf no disponible, usando HTML fallback")
            return generar_html_fallback(html_content, f"factura_{venta_id}")
            
    except Exception as e:
        logger.error(f"Error al generar factura PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al generar factura: {str(e)}'
        }), 500

# ===== NUEVA RUTA: FACTURA DE CRÉDITO =====

@ventas_pdf_bp.route('/credito/<int:credito_id>/factura-pdf', methods=['GET'])
def generar_factura_credito_pdf(credito_id):
    """
    Genera PDF con la información de un crédito específico.
    Parámetros opcionales: ?cajero=...&indice=...&total=...
    """
    try:
        logger.info(f"Generando factura para crédito ID: {credito_id}")
        
        # Obtener parámetros
        cajero = request.args.get('cajero', 'SISTEMA')
        indice = request.args.get('indice', '')
        total_creditos = request.args.get('total', '')

        # Obtener datos completos del crédito
        credito = ClienteProveedorModel.obtener_credito_con_detalle(credito_id)
        if not credito:
            return jsonify({'success': False, 'message': 'Crédito no encontrado'}), 404

        # Formatear fechas
        fecha_inicio, _ = obtener_fecha_formateada(credito.get('fecha_inicio'))
        fecha_vencimiento, _ = obtener_fecha_formateada(credito.get('fecha_vencimiento'))
        fecha_venta, _ = obtener_fecha_formateada(credito.get('venta_fecha'))

        # Productos HTML
        productos_html = ""
        for prod in credito.get('productos', []):
            productos_html += f"""
            <tr>
                <td style="width:15%; text-align:center; border-bottom:1px dashed #000; padding:5px;">{prod['cantidad_vendida']}</td>
                <td style="width:55%; border-bottom:1px dashed #000; padding:5px;">
                    {prod['producto_nombre']}
                    <div style="font-size:9px;">({prod.get('presentacion','')})</div>
                </td>
                <td style="width:30%; text-align:right; border-bottom:1px dashed #000; padding:5px;">{formato_moneda(prod['precio_neto'])}</td>
            </tr>
            """

        # Título con contador si se proporciona
        titulo = f"CRÉDITO #{credito_id:04d}"
        if indice and total_creditos:
            titulo = f"CRÉDITO {indice} DE {total_creditos} - #{credito_id:04d}"

        # Construir HTML (mismos estilos que la factura de venta)
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Factura Crédito #{credito_id} - {Config.EMPRESA['nombre']}</title>
            <style>
                @page {{ size: 80mm auto; margin: 2mm; }}
                body {{
                    font-family: 'Arial', sans-serif;
                    font-size: 10px;
                    width: 76mm;
                    margin:0 auto;
                    color:#000 !important;
                }}
                .header {{ text-align:center; margin-bottom:10px; border-bottom:2px solid #000; }}
                .empresa-nombre {{ font-weight:bold; font-size:13px; }}
                .empresa-info {{ font-size:9px; }}
                .ticket-header {{ text-align:center; margin:10px 0; }}
                .ticket-title {{ font-weight:bold; font-size:12px; }}
                .ticket-numero {{ font-size:14px; font-weight:bold; }}
                .ticket-info {{ font-size:9px; }}
                .info-section {{ margin:8px 0; padding:6px; background:#f0f0f0; border:1px solid #000; }}
                .info-row {{ margin:4px 0; }}
                .info-label {{ font-weight:bold; display:inline-block; width:40%; }}
                .info-value {{ display:inline-block; width:58%; text-align:right; }}
                table {{ width:100%; border-collapse:collapse; margin:10px 0; }}
                th {{ text-align:left; padding:5px; border-bottom:2px solid #000; background:#e0e0e0; }}
                .totales-section {{ margin-top:15px; padding-top:10px; border-top:2px solid #000; }}
                .total-row {{ margin:5px 0; }}
                .total-label {{ font-weight:bold; display:inline-block; width:60%; }}
                .total-value {{ display:inline-block; width:38%; text-align:right; }}
                .total-grande {{ font-size:12px; border-top:2px solid #000; border-bottom:2px solid #000; padding:8px 0; }}
                .pago-section {{ margin:12px 0; padding:8px; background:#f0f0f0; border:1px solid #000; }}
                .footer {{ text-align:center; margin-top:15px; padding-top:10px; border-top:1px dashed #000; font-size:8px; }}
                .divider {{ border-bottom:1px dashed #000; margin:10px 0; }}
                .double-divider {{ border-bottom:3px double #000; margin:15px 0; }}
                @media print {{ 
                    body {{ color:#000 !important; }} 
                    .pago-section, .info-section, th {{ background:#f0f0f0 !important; -webkit-print-color-adjust: exact; }} 
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="empresa-nombre">{Config.EMPRESA['nombre']}</div>
                <div class="empresa-info">Teléfono: {Config.EMPRESA['telefono']}</div>
                {f'<div class="empresa-info">{Config.EMPRESA.get("direccion", "")}</div>' if Config.EMPRESA.get('direccion') else ''}
                {f'<div class="empresa-info">NIT: {Config.EMPRESA.get("nit", "")}</div>' if Config.EMPRESA.get('nit') else ''}
            </div>
            
            <div class="double-divider"></div>
            
            <div class="ticket-header">
                <div class="ticket-title">FACTURA DE CRÉDITO</div>
                <div class="ticket-numero">{titulo}</div>
                <div class="ticket-info">Fecha venta: {fecha_venta}</div>
                <div class="ticket-info">Fecha inicio: {fecha_inicio}</div>
                <div class="ticket-info">Vence: {fecha_vencimiento}</div>
            </div>
            
            <div class="divider"></div>
            
            <div class="info-section">
                <div class="info-row"><span class="info-label">Cajero(a):</span><span class="info-value">{cajero}</span></div>
                <div class="info-row"><span class="info-label">Cliente:</span><span class="info-value">{credito.get('cliente_nombre', '')}</span></div>
                <div class="info-row"><span class="info-label">Teléfono:</span><span class="info-value">{credito.get('cliente_telefono', '')}</span></div>
                <div class="info-row"><span class="info-label">Cédula:</span><span class="info-value">{credito.get('cliente_cedula', '')}</span></div>
                <div class="info-row"><span class="info-label">Venta asociada:</span><span class="info-value">#{credito.get('numero_venta', '')}</span></div>
            </div>
            
            <div class="divider"></div>
            
            <table>
                <thead>
                    <tr>
                        <th style="width:15%; text-align:center;">Cant.</th>
                        <th style="width:55%;">Producto</th>
                        <th style="width:30%; text-align:right;">Importe</th>
                    </tr>
                </thead>
                <tbody>
                    {productos_html}
                </tbody>
            </table>
            
            <div class="divider"></div>
            
            <div class="totales-section">
                <div class="total-row"><span class="total-label">Sub Total:</span><span class="total-value">{formato_moneda(credito.get('venta_subtotal', 0))}</span></div>
                <div class="total-row"><span class="total-label">Descuento:</span><span class="total-value">{formato_moneda(credito.get('venta_descuento', 0))}</span></div>
                <div class="total-row total-grande"><span class="total-label">TOTAL VENTA:</span><span class="total-value">{formato_moneda(credito.get('venta_total', 0))}</span></div>
                
                <div class="pago-section">
                    <div class="total-row"><span class="total-label">Anticipo:</span><span class="total-value">{formato_moneda(credito.get('anticipo', 0))}</span></div>
                    <div class="total-row"><span class="total-label">Deuda inicial:</span><span class="total-value">{formato_moneda(credito.get('deuda_inicial', 0))}</span></div>
                    <div class="total-row"><span class="total-label">Abonos realizados:</span><span class="total-value">{formato_moneda(credito.get('abonos_realizados', 0))}</span></div>
                    <div class="total-row"><span class="total-label" style="font-weight:bold;">SALDO PENDIENTE:</span><span class="total-value" style="font-weight:bold;">{formato_moneda(credito.get('saldo_pendiente', 0))}</span></div>
                </div>
            </div>
            
            <div class="double-divider"></div>
            
            <div class="footer">
                <div class="footer-line">¡Gracias por su confianza!</div>
                <div class="footer-line">--- {Config.EMPRESA['nombre']} ---</div>
                <div class="footer-line">Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </body>
        </html>
        """

        # Generar PDF o HTML fallback
        if XHTML2PDF_AVAILABLE:
            pdf_bytes = convert_html_to_pdf(html_content)
            if pdf_bytes:
                response = make_response(pdf_bytes)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'inline; filename="credito_{credito_id}.pdf"'
                return response
        return generar_html_fallback(html_content, f"credito_{credito_id}")

    except Exception as e:
        logger.error(f"Error generando factura de crédito: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ===== NUEVA RUTA: COMPROBANTE DE ABONO =====

@ventas_pdf_bp.route('/credito/<int:credito_id>/abono-factura-pdf', methods=['GET'])
def generar_factura_abono_pdf(credito_id):
    """
    Genera comprobante de abono para un crédito.
    Parámetros requeridos: monto, fecha, nuevo_saldo
    Opcionales: observaciones, cajero
    """
    try:
        logger.info(f"Generando comprobante de abono para crédito ID: {credito_id}")

        # Obtener parámetros
        monto_abono = request.args.get('monto', '')
        fecha_abono = request.args.get('fecha', '')
        nuevo_saldo = request.args.get('nuevo_saldo', '')
        observaciones = request.args.get('observaciones', '')
        cajero = request.args.get('cajero', 'SISTEMA')

        if not monto_abono or not fecha_abono or not nuevo_saldo:
            return jsonify({'success': False, 'message': 'Faltan datos del abono (monto, fecha, nuevo_saldo)'}), 400

        # Obtener datos del crédito (para cliente)
        credito = ClienteProveedorModel.obtener_credito_con_detalle(credito_id)
        if not credito:
            return jsonify({'success': False, 'message': 'Crédito no encontrado'}), 404

        # Formatear fecha de abono
        fecha_abono_formateada, _ = obtener_fecha_formateada(fecha_abono)

        # HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Comprobante Abono #{credito_id} - {Config.EMPRESA['nombre']}</title>
            <style>
                @page {{ size: 80mm auto; margin: 2mm; }}
                body {{
                    font-family: 'Arial', sans-serif;
                    font-size: 10px;
                    width: 76mm;
                    margin:0 auto;
                    color:#000 !important;
                }}
                .header {{ text-align:center; margin-bottom:10px; border-bottom:2px solid #000; }}
                .empresa-nombre {{ font-weight:bold; font-size:13px; }}
                .empresa-info {{ font-size:9px; }}
                .ticket-header {{ text-align:center; margin:10px 0; }}
                .ticket-title {{ font-weight:bold; font-size:12px; }}
                .ticket-numero {{ font-size:14px; font-weight:bold; }}
                .ticket-info {{ font-size:9px; }}
                .info-section {{ margin:8px 0; padding:6px; background:#f0f0f0; border:1px solid #000; }}
                .info-row {{ margin:4px 0; }}
                .info-label {{ font-weight:bold; display:inline-block; width:40%; }}
                .info-value {{ display:inline-block; width:58%; text-align:right; }}
                .pago-section {{ margin:12px 0; padding:8px; background:#f0f0f0; border:1px solid #000; }}
                .total-row {{ margin:5px 0; }}
                .total-label {{ font-weight:bold; display:inline-block; width:50%; }}
                .total-value {{ display:inline-block; width:48%; text-align:right; }}
                .footer {{ text-align:center; margin-top:15px; padding-top:10px; border-top:1px dashed #000; font-size:8px; }}
                .divider {{ border-bottom:1px dashed #000; margin:10px 0; }}
                .double-divider {{ border-bottom:3px double #000; margin:15px 0; }}
                @media print {{ 
                    body {{ color:#000 !important; }} 
                    .info-section, .pago-section {{ background:#f0f0f0 !important; -webkit-print-color-adjust: exact; }} 
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="empresa-nombre">{Config.EMPRESA['nombre']}</div>
                <div class="empresa-info">Teléfono: {Config.EMPRESA['telefono']}</div>
                {f'<div class="empresa-info">{Config.EMPRESA.get("direccion", "")}</div>' if Config.EMPRESA.get('direccion') else ''}
                {f'<div class="empresa-info">NIT: {Config.EMPRESA.get("nit", "")}</div>' if Config.EMPRESA.get('nit') else ''}
            </div>
            
            <div class="double-divider"></div>
            
            <div class="ticket-header">
                <div class="ticket-title">COMPROBANTE DE ABONO</div>
                <div class="ticket-numero">Crédito #{credito_id:04d}</div>
            </div>
            
            <div class="divider"></div>
            
            <div class="info-section">
                <div class="info-row"><span class="info-label">Cajero(a):</span><span class="info-value">{cajero}</span></div>
                <div class="info-row"><span class="info-label">Cliente:</span><span class="info-value">{credito.get('cliente_nombre', '')}</span></div>
                <div class="info-row"><span class="info-label">Teléfono:</span><span class="info-value">{credito.get('cliente_telefono', '')}</span></div>
                <div class="info-row"><span class="info-label">Cédula:</span><span class="info-value">{credito.get('cliente_cedula', '')}</span></div>
            </div>
            
            <div class="divider"></div>
            
            <div class="pago-section">
                <div class="total-row"><span class="total-label">Saldo anterior:</span><span class="total-value">{formato_moneda(credito.get('saldo_pendiente', 0))}</span></div>
                <div class="total-row"><span class="total-label">Abono realizado:</span><span class="total-value">{formato_moneda(monto_abono)}</span></div>
                <div class="total-row"><span class="total-label">Nuevo saldo:</span><span class="total-value">{formato_moneda(nuevo_saldo)}</span></div>
                <div class="total-row"><span class="total-label">Fecha abono:</span><span class="total-value">{fecha_abono_formateada}</span></div>
                {f'<div class="total-row"><span class="total-label">Observaciones:</span><span class="total-value">{observaciones}</span></div>' if observaciones else ''}
            </div>
            
            <div class="double-divider"></div>
            
            <div class="footer">
                <div class="footer-line">--- {Config.EMPRESA['nombre']} ---</div>
                <div class="footer-line">Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </body>
        </html>
        """

        if XHTML2PDF_AVAILABLE:
            pdf_bytes = convert_html_to_pdf(html_content)
            if pdf_bytes:
                response = make_response(pdf_bytes)
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'inline; filename="abono_{credito_id}.pdf"'
                return response
        return generar_html_fallback(html_content, f"abono_{credito_id}")

    except Exception as e:
        logger.error(f"Error generando comprobante de abono: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500