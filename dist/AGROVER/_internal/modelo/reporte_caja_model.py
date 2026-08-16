# modelo/reporte_caja_model.py
import logging
from datetime import datetime, timedelta
import random
from database import db

logger = logging.getLogger(__name__)

class ReporteCajaModel:
    def __init__(self):
        self.table_name = "reporte_caja"
    
    def inicializar_datos_ejemplo(self):
        """Inicializa datos de ejemplo en reporte_caja"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            print("🧹 Limpiando datos existentes...")
            cursor.execute("TRUNCATE TABLE reporte_caja")
            
            print("📊 Generando datos de ejemplo...")
            
            # Categorías de egresos
            categorias_egresos = [
                "Compra de medicamentos",
                "Pago de salarios",
                "Mantenimiento de equipo",
                "Servicios públicos",
                "Alquiler local"
            ]
            
            # Razones de ingresos
            razones_ingresos = [
                "Venta de medicamentos veterinarios",
                "Consulta veterinaria general",
                "Vacunación de ganado",
                "Venta de alimentos concentrados",
                "Castración de mascotas"
            ]
            
            # Generar datos para los últimos 30 días
            hoy = datetime.now()
            total_movimientos = 0
            
            for dia in range(30):
                fecha_base = hoy - timedelta(days=dia)
                
                # Generar 2-4 ingresos por día
                num_ingresos = random.randint(2, 4)
                for _ in range(num_ingresos):
                    fecha = fecha_base.replace(
                        hour=random.randint(8, 18),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    
                    monto = round(random.uniform(50000, 500000), 2)
                    razon = random.choice(razones_ingresos)
                    categoria = self._obtener_categoria_por_tipo('ingreso', razon)
                    
                    cursor.execute("""
                        INSERT INTO reporte_caja (ingresos, razon_ingreso, fecha_ingreso, categoria)
                        VALUES (%s, %s, %s, %s)
                    """, (monto, razon, fecha, categoria))
                    total_movimientos += 1
                
                # Generar 1-3 egresos por día
                num_egresos = random.randint(1, 3)
                for _ in range(num_egresos):
                    fecha = fecha_base.replace(
                        hour=random.randint(8, 18),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    
                    monto = round(random.uniform(20000, 300000), 2)
                    razon = random.choice(categorias_egresos)
                    categoria = self._obtener_categoria_por_tipo('egreso', razon)
                    
                    cursor.execute("""
                        INSERT INTO reporte_caja (egresos, razon_egreso, fecha_egreso, categoria)
                        VALUES (%s, %s, %s, %s)
                    """, (monto, razon, fecha, categoria))
                    total_movimientos += 1
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'total_movimientos': total_movimientos,
                'periodo': 'Últimos 30 días',
                'mensaje': f'Generados {total_movimientos} movimientos de ejemplo'
            }
            
        except Exception as e:
            logger.error(f"Error inicializando datos de ejemplo: {e}")
            return {'success': False, 'error': str(e)}
    
    def _obtener_categoria_por_tipo(self, tipo, razon):
        """Obtiene la categoría basada en el tipo y la razón"""
        razon_lower = razon.lower()
        if tipo == 'ingreso':
            if 'venta' in razon_lower:
                return 'venta'
            elif 'consulta' in razon_lower or 'servicio' in razon_lower:
                return 'servicio'
            else:
                return 'otros'
        else:  # egreso
            if 'salario' in razon_lower:
                return 'salario'
            elif 'alquiler' in razon_lower:
                return 'alquiler'
            elif 'medicamento' in razon_lower or 'insumo' in razon_lower:
                return 'insumo'
            else:
                return 'otros'
    
    def crear_movimiento(self, data):
        """
        Crea un nuevo movimiento en reporte_caja
        data: dict con los datos del movimiento
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Validar datos requeridos
            if 'monto' not in data or 'razon' not in data or 'tipo' not in data:
                return {'success': False, 'error': 'Datos incompletos: se requiere monto, razon y tipo'}
            
            # Preparar campos según si es ingreso o egreso
            if data['tipo'] == 'ingreso':
                campos = ['ingresos', 'razon_ingreso', 'fecha_ingreso']
                valores = [float(data['monto']), data['razon']]
            else:  # egreso
                campos = ['egresos', 'razon_egreso', 'fecha_egreso']
                valores = [float(data['monto']), data['razon']]
            
            # Agregar fecha
            fecha = data.get('fecha')
            if not fecha:
                fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            valores.append(fecha)
            
            # Agregar categoría
            if 'categoria' in data and data['categoria']:
                categoria = data['categoria']
            else:
                categoria = self._obtener_categoria_por_tipo(data['tipo'], data['razon'])
            
            campos.append('categoria')
            valores.append(categoria)
            
            query = f"INSERT INTO {self.table_name} ({', '.join(campos)}) VALUES ({', '.join(['%s'] * len(campos))})"
            
            cursor.execute(query, valores)
            conn.commit()
            
            movimiento_id = cursor.lastrowid
            
            # Obtener el movimiento recién creado
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = %s", (movimiento_id,))
            movimiento = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {'success': True, 'id': movimiento_id, 'data': movimiento}
            
        except Exception as e:
            logger.error(f"Error creando movimiento: {e}")
            return {'success': False, 'error': str(e)}
    
    def obtener_movimientos(self, fecha_inicio=None, fecha_fin=None, tipo=None, page=1, per_page=10):
        """
        Obtiene movimientos con filtros opcionales
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            condiciones = []
            valores = []
            
            # Filtrar por fecha
            if fecha_inicio and fecha_fin:
                condiciones.append("""
                    (fecha_ingreso BETWEEN %s AND %s OR fecha_egreso BETWEEN %s AND %s)
                """)
                valores.extend([fecha_inicio, fecha_fin, fecha_inicio, fecha_fin])
            
            # Filtrar por tipo (ingreso/egreso)
            if tipo == 'ingreso':
                condiciones.append('ingresos > 0')
            elif tipo == 'egreso':
                condiciones.append('egresos > 0')
            
            # Construir query
            where_clause = ""
            if condiciones:
                where_clause = f"WHERE {' AND '.join(condiciones)}"
            
            # Query para contar total
            count_query = f"SELECT COUNT(*) as total FROM {self.table_name} {where_clause}"
            cursor.execute(count_query, valores)
            total_result = cursor.fetchone()
            total = total_result['total'] if total_result else 0
            
            # Query para obtener datos paginados
            offset = (page - 1) * per_page
            query = f"""
                SELECT 
                    id,
                    ingresos,
                    razon_ingreso,
                    fecha_ingreso,
                    egresos,
                    razon_egreso,
                    fecha_egreso,
                    categoria,
                    CASE 
                        WHEN ingresos > 0 THEN 'ingreso' 
                        ELSE 'egreso' 
                    END as tipo_movimiento,
                    COALESCE(razon_ingreso, razon_egreso) as descripcion,
                    COALESCE(fecha_ingreso, fecha_egreso) as fecha
                FROM {self.table_name} 
                {where_clause}
                ORDER BY COALESCE(fecha_ingreso, fecha_egreso) DESC
                LIMIT %s OFFSET %s
            """
            
            valores.extend([per_page, offset])
            cursor.execute(query, valores)
            movimientos = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'data': movimientos,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo movimientos: {e}")
            return {'success': False, 'error': str(e)}
    
    def obtener_resumen(self, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene resumen financiero para un período
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            condiciones = []
            valores = []
            
            if fecha_inicio and fecha_fin:
                condiciones.append("""
                    (fecha_ingreso BETWEEN %s AND %s OR fecha_egreso BETWEEN %s AND %s)
                """)
                valores.extend([fecha_inicio, fecha_fin, fecha_inicio, fecha_fin])
            
            where_clause = ""
            if condiciones:
                where_clause = f"WHERE {' AND '.join(condiciones)}"
            
            query = f"""
                SELECT 
                    COALESCE(SUM(ingresos), 0) as total_ingresos,
                    COALESCE(SUM(egresos), 0) as total_egresos,
                    COALESCE(SUM(ingresos), 0) - COALESCE(SUM(egresos), 0) as saldo_neto,
                    COUNT(CASE WHEN ingresos > 0 THEN 1 END) as cantidad_ingresos,
                    COUNT(CASE WHEN egresos > 0 THEN 1 END) as cantidad_egresos
                FROM {self.table_name} 
                {where_clause}
            """
            
            cursor.execute(query, valores)
            resumen = cursor.fetchone()
            
            if not resumen:
                resumen = {
                    'total_ingresos': 0,
                    'total_egresos': 0,
                    'saldo_neto': 0,
                    'cantidad_ingresos': 0,
                    'cantidad_egresos': 0
                }
            
            # Obtener distribución de egresos por categoría
            dist_where = "WHERE egresos > 0"
            dist_valores = []
            
            if fecha_inicio and fecha_fin:
                dist_where += " AND fecha_egreso BETWEEN %s AND %s"
                dist_valores.extend([fecha_inicio, fecha_fin])
            
            dist_query = f"""
                SELECT 
                    COALESCE(categoria, 'otros') as categoria,
                    SUM(egresos) as total,
                    COUNT(*) as cantidad
                FROM reporte_caja 
                {dist_where}
                GROUP BY COALESCE(categoria, 'otros')
                ORDER BY SUM(egresos) DESC
            """
            
            cursor.execute(dist_query, dist_valores)
            distribucion = cursor.fetchall()
            
            # Obtener flujo diario
            flujo_where = ""
            flujo_valores = []
            
            if fecha_inicio and fecha_fin:
                flujo_where = "WHERE (fecha_ingreso BETWEEN %s AND %s OR fecha_egreso BETWEEN %s AND %s)"
                flujo_valores.extend([fecha_inicio, fecha_fin, fecha_inicio, fecha_fin])
            
            flujo_query = f"""
                SELECT 
                    DATE(COALESCE(fecha_ingreso, fecha_egreso)) as fecha,
                    COALESCE(SUM(ingresos), 0) as ingresos,
                    COALESCE(SUM(egresos), 0) as egresos
                FROM reporte_caja 
                {flujo_where}
                GROUP BY DATE(COALESCE(fecha_ingreso, fecha_egreso))
                ORDER BY fecha ASC
            """
            
            cursor.execute(flujo_query, flujo_valores)
            flujo = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'resumen': resumen,
                'distribucion': distribucion,
                'flujo': flujo
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return {'success': False, 'error': str(e)}
        

    def obtener_movimientos_completos(self, fecha_inicio=None, fecha_fin=None, tipo=None, page=1, per_page=10):
        """
        Versión mejorada que incluye todos los campos necesarios
        """
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            condiciones = []
            valores = []
            
            # Filtrar por fecha
            if fecha_inicio and fecha_fin:
                condiciones.append("""
                    (fecha_ingreso BETWEEN %s AND %s OR fecha_egreso BETWEEN %s AND %s)
                """)
                valores.extend([fecha_inicio, fecha_fin, fecha_inicio, fecha_fin])
            
            # Filtrar por tipo (ingreso/egreso)
            if tipo == 'ingreso':
                condiciones.append('ingresos > 0')
            elif tipo == 'egreso':
                condiciones.append('egresos > 0')
            
            # Construir query
            where_clause = ""
            if condiciones:
                where_clause = f"WHERE {' AND '.join(condiciones)}"
            
            # Query para contar total
            count_query = f"SELECT COUNT(*) as total FROM {self.table_name} {where_clause}"
            cursor.execute(count_query, valores)
            total_result = cursor.fetchone()
            total = total_result['total'] if total_result else 0
            
            # Query para obtener datos con ID EXPLÍCITO
            offset = (page - 1) * per_page
            query = f"""
                SELECT 
                    id,
                    ingresos,
                    razon_ingreso,
                    fecha_ingreso,
                    egresos,
                    razon_egreso,
                    fecha_egreso,
                    categoria,
                    CASE 
                        WHEN ingresos > 0 THEN 'ingreso' 
                        ELSE 'egreso' 
                    END as tipo_movimiento,
                    COALESCE(razon_ingreso, razon_egreso) as descripcion,
                    COALESCE(fecha_ingreso, fecha_egreso) as fecha
                FROM {self.table_name} 
                {where_clause}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """
            
            valores.extend([per_page, offset])
            cursor.execute(query, valores)
            movimientos = cursor.fetchall()
            
            # Asegurarse de que el campo ID esté presente
            for movimiento in movimientos:
                if 'id' not in movimiento:
                    movimiento['id'] = 0
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'data': movimientos,
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo movimientos completos: {e}")
            return {'success': False, 'error': str(e)}
    
    def obtener_movimiento_por_id(self, movimiento_id):
        """Obtiene un movimiento por su ID"""
        try:
            conn = db.get_connection()
            # ✅ AGREGAR dictionary=True aquí también
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT * FROM {self.table_name} WHERE id = %s
            """
            cursor.execute(query, (movimiento_id,))
            movimiento = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'data': movimiento if movimiento else None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo movimiento por ID: {e}")
            return {'success': False, 'error': str(e)}
    
    def actualizar_movimiento(self, movimiento_id, data):
        """Actualiza un movimiento existente"""
        try:
            conn = db.get_connection()
            # ✅ AGREGAR dictionary=True aquí
            cursor = conn.cursor(dictionary=True)
            
            # Obtener el movimiento actual
            cursor.execute(f"SELECT * FROM {self.table_name} WHERE id = %s", (movimiento_id,))
            movimiento_actual = cursor.fetchone()
            
            if not movimiento_actual:
                cursor.close()
                conn.close()
                return {'success': False, 'error': 'Movimiento no encontrado'}
            
            # ✅ AHORA SÍ funciona porque es un diccionario
            # Determinar tipo basado en datos existentes o nuevos
            tipo = 'ingreso' if movimiento_actual.get('ingresos', 0) > 0 else 'egreso'
            if 'tipo' in data:
                tipo = data['tipo']
            
            # Preparar campos a actualizar
            campos = []
            valores = []
            
            if 'monto' in data:
                monto = float(data['monto'])
                if tipo == 'ingreso':
                    campos.append('ingresos = %s')
                    valores.append(monto)
                    campos.append('egresos = %s')
                    valores.append(0)
                else:
                    campos.append('egresos = %s')
                    valores.append(monto)
                    campos.append('ingresos = %s')
                    valores.append(0)
            
            if 'razon' in data:
                if tipo == 'ingreso':
                    campos.append('razon_ingreso = %s')
                    valores.append(data['razon'])
                    campos.append('razon_egreso = %s')
                    valores.append(None)
                else:
                    campos.append('razon_egreso = %s')
                    valores.append(data['razon'])
                    campos.append('razon_ingreso = %s')
                    valores.append(None)
            
            if 'fecha' in data:
                if tipo == 'ingreso':
                    campos.append('fecha_ingreso = %s')
                    valores.append(data['fecha'])
                    campos.append('fecha_egreso = %s')
                    valores.append(None)
                else:
                    campos.append('fecha_egreso = %s')
                    valores.append(data['fecha'])
                    campos.append('fecha_ingreso = %s')
                    valores.append(None)
            
            if 'categoria' in data:
                campos.append('categoria = %s')
                valores.append(data['categoria'])
            
            if campos:
                query = f"UPDATE {self.table_name} SET {', '.join(campos)} WHERE id = %s"
                valores.append(movimiento_id)
                cursor.execute(query, valores)
                conn.commit()
                affected_rows = cursor.rowcount
            else:
                affected_rows = 0
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'affected_rows': affected_rows
            }
            
        except Exception as e:
            logger.error(f"Error actualizando movimiento: {e}")
            return {'success': False, 'error': str(e)}
    
    def eliminar_movimiento(self, movimiento_id):
        """Elimina un movimiento"""
        try:
            conn = db.get_connection()
            cursor = conn.cursor()  # ✅ Aquí no necesita dictionary=True
            
            query = f"DELETE FROM {self.table_name} WHERE id = %s"
            cursor.execute(query, (movimiento_id,))
            conn.commit()
            affected_rows = cursor.rowcount
            
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'affected_rows': affected_rows
            }
            
        except Exception as e:
            logger.error(f"Error eliminando movimiento: {e}")
            return {'success': False, 'error': str(e)}
    
    def obtener_estadisticas_periodo(self, periodo='hoy'):
        """
        Obtiene estadísticas para diferentes períodos predefinidos
        periodo: 'hoy', 'semana', 'mes', 'anio'
        """
        try:
            hoy = datetime.now()
            
            if periodo == 'hoy':
                fecha_inicio = hoy.replace(hour=0, minute=0, second=0)
                fecha_fin = hoy.replace(hour=23, minute=59, second=59)
            elif periodo == 'semana':
                fecha_inicio = hoy - timedelta(days=hoy.weekday())
                fecha_inicio = fecha_inicio.replace(hour=0, minute=0, second=0)
                fecha_fin = fecha_inicio + timedelta(days=6, hours=23, minutes=59, seconds=59)
            elif periodo == 'mes':
                fecha_inicio = hoy.replace(day=1, hour=0, minute=0, second=0)
                if hoy.month == 12:
                    next_month = hoy.replace(year=hoy.year+1, month=1, day=1)
                else:
                    next_month = hoy.replace(month=hoy.month+1, day=1)
                fecha_fin = next_month - timedelta(seconds=1)
            elif periodo == 'anio':
                fecha_inicio = hoy.replace(month=1, day=1, hour=0, minute=0, second=0)
                fecha_fin = hoy.replace(month=12, day=31, hour=23, minute=59, second=59)
            else:
                # Por defecto hoy
                fecha_inicio = hoy.replace(hour=0, minute=0, second=0)
                fecha_fin = hoy.replace(hour=23, minute=59, second=59)
            
            return self.obtener_resumen(
                fecha_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                fecha_fin.strftime('%Y-%m-%d %H:%M:%S')
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas para período {periodo}: {e}")
            return {'success': False, 'error': str(e)}