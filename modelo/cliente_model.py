from database import db

class ClienteModel:
    @staticmethod
    def buscar_clientes(busqueda=""):
        """Buscar clientes por nombre o cédula"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT cedula, nombre, telefono, correo, direccion
            FROM cliente 
            WHERE nombre LIKE %s OR cedula LIKE %s
            ORDER BY nombre
            LIMIT 20
            """
            
            like_busqueda = f"%{busqueda}%"
            cursor.execute(sql, (like_busqueda, like_busqueda))
            clientes = cursor.fetchall()
            
            return clientes
            
        except Exception as e:
            print(f"Error en buscar_clientes: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_cliente_por_cedula(cedula):
        """Obtener cliente por cédula"""
        conn = None
        cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            sql = """
            SELECT cedula, nombre, telefono, correo, direccion
            FROM cliente 
            WHERE cedula = %s
            """
            
            cursor.execute(sql, (cedula,))
            cliente = cursor.fetchone()
            
            return cliente
            
        except Exception as e:
            print(f"Error en obtener_cliente_por_cedula: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()