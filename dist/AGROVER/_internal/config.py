# config.py - CONFIGURACIÓN AGROVET YACUANQUER
import os
from pathlib import Path

class Config:
    # Ruta base
    BASE_DIR = Path(__file__).parent.absolute()
    
    # CONFIGURACIÓN MYSQL - AGROVET
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '12345',  # Tu contraseña
        'database': 'agrovet',  # Nombre de la BD
        'port': 3306,
        'charset': 'utf8mb4'
    }
    
    # EMPRESA - AGROVET YACUANQUER
    EMPRESA = {
        'nombre': 'AGROVET YACUANQUER',
        'telefono': '3217470975',
        'direccion': 'Yacuanquer, Nariño',
        'mensaje_pie': 'Sistema de Gestión Agrovet'
    }
    
    # MÉTODOS DE PAGO
    METODOS_PAGO = [
        'APARTADO'
        'CONTADO',
        'CRÉDITO',
        'NEQUI',
        'TRANSFERENCIA',
        'TRANSACCIÓN',
        'TARJETA'
    ]
    
    # CATEGORÍAS (sin números)
    CATEGORIAS = [
        'ANTIBIOTICOS',
        'BIOESTIMULANTES',
        'BIOLOGICOS',
        'COADYUVANTES',
        'CONCENTRADO AVES PRODUCCION',
        'CONCENTRADOS',
        'CONCENTRADOS GATOS',
        'CONCENTRADOS PERROS',
        'ENMIENDA',
        'FERTILIZANTES',
        'FUNGICIDAS',
        'HERBICIDAS',
        'INSECTICIDAS',
        'MAIZ',
        'MASCOTAS',
        'REGULADOR DE CRECIMIENTO',
        'REPUESTOS BOMBAS Y ESTACIONARIAS',
        'SALES GANADERAS',
        'SEMILLAS',
        'VETERINARIA'
    ]
    
    # PRESENTACIONES
    PRESENTACIONES = [
        'LITRO',
        'GALON',
        'KILO',
        'LIBRA',
        'UNIDAD',
        'PAQUETE',
        'CAJA',
        'SACO',
        'FRASCO',
        'AMPOLETA',
        'SOBRE',
        'BLOQUE'
    ]
    
    @classmethod
    def crear_directorios(cls):
        """Crear directorios necesarios"""
        dirs = [cls.BASE_DIR / 'data' / 'logs', cls.BASE_DIR / 'data' / 'backup_automatico']
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def formatear_moneda(cls, valor):
        """Formatear como moneda colombiana"""
        try:
            return f"${float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except:
            return "$0,00"

# Crear directorios
Config.crear_directorios()