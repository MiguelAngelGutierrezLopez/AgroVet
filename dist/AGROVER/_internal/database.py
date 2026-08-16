# database.py - CONEXIÓN MEJORADA CON RECONEXIÓN AUTOMÁTICA
import mysql.connector
from mysql.connector import Error, pooling
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

class Database:
    """Clase para manejar conexión a MySQL con reconexión automática"""
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_pool()
        return cls._instance
    
    def _init_pool(self):
        """Inicializar pool de conexiones"""
        try:
            print(f"🔌 Inicializando pool de conexiones MySQL...")
            
            # Aumentar timeout y otros parámetros
            db_config = Config.DB_CONFIG.copy()
            db_config.update({
                'pool_name': 'agrovet_pool',
                'pool_size': 5,
                'pool_reset_session': True,
                'connect_timeout': 30,
                'connection_timeout': 30,
                'buffered': True,
                'autocommit': False
            })
            
            self._connection_pool = pooling.MySQLConnectionPool(
                pool_name="agrovet_pool",
                pool_size=5,
                **Config.DB_CONFIG
            )
            print(f"✅ Pool de conexiones inicializado (tamaño: 5)")
            
        except Error as e:
            print(f"❌ Error inicializando pool: {e}")
            self._connection_pool = None
    
    def get_connection(self):
        """Obtener conexión del pool con manejo de errores"""
        if not self._connection_pool:
            self._init_pool()
            if not self._connection_pool:
                raise Exception("No se pudo inicializar el pool de conexiones")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = self._connection_pool.get_connection()
                
                # Verificar y reconectar si es necesario
                if not conn.is_connected():
                    conn.reconnect(attempts=3, delay=1)
                
                # Hacer ping para mantener la conexión activa
                conn.ping(reconnect=True, attempts=3, delay=1)
                
                return conn
                
            except Error as e:
                print(f"⚠️  Intento {attempt + 1} de conexión falló: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Esperar 1 segundo
                    continue
                else:
                    # Último intento: crear nueva conexión directa
                    try:
                        print("🔄 Intentando conexión directa...")
                        conn = mysql.connector.connect(**Config.DB_CONFIG)
                        print("✅ Conexión directa establecida")
                        return conn
                    except Error as e2:
                        raise Exception(f"❌ No se pudo conectar después de {max_retries} intentos: {e2}")
    
    def connect(self):
        """Alias para get_connection"""
        return self.get_connection()
    
    def test_connection(self):
        """Probar conexión"""
        try:
            conn = self.get_connection()
            if conn and conn.is_connected():
                cursor = conn.cursor()
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                cursor.close()
                conn.close()
                
                print(f"✅ MySQL {version}")
                print(f"📊 Tablas: {len(tables)}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error en test_connection: {e}")
            return False
    
    def disconnect(self):
        """Cerrar pool de conexiones"""
        try:
            if self._connection_pool:
                # El pool se cierra automáticamente cuando no hay referencias
                self._connection_pool = None
                print("🔌 Pool de conexiones cerrado")
        except:
            pass

# Instancia global
db = Database()