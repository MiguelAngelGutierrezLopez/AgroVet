from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, date
import logging
import sys
import os

# Agregar ruta para importar modelos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from modelo.historial_venta_model import model
    logger = logging.getLogger(__name__)
    logger.info("Modelo de historial de ventas importado correctamente")
except Exception as e:
    print(f"Error importando modelo: {e}")
    import traceback
    traceback.print_exc()
    # Crear un modelo dummy para evitar errores
    class DummyModel:
        @staticmethod
        def obtener_historial_completo():
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def filtrar_ventas(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def obtener_estadisticas_periodo(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def obtener_detalle_venta(venta_id):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def obtener_clientes_para_filtro():
            return {'success': False, 'error': 'Modelo no cargado', 'usuarios': []}
        @staticmethod
        def obtener_productos_para_filtro():
            return {'success': False, 'error': 'Modelo no cargado', 'productos': []}
        @staticmethod
        def obtener_ventas_recientes(limit=10):
            return {'success': False, 'error': 'Modelo no cargado', 'ventas': []}
        @staticmethod
        def obtener_estadisticas_financieras(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def obtener_estadisticas_financieras_periodo_rapido(periodo):
            return {'success': False, 'error': 'Modelo no cargado', 'estadisticas': {}}
        @staticmethod
        def eliminar_venta_completa(venta_id, recuperar_productos=False):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def eliminar_ventas_multiples(ventas_ids, recuperar_productos=False):
            return {'success': False, 'error': 'Modelo no cargado', 'eliminadas': 0}
        @staticmethod
        def verificar_venta_para_eliminar(venta_id):
            return {'success': False, 'error': 'Modelo no cargado'}
        @staticmethod
        def obtener_ingresos_por_categoria_pago(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'ingresos': []}
        @staticmethod
        def obtener_tendencia_ventas(**kwargs):
            return {'success': False, 'error': 'Modelo no cargado', 'tendencia': []}
    
    model = DummyModel()

# Crear blueprint
historial_venta_bp = Blueprint('historial_venta', __name__)


@historial_venta_bp.route('/api/historial-ventas', methods=['GET'])
def obtener_historial():
    """Obtener historial completo de ventas"""
    try:
        logger.info("Solicitando historial completo de ventas")
        resultado = model.obtener_historial_completo()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_historial: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500


@historial_venta_bp.route('/api/historial-ventas/filtrar', methods=['GET'])
def filtrar_historial():
    """Filtrar historial de ventas con normalización de datos"""
    try:
        # Obtener parámetros de la consulta
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_pago = request.args.get('tipo_pago')
        tipo_usuario = request.args.get('tipo_usuario')
        cliente_cedula = request.args.get('cliente_cedula')
        producto_id = request.args.get('producto_id')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        # ============================================================
        #  CORRECCIÓN: Validar y normalizar fechas
        # ============================================================
        if fecha_inicio:
            try:
                datetime.strptime(fecha_inicio, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de fecha inválido: {fecha_inicio}. Use YYYY-MM-DD'
                }), 400
        
        if fecha_fin:
            try:
                datetime.strptime(fecha_fin, '%Y-%m-%d')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Formato de fecha inválido: {fecha_fin}. Use YYYY-MM-DD'
                }), 400
        
        # ============================================================
        #  CORRECCIÓN: Normalizar horas (HH:MM → HH:MM:SS)
        # ============================================================
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        # ============================================================
        #  CORRECCIÓN: Normalizar tipo de pago (mayúsculas)
        # ============================================================
        if tipo_pago:
            tipo_pago = tipo_pago.upper()
        
        # ============================================================
        #  CORRECCIÓN: Normalizar cliente
        # ============================================================
        cliente_normalizado = None
        if cliente_cedula:
            cliente_cedula = cliente_cedula.strip()
            cliente_normalizado = cliente_cedula
        
        # ============================================================
        #  CORRECCIÓN: Validar producto_id
        # ============================================================
        producto_id_int = None
        if producto_id and producto_id.isdigit():
            producto_id_int = int(producto_id)
        
        # ============================================================
        #  CORRECCIÓN: Solo pasar filtros con valor (ignorar vacíos)
        # ============================================================
        kwargs = {}
        if fecha_inicio:
            kwargs['fecha_inicio'] = fecha_inicio
        if fecha_fin:
            kwargs['fecha_fin'] = fecha_fin
        if tipo_pago:
            kwargs['tipo_pago'] = tipo_pago
        if cliente_normalizado:
            kwargs['cliente_cedula'] = cliente_normalizado
        if producto_id_int:
            kwargs['producto_id'] = producto_id_int
        if hora_inicio:
            kwargs['hora_inicio'] = hora_inicio
        if hora_fin:
            kwargs['hora_fin'] = hora_fin
        
        logger.info(f"Filtros normalizados: {kwargs}")
        
        resultado = model.filtrar_ventas(**kwargs)
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en filtrar_historial: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500


@historial_venta_bp.route('/api/historial-ventas/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas del período"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        logger.info(f"Obteniendo estadísticas para período: {fecha_inicio} - {fecha_fin}")
        
        resultado = model.obtener_estadisticas_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'estadisticas': {
                'total_ventas': 0,
                'ingresos_totales': 0,
                'promedio_venta': 0,
                'total_unidades': 0
            },
            'ventas_por_pago': [],
            'tendencia_ventas': []
        }), 500


@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>', methods=['GET'])
def obtener_detalle_venta(venta_id):
    """Obtener detalle de una venta específica"""
    try:
        logger.info(f"Obteniendo detalle para venta ID: {venta_id}")
        resultado = model.obtener_detalle_venta(venta_id)
        if resultado['success']:
            return jsonify(resultado)
        else:
            return jsonify(resultado), 404
    except Exception as e:
        logger.error(f"Error en obtener_detalle_venta: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@historial_venta_bp.route('/api/historial-ventas/filtros/clientes', methods=['GET'])
def obtener_clientes_filtro():
    """Obtener lista de clientes para filtros"""
    try:
        logger.info("Obteniendo lista de clientes para filtros")
        resultado = model.obtener_clientes_para_filtro()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_clientes_filtro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'usuarios': []
        }), 500


@historial_venta_bp.route('/api/historial-ventas/filtros/productos', methods=['GET'])
def obtener_productos_filtro():
    """Obtener lista de productos para filtros"""
    try:
        logger.info("Obteniendo lista de productos para filtros")
        resultado = model.obtener_productos_para_filtro()
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_productos_filtro: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'productos': []
        }), 500


@historial_venta_bp.route('/api/historial-ventas/recientes', methods=['GET'])
def obtener_ventas_recientes():
    """Obtener ventas recientes"""
    try:
        limit = request.args.get('limit', default=10, type=int)
        logger.info(f"Obteniendo {limit} ventas recientes")
        resultado = model.obtener_ventas_recientes(limit=limit)
        return jsonify(resultado)
    except Exception as e:
        logger.error(f"Error en obtener_ventas_recientes: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total': 0
        }), 500


# ============================================================
#  CORRECCIÓN: PERÍODO RÁPIDO CON TENDENCIA DE VENTAS
# ============================================================
@historial_venta_bp.route('/api/historial-ventas/periodo/rapido', methods=['GET'])
def obtener_periodo_rapido():
    """Obtener ventas para períodos rápidos (hoy, semana, mes, año) CON TENDENCIA"""
    try:
        periodo = request.args.get('periodo', 'hoy')
        mes = request.args.get('mes')
        anio = request.args.get('anio')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        hoy = datetime.now()
        
        if periodo == 'hoy':
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        elif periodo == 'semana':
            fecha_inicio = (hoy - timedelta(days=hoy.weekday())).date()
            fecha_fin = hoy.date()
        elif periodo == 'mes':
            anio_seleccionado = int(anio) if anio and anio.isdigit() else hoy.year
            mes_seleccionado = int(mes) if mes and mes.isdigit() else hoy.month
            fecha_inicio = date(anio_seleccionado, mes_seleccionado, 1)
            if mes_seleccionado == 12:
                fecha_fin = date(anio_seleccionado + 1, 1, 1) - timedelta(days=1)
            else:
                fecha_fin = date(anio_seleccionado, mes_seleccionado + 1, 1) - timedelta(days=1)
        elif periodo == 'anio':
            anio_seleccionado = int(anio) if anio and anio.isdigit() else hoy.year
            fecha_inicio = date(anio_seleccionado, 1, 1)
            fecha_fin = date(anio_seleccionado, 12, 31)
        else:
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        
        logger.info(f"Período rápido: {periodo} ({fecha_inicio} - {fecha_fin})")
        
        fecha_inicio_str = str(fecha_inicio)
        fecha_fin_str = str(fecha_fin)
        
        # Obtener ventas del período
        resultado_ventas = model.filtrar_ventas(
            fecha_inicio=fecha_inicio_str,
            fecha_fin=fecha_fin_str,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        # Obtener estadísticas financieras
        resultado_financieras = model.obtener_estadisticas_financieras(
            fecha_inicio=fecha_inicio_str,
            fecha_fin=fecha_fin_str,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        # Obtener estadísticas tradicionales (para compatibilidad)
        resultado_estadisticas = model.obtener_estadisticas_periodo(
            fecha_inicio=fecha_inicio_str,
            fecha_fin=fecha_fin_str,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        # ============================================================
        #  CORRECCIÓN: Obtener tendencia de ventas para el gráfico
        # ============================================================
        # Para la tendencia, usar los últimos 7 días desde la fecha_fin
        fecha_tendencia_inicio = (datetime.strptime(fecha_fin_str, '%Y-%m-%d') - timedelta(days=6)).date()
        
        resultado_tendencia = model.obtener_tendencia_ventas(
            fecha_inicio=str(fecha_tendencia_inicio),
            fecha_fin=fecha_fin_str
        )
        
        # Si el modelo no tiene obtener_tendencia_ventas, construir desde estadísticas
        tendencia_ventas = []
        if resultado_tendencia.get('success'):
            tendencia_ventas = resultado_tendencia.get('tendencia', [])
        else:
            # Fallback: usar tendencia de estadísticas
            tendencia_ventas = resultado_estadisticas.get('tendencia_ventas', [])
            logger.warning("Usando tendencia desde estadísticas (fallback)")
        
        # Asegurarse de que los datos sean serializables
        response_data = {
            'success': True,
            'periodo': periodo,
            'fecha_inicio': fecha_inicio_str,
            'fecha_fin': fecha_fin_str,
            'ventas': resultado_ventas.get('ventas', []) if resultado_ventas.get('success') else [],
            'total_ventas': resultado_ventas.get('total', 0) if resultado_ventas.get('success') else 0,
            
            # Estadísticas financieras (nuevo dashboard)
            'estadisticas_financieras': resultado_financieras.get('estadisticas', {}) if resultado_financieras.get('success') else {},
            
            # Estadísticas tradicionales (para compatibilidad con gráficos)
            'estadisticas': resultado_estadisticas.get('estadisticas', {}) if resultado_estadisticas.get('success') else {},
            'ventas_por_pago': resultado_estadisticas.get('ventas_por_pago', []) if resultado_estadisticas.get('success') else [],
            'ingresos_por_pago': resultado_estadisticas.get('ingresos_por_pago', []) if resultado_estadisticas.get('success') else [],
            
            # ============================================================
            #  CORRECCIÓN: Incluir tendencia_ventas en la respuesta
            # ============================================================
            'tendencia_ventas': tendencia_ventas
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error en obtener_periodo_rapido: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'ventas': [],
            'total_ventas': 0,
            'estadisticas_financieras': {},
            'estadisticas': {},
            'ventas_por_pago': [],
            'ingresos_por_pago': [],
            'tendencia_ventas': []
        }), 500


@historial_venta_bp.route('/api/historial-ventas/exportar/excel', methods=['GET'])
def exportar_excel():
    """Exportar historial de ventas a Excel/CSV"""
    try:
        # Obtener parámetros de filtro
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        tipo_pago = request.args.get('tipo_pago')
        tipo_usuario = request.args.get('tipo_usuario')
        cliente_cedula = request.args.get('cliente_cedula')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        logger.info(f"Exportando a Excel con filtros: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")
        
        # Construir kwargs solo con filtros válidos
        kwargs = {}
        if fecha_inicio:
            kwargs['fecha_inicio'] = fecha_inicio
        if fecha_fin:
            kwargs['fecha_fin'] = fecha_fin
        if tipo_pago:
            kwargs['tipo_pago'] = tipo_pago
        if cliente_cedula:
            kwargs['cliente_cedula'] = cliente_cedula
        if hora_inicio:
            kwargs['hora_inicio'] = hora_inicio
        if hora_fin:
            kwargs['hora_fin'] = hora_fin
        
        resultado = model.filtrar_ventas(**kwargs)
        
        if not resultado.get('success') or not resultado.get('ventas'):
            return jsonify({
                'success': False,
                'error': 'No hay datos para exportar'
            }), 404
        
        ventas = resultado['ventas']
        
        from io import StringIO
        from flask import Response
        
        csv_lines = []
        headers = ["ID Venta", "Número", "Fecha", "Hora", "Cliente", "Cédula", "Teléfono", "Tipo Pago", "Total", "Utilidad", "Productos"]
        csv_lines.append(";".join(headers))
        
        for venta in ventas:
            productos_list = venta.get('productos', [])
            productos_str = " | ".join([
                f"{p.get('nombre', '')} ({p.get('cantidad', 0)} x ${float(p.get('precio_unitario', 0)):,.0f})"
                for p in productos_list[:3]
            ])
            if len(productos_list) > 3:
                productos_str += f" ... y {len(productos_list) - 3} más"
            
            linea = [
                str(venta.get('id', '')),
                str(venta.get('numero_venta', '')),
                str(venta.get('fecha_dia', '')),
                str(venta.get('fecha_hora', '')),
                venta.get('nombre_cliente', 'CLIENTE FINAL'),
                venta.get('cliente_cedula', ''),
                venta.get('telefono_cliente', ''),
                venta.get('tipo_pago', ''),
                f"{float(venta.get('total', 0)):,.0f}",
                f"{float(venta.get('utilidad', 0)):,.0f}",
                productos_str
            ]
            csv_lines.append(";".join(linea))
        
        csv_content = "\n".join(csv_lines)
        
        output = StringIO()
        output.write(csv_content)
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=historial_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info(f"Exportación a Excel completada: {len(ventas)} ventas")
        return response
        
    except Exception as e:
        logger.error(f"Error exportando a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@historial_venta_bp.route('/api/historial-ventas/exportar/resumen-excel', methods=['GET'])
def exportar_resumen_excel():
    """Exportar resumen estadístico a Excel"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        logger.info(f"Exportando resumen a Excel: {fecha_inicio} - {fecha_fin}")
        
        resultado = model.obtener_estadisticas_periodo(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        if not resultado.get('success'):
            return jsonify({
                'success': False,
                'error': 'No se pudieron obtener estadísticas'
            }), 500
        
        estadisticas = resultado.get('estadisticas', {})
        ventas_por_pago = resultado.get('ventas_por_pago', [])
        tendencia_ventas = resultado.get('tendencia_ventas', [])
        
        from io import StringIO
        from flask import Response
        
        csv_lines = []
        csv_lines.append("RESUMEN DE VENTAS - AGROVET YACUANQUER")
        if fecha_inicio and fecha_fin:
            csv_lines.append(f"Período: {fecha_inicio} - {fecha_fin}")
        csv_lines.append("")
        
        csv_lines.append("ESTADÍSTICAS GENERALES")
        csv_lines.append("Métrica;Valor")
        csv_lines.append(f"Ventas Totales;{estadisticas.get('total_ventas', 0)}")
        csv_lines.append(f"Ingresos Totales;${float(estadisticas.get('ingresos_totales', 0)):,.0f}")
        csv_lines.append(f"Venta Promedio;${float(estadisticas.get('promedio_venta', 0)):,.0f}")
        csv_lines.append(f"Unidades Vendidas;{estadisticas.get('total_unidades', 0)}")
        csv_lines.append("")
        
        csv_lines.append("VENTAS POR TIPO DE PAGO")
        csv_lines.append("Tipo de Pago;Cantidad;Monto Total")
        
        total_ventas_pago = sum(v.get('cantidad', 0) for v in ventas_por_pago)
        
        for venta_pago in ventas_por_pago:
            cantidad = venta_pago.get('cantidad', 0)
            monto = float(venta_pago.get('monto_total', 0))
            porcentaje = (cantidad / total_ventas_pago * 100) if total_ventas_pago > 0 else 0
            
            csv_lines.append(
                f"{venta_pago.get('tipo_pago', '')};"
                f"{cantidad};"
                f"${monto:,.0f};"
                f"{porcentaje:.1f}%"
            )
        
        csv_lines.append("")
        
        if tendencia_ventas:
            csv_lines.append("TENDENCIA DE VENTAS (ÚLTIMOS 7 DÍAS)")
            csv_lines.append("Fecha;Ventas;Ingresos")
            for tendencia in tendencia_ventas:
                csv_lines.append(
                    f"{tendencia.get('fecha_dia', '')};"
                    f"{tendencia.get('cantidad_ventas', 0)};"
                    f"${float(tendencia.get('total_dia', 0)):,.0f}"
                )
        
        csv_lines.append("")
        csv_lines.append(f"Exportado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        csv_lines.append("Sistema POS - Agrovet Yacuanquer")
        
        csv_content = "\n".join(csv_lines)
        
        output = StringIO()
        output.write(csv_content)
        
        response = Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=resumen_ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        logger.info("Exportación de resumen a Excel completada")
        return response
        
    except Exception as e:
        logger.error(f"Error exportando resumen a Excel: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@historial_venta_bp.route('/api/historial-ventas/test', methods=['GET'])
def test_conexion():
    """Endpoint de prueba para verificar que el historial funciona"""
    try:
        logger.info("Test endpoint de historial de ventas llamado")
        return jsonify({
            'success': True,
            'message': 'Historial de ventas funcionando correctamente',
            'endpoints': {
                'GET /api/historial-ventas': 'Obtener historial completo',
                'GET /api/historial-ventas/filtrar': 'Filtrar historial',
                'GET /api/historial-ventas/estadisticas': 'Obtener estadísticas',
                'GET /api/historial-ventas/{id}': 'Detalle de venta',
                'GET /api/historial-ventas/filtros/clientes': 'Clientes para filtro',
                'GET /api/historial-ventas/filtros/productos': 'Productos para filtro',
                'GET /api/historial-ventas/recientes': 'Ventas recientes',
                'GET /api/historial-ventas/periodo/rapido': 'Períodos rápidos (con tendencia)',
                'GET /api/historial-ventas/estadisticas-financieras': 'Estadísticas financieras'
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error en test_conexion: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@historial_venta_bp.route('/api/historial-ventas/estadisticas-financieras', methods=['GET'])
def obtener_estadisticas_financieras():
    """Obtener estadísticas financieras para el dashboard"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        logger.info(f"Obteniendo estadísticas financieras: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, periodo={periodo}")
        
        if periodo and not fecha_inicio and not fecha_fin:
            resultado = model.obtener_estadisticas_financieras_periodo_rapido(
                periodo,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin
            )
        else:
            resultado = model.obtener_estadisticas_financieras(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin
            )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas_financieras: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>/eliminar', methods=['DELETE'])
def eliminar_venta(venta_id):
    """Eliminar una venta y todos sus registros relacionados"""
    try:
        logger.info(f"Solicitud para eliminar venta ID: {venta_id}")
        
        recuperar_productos = request.args.get('recuperar_productos', 'false').lower() == 'true'
        logger.info(f"Recuperar productos: {recuperar_productos}")
        
        resultado = model.eliminar_venta_completa(venta_id, recuperar_productos=recuperar_productos)
        
        if resultado.get('success'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"Error en eliminar_venta: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        }), 500


@historial_venta_bp.route('/api/historial-ventas/multiple-eliminar', methods=['POST'])
def eliminar_ventas_multiples():
    """Eliminar múltiples ventas en una sola operación"""
    try:
        data = request.get_json()
        
        if not data or 'ventas_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'No se proporcionaron IDs de ventas'
            }), 400
        
        ventas_ids = data['ventas_ids']
        recuperar_productos = data.get('recuperar_productos', False)
        
        if not isinstance(ventas_ids, list) or len(ventas_ids) == 0:
            return jsonify({
                'success': False,
                'error': 'Se requiere una lista de IDs de ventas'
            }), 400
        
        logger.info(f"Solicitud para eliminar {len(ventas_ids)} ventas: {ventas_ids}, recuperar_productos={recuperar_productos}")
        
        resultado = model.eliminar_ventas_multiples(ventas_ids, recuperar_productos=recuperar_productos)
        
        if resultado.get('success'):
            return jsonify(resultado)
        else:
            return jsonify(resultado), 500
            
    except Exception as e:
        logger.error(f"Error en eliminar_ventas_multiples: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        }), 500


@historial_venta_bp.route('/api/historial-ventas/ingresos-por-categoria', methods=['GET'])
def obtener_ingresos_por_categoria():
    """Obtener ingresos por categoría de pago"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        periodo = request.args.get('periodo')
        hora_inicio = request.args.get('hora_inicio') or request.args.get('hora_inicial')
        hora_fin = request.args.get('hora_fin') or request.args.get('hora_final')
        
        if hora_inicio and len(hora_inicio) == 5:
            hora_inicio = hora_inicio + ':00'
        if hora_fin and len(hora_fin) == 5:
            hora_fin = hora_fin + ':00'
        
        resultado = model.obtener_ingresos_por_categoria_pago(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            periodo=periodo,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_ingresos_por_categoria: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ingresos': []
        }), 500


@historial_venta_bp.route('/api/historial-ventas/<int:venta_id>/verificar', methods=['GET'])
def verificar_venta(venta_id):
    """Verificar información de una venta antes de eliminarla"""
    try:
        logger.info(f"Verificando venta ID: {venta_id}")
        resultado = model.verificar_venta_para_eliminar(venta_id)
        if resultado.get('success'):
            return jsonify(resultado)
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Error en verificación'),
                'puede_eliminar': False
            }), 400
    except Exception as e:
        logger.error(f"Error en verificar_venta: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'puede_eliminar': False
        }), 500


# ============================================================
#  NUEVO ENDPOINT: OBTENER TENDENCIA DE VENTAS
# ============================================================
@historial_venta_bp.route('/api/historial-ventas/tendencia', methods=['GET'])
def obtener_tendencia():
    """Obtener tendencia de ventas para el gráfico"""
    try:
        fecha_inicio = request.args.get('fecha_inicio')
        fecha_fin = request.args.get('fecha_fin')
        dias = request.args.get('dias', default=7, type=int)
        
        logger.info(f"Obteniendo tendencia de ventas: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, dias={dias}")
        
        resultado = model.obtener_tendencia_ventas(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            dias=dias
        )
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_tendencia: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'tendencia': []
        }), 500