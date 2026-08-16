from database import db

class ProductoModel:
    @staticmethod
    def obtener_todos_productos(filtros=None):
        """Obtener todos los productos con filtros opcionales"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT p.*, pr.nombre_proveedor
            FROM productos p
            LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
            WHERE 1=1
            """
            params = []
            
            # Aplicar filtros si existen
            if filtros:
                # Filtro por búsqueda de texto
                if filtros.get('busqueda'):
                    sql += " AND (p.nombre LIKE %s OR p.descripcion LIKE %s OR p.categoria LIKE %s OR pr.nombre_proveedor LIKE %s)"
                    like_busqueda = f"%{filtros['busqueda']}%"
                    params.extend([like_busqueda, like_busqueda, like_busqueda, like_busqueda])
                
                # Filtro por categoría
                if filtros.get('categoria'):
                    sql += " AND p.categoria = %s"
                    params.append(filtros['categoria'])
                
                # Filtro por estado (cantidad)
                if filtros.get('estado'):
                    estado = filtros['estado']
                    if estado == 'active':
                        sql += " AND p.cantidad > 0"
                    elif estado == 'inactive':
                        sql += " AND p.cantidad = 0"
                
                # Filtro por stock
                if filtros.get('stock'):
                    stock = filtros['stock']
                    if stock == 'bajo':
                        sql += " AND p.cantidad < 10 AND p.cantidad > 0"
                    elif stock == 'medio':
                        sql += " AND p.cantidad >= 10 AND p.cantidad <= 50"
                    elif stock == 'alto':
                        sql += " AND p.cantidad > 50"
            
            # Ordenar por ID descendente (los más nuevos primero)
            sql += " ORDER BY p.id DESC"
            
            cursor.execute(sql, params)
            productos = cursor.fetchall()
            
            return productos
            
        except Exception as e:
            print(f"Error en obtener_todos_productos: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def buscar_productos(busqueda=""):
        """Buscar productos por nombre (para ventas)"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT id, nombre, descripcion, cantidad, 
                   presentacion, precio_venta, categoria
            FROM productos 
            WHERE cantidad > 0 
            AND nombre LIKE %s
            ORDER BY nombre
            LIMIT 20
            """
            
            like_busqueda = f"%{busqueda}%"
            cursor.execute(sql, (like_busqueda,))
            productos = cursor.fetchall()
            
            return productos
            
        except Exception as e:
            print(f"Error en buscar_productos: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_producto_por_id(producto_id):
        """Obtener producto por ID"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT p.*, pr.nombre_proveedor
            FROM productos p
            LEFT JOIN proveedor pr ON p.proveedor = pr.telefono
            WHERE p.id = %s
            """
            
            cursor.execute(sql, (producto_id,))
            producto = cursor.fetchone()
            
            return producto
            
        except Exception as e:
            print(f"Error en obtener_producto_por_id: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear_producto(datos_producto):
        """Crear un nuevo producto"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            INSERT INTO productos 
            (nombre, descripcion, categoria, cantidad, presentacion, 
             proveedor, precio_costo, precio_venta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                datos_producto['nombre'],
                datos_producto.get('descripcion'),
                datos_producto['categoria'],
                datos_producto.get('cantidad', 0),
                datos_producto.get('presentacion'),
                datos_producto.get('proveedor'),
                datos_producto.get('precio_costo', 0),
                datos_producto.get('precio_venta', 0)
            ))
            
            producto_id = cursor.lastrowid
            conn.commit()
            
            return {
                'success': True,
                'producto_id': producto_id
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error en crear_producto: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def actualizar_producto(producto_id, datos_producto):
        """Actualizar un producto existente"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            UPDATE productos 
            SET nombre = %s,
                descripcion = %s,
                categoria = %s,
                cantidad = %s,
                presentacion = %s,
                proveedor = %s,
                precio_costo = %s,
                precio_venta = %s
            WHERE id = %s
            """
            
            cursor.execute(sql, (
                datos_producto['nombre'],
                datos_producto.get('descripcion'),
                datos_producto['categoria'],
                datos_producto.get('cantidad', 0),
                datos_producto.get('presentacion'),
                datos_producto.get('proveedor'),
                datos_producto.get('precio_costo', 0),
                datos_producto.get('precio_venta', 0),
                producto_id
            ))
            
            conn.commit()
            
            return {
                'success': True,
                'rows_affected': cursor.rowcount
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error en actualizar_producto: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def eliminar_producto(producto_id):
        """Eliminar un producto"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = "DELETE FROM productos WHERE id = %s"
            cursor.execute(sql, (producto_id,))
            
            conn.commit()
            
            return {
                'success': True,
                'rows_affected': cursor.rowcount
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error en eliminar_producto: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_estadisticas():
        """Obtener estadísticas de productos"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Consulta para estadísticas
            sql = """
            SELECT 
                COUNT(*) as total_productos,
                SUM(CASE WHEN cantidad > 0 THEN 1 ELSE 0 END) as productos_activos,
                SUM(CASE WHEN cantidad < 10 AND cantidad > 0 THEN 1 ELSE 0 END) as stock_bajo,
                SUM(cantidad) as total_stock,
                SUM(cantidad * precio_costo) as valor_inventario
            FROM productos
            """
            
            cursor.execute(sql)
            stats = cursor.fetchone()
            
            return stats
            
        except Exception as e:
            print(f"Error en obtener_estadisticas: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_categorias():
        """Obtener lista de categorías únicas"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = "SELECT DISTINCT categoria FROM productos ORDER BY categoria"
            cursor.execute(sql)
            categorias = [row['categoria'] for row in cursor.fetchall()]
            
            return categorias
            
        except Exception as e:
            print(f"Error en obtener_categorias: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_proveedores():
        """Obtener lista de proveedores para select"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = "SELECT telefono, nombre_proveedor FROM proveedor ORDER BY nombre_proveedor"
            cursor.execute(sql)
            proveedores = cursor.fetchall()
            
            return proveedores
            
        except Exception as e:
            print(f"Error en obtener_proveedores: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def actualizar_stock(producto_id, cantidad):
        """Actualizar stock de un producto (para ventas)"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = "UPDATE productos SET cantidad = cantidad - %s WHERE id = %s AND cantidad >= %s"
            cursor.execute(sql, (cantidad, producto_id, cantidad))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return {
                    'success': False,
                    'error': 'Stock insuficiente'
                }
            
            conn.commit()
            return {
                'success': True
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Error en actualizar_stock: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()