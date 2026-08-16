# config.py - CONFIGURACIÓN AGROVET YACUANQUER
import os
from pathlib import Path

class Config:
    # Ruta base
    BASE_DIR = Path(__file__).parent.absolute()
    
    # CONFIGURACIÓN MYSQL - AGROVET
    db_name = 'AgroVet'  # Puede venir de cualquier parte
    db_name = db_name.lower()

    DB_CONFIG = {
        'host': 'localhost',
        'user': 'root',
        'password': '12345',
        'database': db_name,
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
        'TRANSACCIÓN',
        'TARJETA'
    ]

    IVA_PORCENTAJE = 0 


    PDF_OPTIONS = {
        'page-size': 'Letter',
        'margin-top': '0.25in',
        'margin-right': '0.25in',
        'margin-bottom': '0.25in',
        'margin-left': '0.25in',
        'encoding': "UTF-8",
        'no-outline': None
    }

    
    # CATEGORÍAS (sin números)
    CATEGORIAS = [
        'BIOESTIMULANTES',
        'BIOLOGICOS',
        'COADYUVANTES',
        'CONCENTRADOS',
        'ENMIENDA',
        'FERTILIZANTES',
        'FUNGICIDAS',
        'HERBICIDAS',
        'INSECTICIDAS',
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