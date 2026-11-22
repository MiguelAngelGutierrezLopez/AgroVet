# modelo/reporte_caja_model.py
from datetime import datetime, timedelta
from database import Database
import logging
import math

logger = logging.getLogger(__name__)

class ReporteCajaModel:
    """Modelo para manejar todas las operaciones relacionadas con el reporte de caja"""
    
    # Constantes para métodos de pago
    METODOS_BANCO = ['NEQUI', 'TRANSACCIÓN', 'TRANSFERENCIA', 'TARJETA', 'BANCO', 'Banco']
    TIPOS_CONTADO = ['CONTADO', 'Contado', 'contado']
    TIPOS_CREDITO = ['CRÉDITO', 'Credito', 'credito']
    
    @staticmethod
    def obtener_periodo_fechas(periodo, fecha_inicio_str=None, fecha_fin_str=None):
        hoy = datetime.now()
        
        if periodo == 'hoy':
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        elif periodo == 'semana':
            start = hoy - timedelta(days=hoy.weekday())
            fecha_inicio = start.date()
            fecha_fin = (start + timedelta(days=6)).date()
        elif periodo == 'mes':
            fecha_inicio = hoy.replace(day=1).date()
            next_month = hoy.replace(day=28) + timedelta(days=4)
            fecha_fin = (next_month - timedelta(days=next_month.day)).date()
        elif periodo == 'anio':
            fecha_inicio = hoy.replace(month=1, day=1).date()
            fecha_fin = hoy.replace(month=12, day=31).date()
        elif periodo == 'personalizado' and fecha_inicio_str and fecha_fin_str:
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
        else:
            fecha_inicio = hoy.date()
            fecha_fin = hoy.date()
        
        return fecha_inicio, fecha_fin
    
    @staticmethod
    def calcular_total_caja(ingresos_manuales, egresos_manuales, ventas_contado, anticipos, abonos):
        return ingresos_manuales + ventas_contado + anticipos + abonos - egresos_manuales
    
    @staticmethod
    def obtener_movimientos(filtros):
        try:
            db = Database()
            page = filtros.get('page', 1)
            per_page = filtros.get('per_page', 10)
            offset = (page - 1) * per_page
            tipo = filtros.get('tipo')
            fecha_inicio = filtros.get('fecha_inicio')
            fecha_fin = filtros.get('fecha_fin')
            
            where_clauses = []
            params = []
            
            if tipo == 'ingreso':
                where_clauses.append("ingresos > 0")
            elif tipo == 'egreso':
                where_clauses.append("egresos > 0")
            
            if fecha_inicio and fecha_fin:
                where_clauses.append("DATE(COALESCE(fecha_ingreso, fecha_egreso)) BETWEEN %s AND %s")
                params.extend([fecha_inicio, fecha_fin])
            
            count_query = "SELECT COUNT(*) as total FROM reporte_caja"
            if where_clauses:
                count_query += " WHERE " + " AND ".join(where_clauses)
            count_result = db.fetch_one(count_query, tuple(params))
            total = count_result['total'] if count_result else 0
            
            data_query = """
                SELECT 
                    id,
                    ingresos,
                    razon_ingreso,
                    fecha_ingreso,
                    categoria,
                    egresos,
                    razon_egreso,
                    fecha_egreso,
                    CASE 
                        WHEN ingresos > 0 THEN 'ingreso'
                        WHEN egresos > 0 THEN 'egreso'
                        ELSE 'otro'
                    END as tipo,
                    CASE 
                        WHEN ingresos > 0 THEN ingresos
                        WHEN egresos > 0 THEN -egresos
                        ELSE 0
                    END as monto_signed
                FROM reporte_caja
            """
            if where_clauses:
                data_query += " WHERE " + " AND ".join(where_clauses)
            data_query += " ORDER BY COALESCE(fecha_ingreso, fecha_egreso) DESC, id DESC"
            data_query += " LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
            
            movimientos = db.fetch_all(data_query, tuple(params))
            
            for movimiento in movimientos:
                for field in ['fecha_ingreso', 'fecha_egreso']:
                    if movimiento[field]:
                        movimiento[field] = movimiento[field].strftime('%Y-%m-%d %H:%M:%S')
            
            return {
                'success': True,
                'movimientos': movimientos,
                'paginacion': {
                    'pagina': page,
                    'por_pagina': per_page,
                    'total': total,
                    'total_paginas': (total + per_page - 1) // per_page
                }
            }
        except Exception as e:
            logger.error(f"Error en obtener_movimientos: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def obtener_resumen_financiero(periodo, fecha_inicio=None, fecha_fin=None):
        try:
            db = Database()
            
            if periodo == 'personalizado' and fecha_inicio and fecha_fin:
                fecha_inicio_date = fecha_inicio
                fecha_fin_date = fecha_fin
            else:
                fecha_inicio_date, fecha_fin_date = ReporteCajaModel.obtener_periodo_fechas(periodo)
                fecha_inicio_date = fecha_inicio_date.isoformat()
                fecha_fin_date = fecha_fin_date.isoformat()
            
            # 1. Ingresos manuales
            ingresos_query = """
                SELECT COUNT(*) as cantidad, COALESCE(SUM(ingresos), 0) as total
                FROM reporte_caja 
                WHERE ingresos > 0 AND DATE(fecha_ingreso) BETWEEN %s AND %s
            """
            ingresos_res = db.fetch_one(ingresos_query, (fecha_inicio_date, fecha_fin_date))
            total_ingresos_manuales = float(ingresos_res['total']) if ingresos_res else 0.0
            cantidad_ingresos = ingresos_res['cantidad'] if ingresos_res else 0
            
            # 2. Egresos manuales
            egresos_query = """
                SELECT COUNT(*) as cantidad, COALESCE(SUM(egresos), 0) as total
                FROM reporte_caja 
                WHERE egresos > 0 AND DATE(fecha_egreso) BETWEEN %s AND %s
            """
            egresos_res = db.fetch_one(egresos_query, (fecha_inicio_date, fecha_fin_date))
            total_egresos_manuales = float(egresos_res['total']) if egresos_res else 0.0
            cantidad_egresos = egresos_res['cantidad'] if egresos_res else 0
            
            # 3. Ventas CONTADO (normales)
            tipos_contado_str = "', '".join(ReporteCajaModel.TIPOS_CONTADO)
            ventas_contado_query = """
                SELECT COUNT(DISTINCT v.id) as cantidad, COALESCE(SUM(v.total), 0) as total
                FROM ventas v
                WHERE v.tipo_pago IN ('""" + tipos_contado_str + """') 
                AND v.fecha_dia BETWEEN %s AND %s
                AND v.id NOT IN (SELECT DISTINCT id_venta FROM ventas_mixtas)
            """
            vc_res = db.fetch_one(ventas_contado_query, (fecha_inicio_date, fecha_fin_date))
            ventas_contado_normal = float(vc_res['total']) if vc_res else 0.0
            cantidad_contado_normal = vc_res['cantidad'] if vc_res else 0
            
            # 4. Ventas MIXTAS - parte de contado
            ventas_mixtas_contado_query = """
                SELECT COUNT(DISTINCT v.id) as cantidad_ventas, COALESCE(SUM(vm.monto), 0) as total_contado
                FROM ventas v
                INNER JOIN ventas_mixtas vm ON v.id = vm.id_venta
                WHERE vm.categoria = 'contado' AND v.fecha_dia BETWEEN %s AND %s
            """
            vm_res = db.fetch_one(ventas_mixtas_contado_query, (fecha_inicio_date, fecha_fin_date))
            ventas_mixtas_contado = float(vm_res['total_contado']) if vm_res else 0.0
            cantidad_mixtas_contado = vm_res['cantidad_ventas'] if vm_res else 0
            
            total_ventas_contado = ventas_contado_normal + ventas_mixtas_contado
            total_cantidad_contado = cantidad_contado_normal + cantidad_mixtas_contado
            
            # 5. Anticipos de créditos (normales)
            anticipos_query = """
                SELECT COUNT(DISTINCT c.id) as cantidad, COALESCE(SUM(c.anticipo), 0) as total_anticipo
                FROM creditos c
                INNER JOIN ventas v ON c.venta_id = v.id
                WHERE c.anticipo > 0 AND v.fecha_dia BETWEEN %s AND %s
            """
            ant_res = db.fetch_one(anticipos_query, (fecha_inicio_date, fecha_fin_date))
            total_anticipos = float(ant_res['total_anticipo']) if ant_res else 0.0
            cantidad_anticipos = ant_res['cantidad'] if ant_res else 0
            
            # 6. Anticipos de créditos (mixtos)
            anticipos_mixtas_query = """
                SELECT COUNT(DISTINCT v.id) as cantidad, COALESCE(SUM(vm.anticipo), 0) as total_anticipo
                FROM ventas v
                INNER JOIN ventas_mixtas vm ON v.id = vm.id_venta
                WHERE vm.categoria = 'credito' AND vm.anticipo > 0
                AND v.fecha_dia BETWEEN %s AND %s
            """
            ant_mix_res = db.fetch_one(anticipos_mixtas_query, (fecha_inicio_date, fecha_fin_date))
            if ant_mix_res:
                total_anticipos += float(ant_mix_res['total_anticipo'] or 0)
                cantidad_anticipos += ant_mix_res['cantidad'] or 0
            
            # 7. Abonos a créditos (solo efectivo)
            abonos_query = """
                SELECT COUNT(*) as cantidad, COALESCE(SUM(monto), 0) as total_abonos
                FROM abonos
                WHERE metodo_pago IN ('efectivo', 'EFECTIVO', 'Efectivo')
                AND DATE(fecha) BETWEEN %s AND %s
            """
            ab_res = db.fetch_one(abonos_query, (fecha_inicio_date, fecha_fin_date))
            total_abonos = float(ab_res['total_abonos']) if ab_res else 0.0
            cantidad_abonos = ab_res['cantidad'] if ab_res else 0
            
            # Calcular total caja
            total_caja = ReporteCajaModel.calcular_total_caja(
                total_ingresos_manuales, total_egresos_manuales,
                total_ventas_contado, total_anticipos, total_abonos
            )
            
            return {
                'success': True,
                'resumen': {
                    'total_ingresos_manuales': total_ingresos_manuales,
                    'total_egresos_manuales': total_egresos_manuales,
                    'cantidad_ingresos': cantidad_ingresos,
                    'cantidad_egresos': cantidad_egresos,
                    'saldo_manual': total_ingresos_manuales - total_egresos_manuales,
                    'ventas_contado_total': total_ventas_contado,
                    'cantidad_ventas_contado': total_cantidad_contado,
                    'ventas_contado_directo': ventas_contado_normal,
                    'ventas_mixtas_contado': ventas_mixtas_contado,
                    'ventas_credito_anticipo_total': total_anticipos,
                    'cantidad_ventas_credito_anticipo': cantidad_anticipos,
                    'abonos_credito_total': total_abonos,
                    'cantidad_abonos_credito': cantidad_abonos,
                    'total_caja': total_caja,
                    'periodo': periodo,
                    'fecha_inicio': fecha_inicio_date,
                    'fecha_fin': fecha_fin_date
                }
            }
        except Exception as e:
            logger.error(f"Error en obtener_resumen_financiero: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def obtener_estadisticas_graficos(periodo, fecha_inicio=None, fecha_fin=None):
        try:
            db = Database()
            if periodo == 'personalizado' and fecha_inicio and fecha_fin:
                fecha_inicio_date = fecha_inicio
                fecha_fin_date = fecha_fin
            else:
                fecha_inicio_date, fecha_fin_date = ReporteCajaModel.obtener_periodo_fechas(periodo)
                fecha_inicio_date = fecha_inicio_date.isoformat()
                fecha_fin_date = fecha_fin_date.isoformat()
            
            flujo_caja_query = """
                SELECT 
                    DATE(COALESCE(fecha_ingreso, fecha_egreso)) as fecha,
                    COALESCE(SUM(ingresos), 0) as ingresos,
                    COALESCE(SUM(egresos), 0) as egresos
                FROM reporte_caja 
                WHERE DATE(COALESCE(fecha_ingreso, fecha_egreso)) BETWEEN %s AND %s
                GROUP BY DATE(COALESCE(fecha_ingreso, fecha_egreso))
                ORDER BY fecha
            """
            flujo_rows = db.fetch_all(flujo_caja_query, (fecha_inicio_date, fecha_fin_date))
            flujo_caja = []
            for row in flujo_rows:
                flujo_caja.append({
                    'fecha': row['fecha'].strftime('%Y-%m-%d') if row['fecha'] else '',
                    'ingresos': float(row['ingresos']),
                    'egresos': float(row['egresos'])
                })
            
            distribucion_egresos_query = """
                SELECT 
                    categoria,
                    COALESCE(SUM(egresos), 0) as total
                FROM reporte_caja 
                WHERE egresos > 0 AND DATE(fecha_egreso) BETWEEN %s AND %s
                GROUP BY categoria
                ORDER BY total DESC
            """
            dist_rows = db.fetch_all(distribucion_egresos_query, (fecha_inicio_date, fecha_fin_date))
            distribucion_egresos = [{'categoria': r['categoria'] or 'otros', 'total': float(r['total'])} for r in dist_rows]
            
            return {
                'success': True,
                'flujo_caja': flujo_caja,
                'distribucion_egresos': distribucion_egresos
            }
        except Exception as e:
            logger.error(f"Error en obtener_estadisticas_graficos: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def crear_movimiento(data):
        try:
            db = Database()
            tipo = data['tipo']
            monto = float(data['monto'])
            razon = data['razon']
            categoria = data.get('categoria', 'otros')
            
            # Usar datetime local del servidor
            ahora = datetime.now()
            fecha_str = ahora.strftime('%Y-%m-%d %H:%M:%S')
            
            # Verificar duplicado en últimos 30 segundos
            tiempo_limite = 30
            if tipo == 'ingreso':
                check_query = """
                    SELECT id FROM reporte_caja 
                    WHERE razon_ingreso = %s AND ingresos = %s
                    AND ABS(TIMESTAMPDIFF(SECOND, fecha_ingreso, %s)) < %s
                """
                dup = db.fetch_one(check_query, (razon, monto, fecha_str, tiempo_limite))
            else:
                check_query = """
                    SELECT id FROM reporte_caja 
                    WHERE razon_egreso = %s AND egresos = %s
                    AND ABS(TIMESTAMPDIFF(SECOND, fecha_egreso, %s)) < %s
                """
                dup = db.fetch_one(check_query, (razon, monto, fecha_str, tiempo_limite))
            
            if dup:
                return {'success': False, 'message': 'Ya existe un movimiento similar en los últimos segundos'}
            
            db.execute("START TRANSACTION")
            if tipo == 'ingreso':
                query = "INSERT INTO reporte_caja (ingresos, razon_ingreso, fecha_ingreso, categoria) VALUES (%s, %s, %s, %s)"
                params = (monto, razon, fecha_str, categoria)
            else:
                query = "INSERT INTO reporte_caja (egresos, razon_egreso, fecha_egreso, categoria) VALUES (%s, %s, %s, %s)"
                params = (monto, razon, fecha_str, categoria)
            
            db.execute(query, params)
            movimiento_id = db.fetch_one("SELECT LAST_INSERT_ID() as id")['id']
            db.execute("COMMIT")
            return {'success': True, 'message': 'Movimiento creado', 'movimiento_id': movimiento_id}
        except Exception as e:
            db.execute("ROLLBACK")
            logger.error(f"Error en crear_movimiento: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def obtener_movimiento_por_id(movimiento_id):
        try:
            db = Database()
            query = "SELECT id, ingresos, razon_ingreso, fecha_ingreso, categoria, egresos, razon_egreso, fecha_egreso FROM reporte_caja WHERE id = %s"
            mov = db.fetch_one(query, (movimiento_id,))
            if not mov:
                return {'success': False, 'message': 'Movimiento no encontrado'}
            if mov['ingresos'] and mov['ingresos'] > 0:
                return {
                    'success': True,
                    'movimiento': {
                        'id': mov['id'],
                        'tipo': 'ingreso',
                        'monto': float(mov['ingresos']),
                        'razon': mov['razon_ingreso'],
                        'fecha': mov['fecha_ingreso'].strftime('%Y-%m-%d %H:%M:%S') if mov['fecha_ingreso'] else None,
                        'categoria': mov['categoria']
                    }
                }
            else:
                return {
                    'success': True,
                    'movimiento': {
                        'id': mov['id'],
                        'tipo': 'egreso',
                        'monto': float(mov['egresos']),
                        'razon': mov['razon_egreso'],
                        'fecha': mov['fecha_egreso'].strftime('%Y-%m-%d %H:%M:%S') if mov['fecha_egreso'] else None,
                        'categoria': mov['categoria']
                    }
                }
        except Exception as e:
            logger.error(f"Error en obtener_movimiento_por_id: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def actualizar_movimiento(movimiento_id, data):
        try:
            db = Database()
            exists = db.fetch_one("SELECT id FROM reporte_caja WHERE id = %s", (movimiento_id,))
            if not exists:
                return {'success': False, 'message': 'Movimiento no encontrado'}
            
            tipo = data['tipo']
            monto = float(data['monto'])
            razon = data['razon']
            categoria = data.get('categoria', 'otros')
            
            # Usar datetime local
            ahora = datetime.now()
            fecha_str = ahora.strftime('%Y-%m-%d %H:%M:%S')
            
            tiempo_limite = 30
            if tipo == 'ingreso':
                check_query = """
                    SELECT id FROM reporte_caja 
                    WHERE razon_ingreso = %s AND ingresos = %s
                    AND ABS(TIMESTAMPDIFF(SECOND, fecha_ingreso, %s)) < %s AND id != %s
                """
                dup = db.fetch_one(check_query, (razon, monto, fecha_str, tiempo_limite, movimiento_id))
            else:
                check_query = """
                    SELECT id FROM reporte_caja 
                    WHERE razon_egreso = %s AND egresos = %s
                    AND ABS(TIMESTAMPDIFF(SECOND, fecha_egreso, %s)) < %s AND id != %s
                """
                dup = db.fetch_one(check_query, (razon, monto, fecha_str, tiempo_limite, movimiento_id))
            
            if dup:
                return {'success': False, 'message': 'Ya existe otro movimiento similar en los últimos segundos'}
            
            db.execute("START TRANSACTION")
            if tipo == 'ingreso':
                query = """
                    UPDATE reporte_caja 
                    SET ingresos = %s, razon_ingreso = %s, fecha_ingreso = %s, categoria = %s,
                        egresos = 0, razon_egreso = NULL, fecha_egreso = NULL
                    WHERE id = %s
                """
                params = (monto, razon, fecha_str, categoria, movimiento_id)
            else:
                query = """
                    UPDATE reporte_caja 
                    SET egresos = %s, razon_egreso = %s, fecha_egreso = %s, categoria = %s,
                        ingresos = 0, razon_ingreso = NULL, fecha_ingreso = NULL
                    WHERE id = %s
                """
                params = (monto, razon, fecha_str, categoria, movimiento_id)
            
            db.execute(query, params)
            db.execute("COMMIT")
            return {'success': True, 'message': 'Movimiento actualizado'}
        except Exception as e:
            db.execute("ROLLBACK")
            logger.error(f"Error en actualizar_movimiento: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def eliminar_movimiento(movimiento_id):
        try:
            db = Database()
            exists = db.fetch_one("SELECT id FROM reporte_caja WHERE id = %s", (movimiento_id,))
            if not exists:
                return {'success': False, 'message': 'Movimiento no encontrado'}
            db.execute("DELETE FROM reporte_caja WHERE id = %s", (movimiento_id,))
            return {'success': True, 'message': 'Movimiento eliminado'}
        except Exception as e:
            logger.error(f"Error en eliminar_movimiento: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def obtener_abonos_detalle(periodo, fecha_inicio=None, fecha_fin=None):
        try:
            db = Database()
            if periodo == 'personalizado' and fecha_inicio and fecha_fin:
                fecha_inicio_date = fecha_inicio
                fecha_fin_date = fecha_fin
            else:
                fecha_inicio_date, fecha_fin_date = ReporteCajaModel.obtener_periodo_fechas(periodo)
                fecha_inicio_date = fecha_inicio_date.isoformat()
                fecha_fin_date = fecha_fin_date.isoformat()
            
            query = """
                SELECT 
                    a.id as abono_id,
                    a.credito_id,
                    a.venta_id,
                    a.monto,
                    a.fecha as fecha_abono,
                    a.metodo_pago,
                    a.referencia,
                    a.observacion,
                    a.usuario_registra,
                    c.cliente_cedula,
                    c.deuda_inicial,
                    c.anticipo,
                    c.saldo_pendiente,
                    cli.nombre as cliente_nombre,
                    cli.telefono as cliente_telefono,
                    v.numero_venta,
                    v.fecha_dia as fecha_venta,
                    v.total as total_venta
                FROM abonos a
                INNER JOIN creditos c ON a.credito_id = c.id
                INNER JOIN cliente cli ON a.cliente_cedula = cli.cedula
                INNER JOIN ventas v ON a.venta_id = v.id
                WHERE DATE(a.fecha) BETWEEN %s AND %s
                ORDER BY a.fecha DESC
            """
            abonos = db.fetch_all(query, (fecha_inicio_date, fecha_fin_date))
            resultado = []
            for ab in abonos:
                resultado.append({
                    'abono_id': ab['abono_id'],
                    'credito_id': ab['credito_id'],
                    'venta_id': ab['venta_id'],
                    'numero_venta': ab['numero_venta'],
                    'cliente': {
                        'cedula': ab['cliente_cedula'],
                        'nombre': ab['cliente_nombre'],
                        'telefono': ab['cliente_telefono']
                    },
                    'monto_abono': float(ab['monto']),
                    'fecha_abono': ab['fecha_abono'].strftime('%Y-%m-%d %H:%M:%S') if ab['fecha_abono'] else '',
                    'metodo_pago': ab['metodo_pago'],
                    'referencia': ab['referencia'],
                    'observacion': ab['observacion'],
                    'usuario_registra': ab['usuario_registra'],
                    'saldo_pendiente': float(ab['saldo_pendiente']),
                    'deuda_inicial': float(ab['deuda_inicial']),
                    'anticipo': float(ab['anticipo']),
                    'total_venta': float(ab['total_venta']),
                    'fecha_venta': ab['fecha_venta'].strftime('%Y-%m-%d') if ab['fecha_venta'] else '',
                    'productos': []
                })
            
            resumen_query = """
                SELECT COUNT(*) as cantidad_abonos, COALESCE(SUM(monto), 0) as total_abonos,
                       COUNT(DISTINCT cliente_cedula) as personas_distintas
                FROM abonos 
                WHERE DATE(fecha) BETWEEN %s AND %s
                AND metodo_pago IN ('efectivo', 'EFECTIVO', 'Efectivo')
            """
            resumen = db.fetch_one(resumen_query, (fecha_inicio_date, fecha_fin_date))
            return {
                'success': True,
                'detalle': resultado,
                'resumen': {
                    'total_abonos': float(resumen['total_abonos']) if resumen else 0.0,
                    'cantidad_abonos': resumen['cantidad_abonos'] if resumen else 0,
                    'personas_distintas': resumen['personas_distintas'] if resumen else 0,
                    'periodo': periodo,
                    'fecha_inicio': fecha_inicio_date,
                    'fecha_fin': fecha_fin_date
                }
            }
        except Exception as e:
            logger.error(f"Error en obtener_abonos_detalle: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def obtener_dinero_banco(periodo, fecha_inicio=None, fecha_fin=None):
        try:
            db = Database()
            if periodo == 'personalizado' and fecha_inicio and fecha_fin:
                fecha_inicio_date = fecha_inicio
                fecha_fin_date = fecha_fin
            else:
                fecha_inicio_date, fecha_fin_date = ReporteCajaModel.obtener_periodo_fechas(periodo)
                fecha_inicio_date = fecha_inicio_date.isoformat()
                fecha_fin_date = fecha_fin_date.isoformat()
            
            metodos_banco_str = "', '".join(ReporteCajaModel.METODOS_BANCO)
            
            ventas_banco = db.fetch_one(
                "SELECT COUNT(*) as cantidad, COALESCE(SUM(total), 0) as total FROM ventas WHERE tipo_pago IN ('" + metodos_banco_str + "') AND fecha_dia BETWEEN %s AND %s",
                (fecha_inicio_date, fecha_fin_date)
            )
            ventas_normales = {
                'cantidad': ventas_banco['cantidad'] if ventas_banco else 0,
                'total': float(ventas_banco['total']) if ventas_banco else 0.0
            }
            
            ventas_mixtas = db.fetch_one(
                """SELECT COUNT(DISTINCT vm.id_venta) as cantidad_ventas, COUNT(vm.id) as cantidad_transacciones,
                          COALESCE(SUM(vm.monto), 0) as total
                   FROM ventas_mixtas vm
                   INNER JOIN ventas v ON vm.id_venta = v.id
                   WHERE vm.metodo_pago IN ('""" + metodos_banco_str + """') 
                   AND v.fecha_dia BETWEEN %s AND %s""",
                (fecha_inicio_date, fecha_fin_date)
            )
            ventas_mixtas_banco = {
                'cantidad_ventas': ventas_mixtas['cantidad_ventas'] if ventas_mixtas else 0,
                'cantidad_transacciones': ventas_mixtas['cantidad_transacciones'] if ventas_mixtas else 0,
                'total': float(ventas_mixtas['total']) if ventas_mixtas else 0.0
            }
            
            abonos_banco = db.fetch_one(
                """SELECT COUNT(*) as cantidad, COALESCE(SUM(monto), 0) as total
                   FROM abonos
                   WHERE metodo_pago IN ('banco', 'transferencia', 'BANCO', 'Transferencia')
                   AND DATE(fecha) BETWEEN %s AND %s""",
                (fecha_inicio_date, fecha_fin_date)
            )
            abonos_banco_total = float(abonos_banco['total']) if abonos_banco else 0.0
            cantidad_abonos_banco = abonos_banco['cantidad'] if abonos_banco else 0
            
            total_general = ventas_normales['total'] + ventas_mixtas_banco['total'] + abonos_banco_total
            
            detalle_query = """
                SELECT 'Venta Normal' as tipo, v.id as venta_id, v.numero_venta, v.fecha_dia, v.total as monto, v.tipo_pago, v.nombre_cliente
                FROM ventas v
                WHERE v.tipo_pago IN ('""" + metodos_banco_str + """') AND v.fecha_dia BETWEEN %s AND %s
                UNION ALL
                SELECT 'Venta Mixta' as tipo, v.id, v.numero_venta, v.fecha_dia, vm.monto, CONCAT('Mixto - ', vm.metodo_pago), v.nombre_cliente
                FROM ventas_mixtas vm
                INNER JOIN ventas v ON vm.id_venta = v.id
                WHERE vm.metodo_pago IN ('""" + metodos_banco_str + """') AND v.fecha_dia BETWEEN %s AND %s
                UNION ALL
                SELECT 'Abono Banco' as tipo, NULL, NULL, a.fecha, a.monto, CONCAT('Abono - ', a.metodo_pago), cli.nombre
                FROM abonos a
                INNER JOIN cliente cli ON a.cliente_cedula = cli.cedula
                WHERE a.metodo_pago IN ('banco', 'transferencia', 'BANCO', 'Transferencia')
                AND DATE(a.fecha) BETWEEN %s AND %s
                ORDER BY fecha_dia DESC
                LIMIT 20
            """
            detalle = db.fetch_all(detalle_query, (fecha_inicio_date, fecha_fin_date, fecha_inicio_date, fecha_fin_date, fecha_inicio_date, fecha_fin_date))
            transacciones = [{
                'tipo': row['tipo'],
                'venta_id': row['venta_id'],
                'numero_venta': row['numero_venta'],
                'fecha': row['fecha_dia'].strftime('%Y-%m-%d') if row['fecha_dia'] else '',
                'monto': float(row['monto']),
                'tipo_pago': row['tipo_pago'],
                'cliente': row['nombre_cliente']
            } for row in detalle]
            
            return {
                'success': True,
                'dinero_banco': {
                    'total_general': total_general,
                    'ventas_normales': ventas_normales,
                    'ventas_mixtas': ventas_mixtas_banco,
                    'abonos_banco': {'total': abonos_banco_total, 'cantidad': cantidad_abonos_banco},
                    'cantidad_ventas': ventas_normales['cantidad'] + ventas_mixtas_banco['cantidad_ventas'],
                    'transacciones_recientes': transacciones
                },
                'periodo': {'nombre': periodo, 'fecha_inicio': fecha_inicio_date, 'fecha_fin': fecha_fin_date}
            }
        except Exception as e:
            logger.error(f"Error en obtener_dinero_banco: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def _monto_no_negativo(valor, nombre):
        try:
            monto = float(valor or 0)
        except (TypeError, ValueError):
            raise ValueError(f'{nombre} debe ser un número válido.')
        if not math.isfinite(monto) or monto < 0:
            raise ValueError(f'{nombre} debe ser un número igual o mayor a cero.')
        return monto

    @staticmethod
    def _obtener_movimientos_para_cierre(fecha_inicio, fecha_fin):
        resumen_result = ReporteCajaModel.obtener_resumen_financiero(
            'personalizado', fecha_inicio, fecha_fin
        )
        if not resumen_result['success']:
            raise RuntimeError(resumen_result.get('message', 'No se pudo calcular el efectivo.'))

        banco_result = ReporteCajaModel.obtener_dinero_banco(
            'personalizado', fecha_inicio, fecha_fin
        )
        if not banco_result['success']:
            raise RuntimeError(banco_result.get('message', 'No se pudo calcular el banco.'))

        resumen = resumen_result['resumen']
        return {
            'ingresos_manuales_efectivo': float(resumen['total_ingresos_manuales'] or 0),
            'ventas_contado_efectivo': float(resumen['ventas_contado_total'] or 0),
            'anticipos_efectivo': float(resumen['ventas_credito_anticipo_total'] or 0),
            'abonos_efectivo': float(resumen['abonos_credito_total'] or 0),
            'egresos_manuales_efectivo': float(resumen['total_egresos_manuales'] or 0),
            'ingresos_banco_registrados': float(
                banco_result['dinero_banco']['total_general'] or 0
            ),
        }

    @staticmethod
    def _formatear_cierre(cierre, apertura_manual=False, cierre_aplicado=True):
        campos_monto = (
            'saldo_inicial_efectivo',
            'saldo_inicial_banco',
            'ingresos_manuales_efectivo',
            'ventas_contado_efectivo',
            'anticipos_efectivo',
            'abonos_efectivo',
            'egresos_manuales_efectivo',
            'ingresos_banco_registrados',
            'ajuste_banco_externo',
            'saldo_final_efectivo',
            'saldo_final_banco',
            'total_final',
        )
        resultado = dict(cierre)
        for campo in ('fecha_cierre', 'fecha_inicio_movimientos'):
            if hasattr(resultado.get(campo), 'isoformat'):
                resultado[campo] = resultado[campo].isoformat()
        for campo in campos_monto:
            resultado[campo] = float(resultado.get(campo) or 0)

        resultado['ingresos_efectivo_total'] = sum(
            resultado[campo]
            for campo in (
                'ingresos_manuales_efectivo',
                'ventas_contado_efectivo',
                'anticipos_efectivo',
                'abonos_efectivo',
            )
        )
        resultado['apertura_manual'] = apertura_manual
        resultado['cierre_aplicado'] = cierre_aplicado
        return resultado

    @staticmethod
    def obtener_cierre_actual():
        try:
            db = Database()
            hoy = datetime.now().date()
            hoy_str = hoy.isoformat()

            cierre_existente = db.fetch_one(
                "SELECT * FROM cierre_caja WHERE fecha_cierre = %s",
                (hoy_str,),
            )
            if cierre_existente:
                return {
                    'success': True,
                    'cierre': ReporteCajaModel._formatear_cierre(cierre_existente),
                }

            cierre_anterior = db.fetch_one(
                """
                SELECT fecha_cierre, saldo_final_efectivo, saldo_final_banco
                FROM cierre_caja
                WHERE fecha_cierre < %s
                ORDER BY fecha_cierre DESC
                LIMIT 1
                """,
                (hoy_str,),
            )
            if cierre_anterior:
                fecha_inicio = (
                    cierre_anterior['fecha_cierre'] + timedelta(days=1)
                ).isoformat()
                saldo_inicial_efectivo = float(cierre_anterior['saldo_final_efectivo'] or 0)
                saldo_inicial_banco = float(cierre_anterior['saldo_final_banco'] or 0)
                apertura_manual = False
            else:
                fecha_inicio = hoy_str
                saldo_inicial_efectivo = 0.0
                saldo_inicial_banco = 0.0
                apertura_manual = True

            movimientos = ReporteCajaModel._obtener_movimientos_para_cierre(
                fecha_inicio, hoy_str
            )
            saldo_final_efectivo = (
                saldo_inicial_efectivo
                + movimientos['ingresos_manuales_efectivo']
                + movimientos['ventas_contado_efectivo']
                + movimientos['anticipos_efectivo']
                + movimientos['abonos_efectivo']
                - movimientos['egresos_manuales_efectivo']
            )
            saldo_final_banco = (
                saldo_inicial_banco + movimientos['ingresos_banco_registrados']
            )
            cierre = {
                'fecha_cierre': hoy_str,
                'fecha_inicio_movimientos': fecha_inicio,
                'saldo_inicial_efectivo': saldo_inicial_efectivo,
                'saldo_inicial_banco': saldo_inicial_banco,
                **movimientos,
                'ajuste_banco_externo': 0.0,
                'saldo_final_efectivo': saldo_final_efectivo,
                'saldo_final_banco': saldo_final_banco,
                'total_final': saldo_final_efectivo + saldo_final_banco,
            }
            return {
                'success': True,
                'cierre': ReporteCajaModel._formatear_cierre(
                    cierre, apertura_manual=apertura_manual, cierre_aplicado=False
                ),
            }
        except Exception as e:
            logger.error(f"Error obteniendo datos del cierre: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def aplicar_cierre(datos):
        try:
            db = Database()
            hoy_str = datetime.now().date().isoformat()
            cierre_existente = db.fetch_one(
                "SELECT * FROM cierre_caja WHERE fecha_cierre = %s",
                (hoy_str,),
            )
            cierre_anterior = db.fetch_one(
                """
                SELECT fecha_cierre, saldo_final_efectivo, saldo_final_banco
                FROM cierre_caja
                WHERE fecha_cierre < %s
                ORDER BY fecha_cierre DESC
                LIMIT 1
                """,
                (hoy_str,),
            )

            if cierre_existente:
                fecha_inicio = cierre_existente['fecha_inicio_movimientos'].isoformat()
                saldo_inicial_efectivo = float(cierre_existente['saldo_inicial_efectivo'] or 0)
                saldo_inicial_banco = float(cierre_existente['saldo_inicial_banco'] or 0)
                ajuste_default = float(cierre_existente['ajuste_banco_externo'] or 0)
            elif cierre_anterior:
                fecha_inicio = (
                    cierre_anterior['fecha_cierre'] + timedelta(days=1)
                ).isoformat()
                saldo_inicial_efectivo = float(cierre_anterior['saldo_final_efectivo'] or 0)
                saldo_inicial_banco = float(cierre_anterior['saldo_final_banco'] or 0)
                ajuste_default = 0.0
            else:
                fecha_inicio = hoy_str
                saldo_inicial_efectivo = ReporteCajaModel._monto_no_negativo(
                    datos.get('saldo_inicial_efectivo'), 'Saldo inicial de efectivo'
                )
                saldo_inicial_banco = ReporteCajaModel._monto_no_negativo(
                    datos.get('saldo_inicial_banco'), 'Saldo inicial del banco'
                )
                ajuste_default = 0.0

            ajuste_banco = ReporteCajaModel._monto_no_negativo(
                datos.get('ajuste_banco_externo', ajuste_default),
                'Ajuste bancario externo',
            )
            movimientos = ReporteCajaModel._obtener_movimientos_para_cierre(
                fecha_inicio, hoy_str
            )
            saldo_final_efectivo = (
                saldo_inicial_efectivo
                + movimientos['ingresos_manuales_efectivo']
                + movimientos['ventas_contado_efectivo']
                + movimientos['anticipos_efectivo']
                + movimientos['abonos_efectivo']
                - movimientos['egresos_manuales_efectivo']
            )
            saldo_final_banco = (
                saldo_inicial_banco
                + movimientos['ingresos_banco_registrados']
                + ajuste_banco
            )
            total_final = saldo_final_efectivo + saldo_final_banco

            db.execute(
                """
                INSERT INTO cierre_caja (
                    fecha_cierre, fecha_inicio_movimientos,
                    saldo_inicial_efectivo, saldo_inicial_banco,
                    ingresos_manuales_efectivo, ventas_contado_efectivo,
                    anticipos_efectivo, abonos_efectivo,
                    egresos_manuales_efectivo, ingresos_banco_registrados,
                    ajuste_banco_externo, saldo_final_efectivo,
                    saldo_final_banco, total_final
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    fecha_inicio_movimientos = VALUES(fecha_inicio_movimientos),
                    saldo_inicial_efectivo = VALUES(saldo_inicial_efectivo),
                    saldo_inicial_banco = VALUES(saldo_inicial_banco),
                    ingresos_manuales_efectivo = VALUES(ingresos_manuales_efectivo),
                    ventas_contado_efectivo = VALUES(ventas_contado_efectivo),
                    anticipos_efectivo = VALUES(anticipos_efectivo),
                    abonos_efectivo = VALUES(abonos_efectivo),
                    egresos_manuales_efectivo = VALUES(egresos_manuales_efectivo),
                    ingresos_banco_registrados = VALUES(ingresos_banco_registrados),
                    ajuste_banco_externo = VALUES(ajuste_banco_externo),
                    saldo_final_efectivo = VALUES(saldo_final_efectivo),
                    saldo_final_banco = VALUES(saldo_final_banco),
                    total_final = VALUES(total_final)
                """,
                (
                    hoy_str,
                    fecha_inicio,
                    saldo_inicial_efectivo,
                    saldo_inicial_banco,
                    movimientos['ingresos_manuales_efectivo'],
                    movimientos['ventas_contado_efectivo'],
                    movimientos['anticipos_efectivo'],
                    movimientos['abonos_efectivo'],
                    movimientos['egresos_manuales_efectivo'],
                    movimientos['ingresos_banco_registrados'],
                    ajuste_banco,
                    saldo_final_efectivo,
                    saldo_final_banco,
                    total_final,
                ),
            )

            resultado = ReporteCajaModel.obtener_cierre_actual()
            if resultado['success']:
                resultado['message'] = 'Cierre de caja guardado.'
            return resultado
        except ValueError as e:
            return {'success': False, 'error_code': 'validation', 'message': str(e)}
        except Exception as e:
            logger.error(f"Error aplicando cierre de caja: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def _serializar_fecha(valor):
        if hasattr(valor, 'isoformat'):
            return valor.isoformat()
        return str(valor) if valor is not None else None

    @staticmethod
    def obtener_ajustes_banco(fecha_cierre):
        db = Database()
        ajustes = db.fetch_all(
            """
            SELECT id, fecha_cierre, tipo, monto, descripcion, referencia,
                   created_at, updated_at
            FROM cierre_caja_ajuste_banco
            WHERE fecha_cierre = %s
            ORDER BY created_at DESC, id DESC
            """,
            (fecha_cierre,),
        ) or []
        for ajuste in ajustes:
            ajuste['fecha_cierre'] = ReporteCajaModel._serializar_fecha(ajuste['fecha_cierre'])
            ajuste['monto'] = float(ajuste['monto'] or 0)
            for campo in ('created_at', 'updated_at'):
                if hasattr(ajuste.get(campo), 'isoformat'):
                    ajuste[campo] = ajuste[campo].isoformat(sep=' ')
        entradas = sum(a['monto'] for a in ajustes if a['tipo'] == 'entrada')
        retiros = sum(a['monto'] for a in ajustes if a['tipo'] == 'retiro')
        return {
            'ajustes': ajustes,
            'total_entradas': entradas,
            'total_retiros': retiros,
            'saldo_neto': entradas - retiros,
        }

    @staticmethod
    def listar_cierres_mes(anio, mes):
        try:
            anio = int(anio)
            mes = int(mes)
            if mes < 1 or mes > 12:
                raise ValueError('Mes no válido.')
            db = Database()
            fecha_inicio = datetime(anio, mes, 1).date()
            if mes == 12:
                fecha_fin = datetime(anio + 1, 1, 1).date() - timedelta(days=1)
            else:
                fecha_fin = datetime(anio, mes + 1, 1).date() - timedelta(days=1)

            cierres = db.fetch_all(
                """
                SELECT * FROM cierre_caja
                WHERE fecha_cierre BETWEEN %s AND %s
                ORDER BY fecha_cierre DESC
                """,
                (fecha_inicio.isoformat(), fecha_fin.isoformat()),
            ) or []

            resultado = []
            for cierre in cierres:
                formateado = ReporteCajaModel._formatear_cierre(cierre)
                ajustes = ReporteCajaModel.obtener_ajustes_banco(formateado['fecha_cierre'])
                formateado['ajustes_banco'] = ajustes
                resultado.append(formateado)
            return {
                'success': True,
                'cierres': resultado,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': fecha_fin.isoformat(),
            }
        except (TypeError, ValueError) as e:
            return {'success': False, 'error_code': 'validation', 'message': str(e)}
        except Exception as e:
            logger.error(f"Error listando cierres mensuales: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def obtener_cierre_fecha(fecha_cierre):
        try:
            datetime.strptime(fecha_cierre, '%Y-%m-%d')
            db = Database()
            cierre = db.fetch_one(
                "SELECT * FROM cierre_caja WHERE fecha_cierre = %s",
                (fecha_cierre,),
            )
            if not cierre:
                return {'success': False, 'error_code': 'not_found', 'message': 'Cierre no encontrado.'}
            formateado = ReporteCajaModel._formatear_cierre(cierre)
            formateado['ajustes_banco'] = ReporteCajaModel.obtener_ajustes_banco(fecha_cierre)
            return {'success': True, 'cierre': formateado}
        except ValueError:
            return {'success': False, 'error_code': 'validation', 'message': 'Fecha de cierre no válida.'}
        except Exception as e:
            logger.error(f"Error obteniendo cierre: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def crear_actualizar_ajuste_banco(fecha_cierre, datos, ajuste_id=None):
        try:
            datetime.strptime(fecha_cierre, '%Y-%m-%d')
            tipo = str(datos.get('tipo', '')).strip().lower()
            if tipo not in ('entrada', 'retiro'):
                raise ValueError('El tipo debe ser entrada o retiro.')
            monto = ReporteCajaModel._monto_no_negativo(datos.get('monto'), 'Monto')
            if monto <= 0:
                raise ValueError('El monto debe ser mayor a cero.')
            descripcion = str(datos.get('descripcion', '')).strip()
            if not descripcion:
                raise ValueError('La descripción es requerida.')
            referencia = str(datos.get('referencia', '')).strip() or None

            db = Database()
            cierre = db.fetch_one(
                "SELECT id FROM cierre_caja WHERE fecha_cierre = %s",
                (fecha_cierre,),
            )
            if not cierre:
                return {'success': False, 'error_code': 'not_found', 'message': 'Primero aplica el cierre de esa fecha.'}

            if ajuste_id:
                db.execute(
                    """
                    UPDATE cierre_caja_ajuste_banco
                    SET tipo = %s, monto = %s, descripcion = %s, referencia = %s
                    WHERE id = %s AND fecha_cierre = %s
                    """,
                    (tipo, monto, descripcion, referencia, ajuste_id, fecha_cierre),
                )
                message = 'Ajuste bancario actualizado.'
            else:
                db.execute(
                    """
                    INSERT INTO cierre_caja_ajuste_banco
                        (fecha_cierre, tipo, monto, descripcion, referencia)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (fecha_cierre, tipo, monto, descripcion, referencia),
                )
                message = 'Ajuste bancario registrado.'

            cierre_actualizado = ReporteCajaModel.obtener_cierre_fecha(fecha_cierre)
            cierre_actualizado['message'] = message
            return cierre_actualizado
        except ValueError as e:
            return {'success': False, 'error_code': 'validation', 'message': str(e)}
        except Exception as e:
            logger.error(f"Error guardando ajuste bancario: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def eliminar_ajuste_banco(fecha_cierre, ajuste_id):
        try:
            db = Database()
            db.execute(
                "DELETE FROM cierre_caja_ajuste_banco WHERE id = %s AND fecha_cierre = %s",
                (ajuste_id, fecha_cierre),
            )
            return ReporteCajaModel.obtener_cierre_fecha(fecha_cierre)
        except Exception as e:
            logger.error(f"Error eliminando ajuste bancario: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def editar_cierre(fecha_cierre, datos):
        try:
            datetime.strptime(fecha_cierre, '%Y-%m-%d')
            db = Database()
            cierre = db.fetch_one(
                "SELECT * FROM cierre_caja WHERE fecha_cierre = %s",
                (fecha_cierre,),
            )
            if not cierre:
                return {'success': False, 'error_code': 'not_found', 'message': 'Cierre no encontrado.'}

            saldo_inicial_efectivo = ReporteCajaModel._monto_no_negativo(
                datos.get('saldo_inicial_efectivo'), 'Saldo inicial de efectivo'
            )
            saldo_inicial_banco = ReporteCajaModel._monto_no_negativo(
                datos.get('saldo_inicial_banco'), 'Saldo inicial del banco'
            )

            ajustes = ReporteCajaModel.obtener_ajustes_banco(fecha_cierre)
            ajuste_neto = ajustes['saldo_neto']
            movimientos = ReporteCajaModel._obtener_movimientos_para_cierre(
                fecha_cierre, fecha_cierre
            )
            saldo_final_efectivo = (
                saldo_inicial_efectivo
                + movimientos['ingresos_manuales_efectivo']
                + movimientos['ventas_contado_efectivo']
                + movimientos['anticipos_efectivo']
                + movimientos['abonos_efectivo']
                - movimientos['egresos_manuales_efectivo']
            )
            saldo_final_banco = (
                saldo_inicial_banco
                + movimientos['ingresos_banco_registrados']
                + ajuste_neto
            )

            db.execute(
                """
                UPDATE cierre_caja
                SET fecha_inicio_movimientos = %s,
                    saldo_inicial_efectivo = %s,
                    saldo_inicial_banco = %s,
                    ingresos_manuales_efectivo = %s,
                    ventas_contado_efectivo = %s,
                    anticipos_efectivo = %s,
                    abonos_efectivo = %s,
                    egresos_manuales_efectivo = %s,
                    ingresos_banco_registrados = %s,
                    ajuste_banco_externo = %s,
                    saldo_final_efectivo = %s,
                    saldo_final_banco = %s,
                    total_final = %s
                WHERE fecha_cierre = %s
                """,
                (
                    fecha_cierre,
                    saldo_inicial_efectivo,
                    saldo_inicial_banco,
                    movimientos['ingresos_manuales_efectivo'],
                    movimientos['ventas_contado_efectivo'],
                    movimientos['anticipos_efectivo'],
                    movimientos['abonos_efectivo'],
                    movimientos['egresos_manuales_efectivo'],
                    movimientos['ingresos_banco_registrados'],
                    ajuste_neto,
                    saldo_final_efectivo,
                    saldo_final_banco,
                    saldo_final_efectivo + saldo_final_banco,
                    fecha_cierre,
                ),
            )

            cierres_siguientes = db.fetch_all(
                """
                SELECT * FROM cierre_caja
                WHERE fecha_cierre > %s
                ORDER BY fecha_cierre ASC
                """,
                (fecha_cierre,),
            ) or []

            apertura_efectivo = saldo_final_efectivo
            apertura_banco = saldo_final_banco
            for cierre_siguiente in cierres_siguientes:
                fecha_siguiente = cierre_siguiente['fecha_cierre'].isoformat()
                movimientos_siguientes = ReporteCajaModel._obtener_movimientos_para_cierre(
                    fecha_siguiente, fecha_siguiente
                )
                ajustes_siguientes = ReporteCajaModel.obtener_ajustes_banco(fecha_siguiente)
                ajuste_neto_siguiente = ajustes_siguientes['saldo_neto']
                final_efectivo = (
                    apertura_efectivo
                    + movimientos_siguientes['ingresos_manuales_efectivo']
                    + movimientos_siguientes['ventas_contado_efectivo']
                    + movimientos_siguientes['anticipos_efectivo']
                    + movimientos_siguientes['abonos_efectivo']
                    - movimientos_siguientes['egresos_manuales_efectivo']
                )
                final_banco = (
                    apertura_banco
                    + movimientos_siguientes['ingresos_banco_registrados']
                    + ajuste_neto_siguiente
                )
                db.execute(
                    """
                    UPDATE cierre_caja
                    SET saldo_inicial_efectivo = %s,
                        saldo_inicial_banco = %s,
                        ingresos_manuales_efectivo = %s,
                        ventas_contado_efectivo = %s,
                        anticipos_efectivo = %s,
                        abonos_efectivo = %s,
                        egresos_manuales_efectivo = %s,
                        ingresos_banco_registrados = %s,
                        ajuste_banco_externo = %s,
                        saldo_final_efectivo = %s,
                        saldo_final_banco = %s,
                        total_final = %s
                    WHERE fecha_cierre = %s
                    """,
                    (
                        apertura_efectivo,
                        apertura_banco,
                        movimientos_siguientes['ingresos_manuales_efectivo'],
                        movimientos_siguientes['ventas_contado_efectivo'],
                        movimientos_siguientes['anticipos_efectivo'],
                        movimientos_siguientes['abonos_efectivo'],
                        movimientos_siguientes['egresos_manuales_efectivo'],
                        movimientos_siguientes['ingresos_banco_registrados'],
                        ajuste_neto_siguiente,
                        final_efectivo,
                        final_banco,
                        final_efectivo + final_banco,
                        fecha_siguiente,
                    ),
                )
                apertura_efectivo = final_efectivo
                apertura_banco = final_banco

            return ReporteCajaModel.obtener_cierre_fecha(fecha_cierre)
        except ValueError as e:
            return {'success': False, 'error_code': 'validation', 'message': str(e)}
        except Exception as e:
            logger.error(f"Error editando cierre: {e}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def ejecutar_diagnostico():
        try:
            db = Database()
            diagnosticos = []
            
            try:
                db.fetch_one("SELECT 1")
                diagnosticos.append({'componente': 'Base de datos', 'estado': 'OK', 'mensaje': 'Conexión exitosa'})
            except Exception as e:
                diagnosticos.append({'componente': 'Base de datos', 'estado': 'ERROR', 'mensaje': str(e)})
            
            try:
                tabla = db.fetch_one("SHOW TABLES LIKE 'reporte_caja'")
                if tabla:
                    diagnosticos.append({'componente': 'Tabla reporte_caja', 'estado': 'OK', 'mensaje': 'Tabla existente'})
                    cols = db.fetch_all("DESCRIBE reporte_caja")
                    col_names = [c['Field'] for c in cols]
                    required = ['id','ingresos','razon_ingreso','fecha_ingreso','categoria','egresos','razon_egreso','fecha_egreso']
                    for col in required:
                        if col in col_names:
                            diagnosticos.append({'componente': f'Columna {col}', 'estado': 'OK', 'mensaje': 'Presente'})
                        else:
                            diagnosticos.append({'componente': f'Columna {col}', 'estado': 'ERROR', 'mensaje': 'Faltante'})
                else:
                    diagnosticos.append({'componente': 'Tabla reporte_caja', 'estado': 'ERROR', 'mensaje': 'No existe'})
            except Exception as e:
                diagnosticos.append({'componente': 'Tabla reporte_caja', 'estado': 'ERROR', 'mensaje': str(e)})
            
            try:
                datos = db.fetch_one("SELECT COUNT(*) as total, COALESCE(SUM(ingresos),0) as sum_ing, COALESCE(SUM(egresos),0) as sum_eg FROM reporte_caja")
                diagnosticos.append({
                    'componente': 'Datos',
                    'estado': 'OK',
                    'mensaje': f"{datos['total']} movimientos registrados",
                    'conteos': {'total_movimientos': datos['total'], 'total_ingresos': float(datos['sum_ing']), 'total_egresos': float(datos['sum_eg'])}
                })
            except Exception as e:
                diagnosticos.append({'componente': 'Datos', 'estado': 'ERROR', 'mensaje': str(e)})
            
            total_checks = len(diagnosticos)
            checks_ok = sum(1 for d in diagnosticos if d['estado'] == 'OK')
            checks_error = sum(1 for d in diagnosticos if d['estado'] == 'ERROR')
            checks_warning = sum(1 for d in diagnosticos if d['estado'] == 'ADVERTENCIA')
            
            return {
                'success': True,
                'diagnosticos': diagnosticos,
                'total_checks': total_checks,
                'checks_ok': checks_ok,
                'checks_error': checks_error,
                'checks_warning': checks_warning
            }
        except Exception as e:
            logger.error(f"Error en ejecutar_diagnostico: {e}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def inicializar_datos_ejemplo():
        try:
            db = Database()
            from datetime import datetime, timedelta
            import random
            
            hoy = datetime.now()
            
            datos_existentes = db.fetch_one("SELECT COUNT(*) as total FROM reporte_caja")
            if datos_existentes and datos_existentes['total'] > 5:
                return {
                    'success': True,
                    'message': 'Ya existen datos en la tabla, no se inicializaron ejemplos',
                    'ingresos_creados': 0,
                    'egresos_creados': 0
                }
            
            ingresos_ejemplo = [
                {'razon': 'Venta de concentrado bovino', 'categoria': 'venta', 'monto_min': 50000, 'monto_max': 200000},
                {'razon': 'Servicio veterinario', 'categoria': 'servicio', 'monto_min': 30000, 'monto_max': 100000},
                {'razon': 'Venta de medicamentos', 'categoria': 'venta', 'monto_min': 10000, 'monto_max': 50000},
                {'razon': 'Pago de deuda cliente', 'categoria': 'otros', 'monto_min': 5000, 'monto_max': 30000},
            ]
            
            egresos_ejemplo = [
                {'razon': 'Compra de insumos veterinarios', 'categoria': 'insumo', 'monto_min': 20000, 'monto_max': 100000},
                {'razon': 'Pago de salarios', 'categoria': 'salario', 'monto_min': 800000, 'monto_max': 1200000},
                {'razon': 'Pago de servicios públicos', 'categoria': 'otros', 'monto_min': 300000, 'monto_max': 500000},
                {'razon': 'Mantenimiento de equipos', 'categoria': 'otros', 'monto_min': 50000, 'monto_max': 150000},
            ]
            
            ingresos_creados = 0
            egresos_creados = 0
            
            for i in range(15):
                fecha = hoy - timedelta(days=i)
                
                num_ingresos = random.randint(1, 2)
                for _ in range(num_ingresos):
                    ingreso = random.choice(ingresos_ejemplo)
                    monto = random.randint(ingreso['monto_min'], ingreso['monto_max'])
                    fecha_mov = fecha.replace(
                        hour=random.randint(9, 17),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    check_query = """
                        SELECT id FROM reporte_caja 
                        WHERE razon_ingreso = %s AND ingresos = %s
                    """
                    duplicate = db.fetch_one(check_query, (ingreso['razon'], monto))
                    
                    if not duplicate:
                        try:
                            db.execute("START TRANSACTION")
                            query = """
                                INSERT INTO reporte_caja (ingresos, razon_ingreso, fecha_ingreso, categoria)
                                VALUES (%s, %s, %s, %s)
                            """
                            db.execute(query, (monto, ingreso['razon'], fecha_mov, ingreso['categoria']))
                            db.execute("COMMIT")
                            ingresos_creados += 1
                        except Exception as e:
                            db.execute("ROLLBACK")
                            logger.error(f"Error creando ingreso de ejemplo: {e}")
                
                num_egresos = random.randint(1, 2)
                for _ in range(num_egresos):
                    egreso = random.choice(egresos_ejemplo)
                    monto = random.randint(egreso['monto_min'], egreso['monto_max'])
                    fecha_mov = fecha.replace(
                        hour=random.randint(9, 17),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    check_query = """
                        SELECT id FROM reporte_caja 
                        WHERE razon_egreso = %s AND egresos = %s
                    """
                    duplicate = db.fetch_one(check_query, (egreso['razon'], monto))
                    
                    if not duplicate:
                        try:
                            db.execute("START TRANSACTION")
                            query = """
                                INSERT INTO reporte_caja (egresos, razon_egreso, fecha_egreso, categoria)
                                VALUES (%s, %s, %s, %s)
                            """
                            db.execute(query, (monto, egreso['razon'], fecha_mov, egreso['categoria']))
                            db.execute("COMMIT")
                            egresos_creados += 1
                        except Exception as e:
                            db.execute("ROLLBACK")
                            logger.error(f"Error creando egreso de ejemplo: {e}")
            
            return {
                'success': True,
                'message': f'Datos de ejemplo creados exitosamente: {ingresos_creados} ingresos y {egresos_creados} egresos',
                'ingresos_creados': ingresos_creados,
                'egresos_creados': egresos_creados
            }
        except Exception as e:
            logger.error(f"Error en inicializar_datos_ejemplo: {e}")
            return {'success': False, 'message': str(e)}

model = ReporteCajaModel()