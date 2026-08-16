from flask import Blueprint, request, jsonify, make_response
from modelo.venta_model import VentaModel
from modelo.producto_model import ProductoModel
from modelo.cliente_model import ClienteModel
from config import Config
from jinja2 import Template
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

def formato_moneda(valor):
    """Formatear valor a moneda colombiana"""
    try:
        valor_float = float(valor)
        return f"${valor_float:,.2f}"
    except:
        return "$0.00"

def obtener_fecha_formateada(venta):
    """Obtener fecha formateada en español"""
    try:
        fecha_venta = venta.get('fecha_dia')
        hora_venta = venta.get('fecha_hora')
        
        if fecha_venta and hora_venta:
            # Convertir strings a objetos datetime si es necesario
            if isinstance(fecha_venta, str):
                fecha_venta = datetime.strptime(fecha_venta, '%Y-%m-%d').date()
            if isinstance(hora_venta, str):
                try:
                    hora_venta = datetime.strptime(hora_venta, '%H:%M:%S').time()
                except:
                    hora_venta = datetime.strptime(hora_venta, '%H:%M').time()
            
            fecha_completa = datetime.combine(fecha_venta, hora_venta)
            
            # Días en español
            dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            # Meses en español
            meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 
                    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
            
            dia_semana = dias[fecha_completa.weekday()]
            mes = meses[fecha_completa.month - 1]
            
            fecha_formateada = f"{dia_semana}, {fecha_completa.day} de {mes} de {fecha_completa.year}"
            hora_formateada = fecha_completa.strftime('%H:%M')
            
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

@ventas_pdf_bp.route('/<int:venta_id>/factura-pdf', methods=['GET'])
def generar_factura_pdf(venta_id):
    """Generar PDF de factura con diseño profesional"""
    try:
        logger.info(f"Generando factura PDF para venta ID: {venta_id}")
        
        # Obtener datos de la venta
        venta = VentaModel.obtener_venta_para_factura(venta_id)
        
        if not venta:
            logger.warning(f"Venta no encontrada: {venta_id}")
            return jsonify({'success': False, 'message': 'Venta no encontrada'}), 404
        
        # Obtener parámetros
        cajero = request.args.get('cajero', 'SISTEMA')
        dias_credito = request.args.get('dias_credito', '30')
        anticipo = request.args.get('anticipo', '0')
        pago_recibido = request.args.get('pago_recibido', '0')
        
        # Obtener tipo de pago de la venta
        tipo_pago = venta.get('tipo_pago', 'contado')
        
        # Calcular valores según tipo de pago
        try:
            total_float = float(venta.get('total', 0))
            anticipo_float = float(anticipo)
            
            if tipo_pago == 'contado':
                pago_recibido_float = float(pago_recibido)
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
        
        # Formatear fecha
        fecha_formateada, hora_formateada = obtener_fecha_formateada(venta)
        
        # Preparar datos para el template
        productos_html = ""
        for producto in venta.get('productos', []):
            productos_html += f"""
            <tr>
                <td style="width: 15%; text-align: center; border-bottom: 1px dashed #999; padding: 5px;">{producto['cantidad_vendida']}</td>
                <td style="width: 55%; border-bottom: 1px dashed #999; padding: 5px;">
                    {producto['producto_nombre']}
                    <div style="font-size: 9px; color: #666;">({producto.get('presentacion', '')})</div>
                </td>
                <td style="width: 30%; text-align: right; border-bottom: 1px dashed #999; padding: 5px;">{formato_moneda(producto['precio_neto'])}</td>
            </tr>
            """
        
        # Determinar qué secciones mostrar según tipo de pago
        mostrar_pago_efectivo = tipo_pago == 'contado' and pago_recibido_float > 0
        mostrar_credito = tipo_pago == 'credito'
        mostrar_banco = tipo_pago == 'banco'
        mostrar_anticipo = mostrar_credito and anticipo_float > 0
        
        # Crear HTML para el PDF
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
                    color: #000000;
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
                    color: #000000;
                    margin: 5px 0;
                    text-transform: uppercase;
                }}
                
                .empresa-info {{
                    font-size: 9px;
                    margin: 2px 0;
                    color: #000000;
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
                    background-color: #e8f4f8;
                    border: 1px solid #b8d8e8;
                    border-radius: 4px;
                }}
                
                .saldo-pendiente {{
                    color: #d35400;
                    font-weight: bold;
                }}
                
                /* Footer */
                .footer {{
                    text-align: center;
                    margin-top: 15px;
                    padding-top: 10px;
                    border-top: 1px dashed #000;
                    font-size: 8px;
                    color: #000000;
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
                {f'<div class="info-row"><span class="info-label">Cédula:</span><span class="info-value">{venta.get("cliente_cedula", "")}</span></div>' if venta.get('cliente_cedula') and venta['cliente_cedula'] != 'final' else ''}
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
                
                <!-- Mostrar anticipo si es crédito -->
                {f'''
                <div class="total-row">
                    <span class="total-label">Anticipo:</span>
                    <span class="total-value">-{formato_moneda(anticipo)}</span>
                </div>
                ''' if mostrar_anticipo else ''}
                
                <!-- Mostrar dinero entregado y cambio si es contado -->
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
                ''' if mostrar_pago_efectivo else ''}
                
                <div class="total-row total-grande">
                    <span class="total-label">TOTAL:</span>
                    <span class="total-value">{formato_moneda(venta.get('total', 0))}</span>
                </div>
                
                <!-- Mostrar saldo pendiente si es crédito -->
                {f'''
                <div class="pago-section saldo-pendiente">
                    <div class="total-row">
                        <span class="total-label">SALDO PENDIENTE:</span>
                        <span class="total-value">{formato_moneda(saldo_pendiente)}</span>
                    </div>
                </div>
                ''' if mostrar_credito and saldo_pendiente > 0 else ''}
                
                <!-- Información de método de pago -->
                <div class="info-section">
                    <div class="info-row">
                        <span class="info-label">Método de Pago:</span>
                        <span class="info-value">{tipo_pago.upper()}</span>
                    </div>
                    
                    {f'<div class="info-row"><span class="info-label">Días de Crédito:</span><span class="info-value">{dias_credito} días</span></div>' if mostrar_credito else ''}
                    
                    {f'<div class="info-row"><span class="info-label">Medio Bancario:</span><span class="info-value">{venta.get("submetodo_banco", "").upper()}</span></div>' if mostrar_banco and venta.get('submetodo_banco') else ''}
                </div>
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
                    return generar_html_fallback(html_content, venta_id)
                
            except Exception as pdf_error:
                logger.error(f"Error generando PDF con xhtml2pdf: {pdf_error}")
                # Fallback a HTML con opción de imprimir
                return generar_html_fallback(html_content, venta_id)
        else:
            # xhtml2pdf no está disponible, devolver HTML con opción de imprimir
            logger.warning("xhtml2pdf no disponible, usando HTML fallback")
            return generar_html_fallback(html_content, venta_id)
            
    except Exception as e:
        logger.error(f"Error al generar factura PDF: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al generar factura: {str(e)}'
        }), 500

def generar_html_fallback(html_content, venta_id):
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
            printBtn.innerHTML = `
                <div style="position: fixed; top: 10px; right: 10px; background: #1F8A86; color: white; padding: 10px 15px; border-radius: 5px; cursor: pointer; z-index: 10000; box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
                    <i class="fas fa-print"></i> Imprimir / Guardar PDF
                </div>
            `;
            printBtn.onclick = function() {{ 
                alert("Para guardar como PDF:\\n1. Presione Ctrl+P\\n2. En 'Destino' seleccione 'Guardar como PDF'\\n3. Haga clic en 'Guardar'");
                window.print(); 
            }};
            document.body.appendChild(printBtn);
            
            // Agregar instrucciones flotantes
            const instructions = document.createElement('div');
            instructions.innerHTML = `
                <div style="position: fixed; bottom: 10px; left: 10px; right: 10px; background: #f8f9fa; border: 2px solid #1a5f7a; padding: 10px; border-radius: 5px; z-index: 10000; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="font-weight: bold; color: #1a5f7a; margin-bottom: 5px;">INSTRUCCIONES PARA PDF:</div>
                    <div style="font-size: 10px; line-height: 1.4;">
                        1. Presione <strong>Ctrl+P</strong> o use el botón arriba<br>
                        2. En "Destino", seleccione <strong>"Guardar como PDF"</strong><br>
                        3. Configure "Disposición" como <strong>"Vertical"</strong><br>
                        4. Haga clic en <strong>"Guardar"</strong><br>
                        5. Para PDF automático, instale: <code>pip install xhtml2pdf</code>
                    </div>
                </div>
            `;
            document.body.appendChild(instructions);
        }});
    </script>
    </body>
    ''')
    
    response = make_response(html_fallback)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response