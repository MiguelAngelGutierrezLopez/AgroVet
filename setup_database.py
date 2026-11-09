"""
setup_database.py
Script para crear la base de datos y tablas a partir de AgroVet.sql
Ejecuta el SQL en MySQL usando las credenciales de `config.Config`.
"""
import os
import sys
import runpy
import argparse
import logging
from config import Config
import mysql.connector
from mysql.connector import Error

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def load_sql(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def get_server_connection():
    cfg = Config.DB_CONFIG.copy()
    # Conectar al servidor sin seleccionar una base de datos
    cfg.pop('database', None)
    try:
        conn = mysql.connector.connect(**cfg)
        return conn
    except Error as e:
        logger.error(f"No se pudo conectar al servidor MySQL: {e}")
        raise


def apply_sql(conn, sql):
    cursor = conn.cursor()
    try:
        logger.info("Ejecutando sentencias SQL... Esto puede tardar algunos segundos...")
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        for statement in statements:
            if statement:
                cursor.execute(statement)
        conn.commit()
        logger.info("SQL aplicado correctamente.")
    except Error as e:
        conn.rollback()
        logger.error(f"Error al aplicar SQL: {e}")
        raise
    finally:
        cursor.close()


def apply_product_history_migrations():
    migrations = (
        '001_add_product_history_columns.py',
        '002_backfill_product_history.py',
        '003_allow_product_deletion.py',
    )
    original_argv = sys.argv[:]
    try:
        for migration_name in migrations:
            migration_path = resource_path(os.path.join('migrations', migration_name))
            if not os.path.isfile(migration_path):
                raise FileNotFoundError(f'No se encontró la migración: {migration_path}')

            logger.info(f'Aplicando migración {migration_name}...')
            sys.argv = [migration_path, '--apply']
            runpy.run_path(migration_path, run_name='__main__')
    finally:
        sys.argv = original_argv


def main():
    parser = argparse.ArgumentParser(description='Crear base de datos AgroVet desde AgroVet.sql')
    parser.add_argument('--file', '-f', default=resource_path('AgroVet.sql'), help='Ruta al archivo .sql')
    args = parser.parse_args()

    sql_path = args.file
    if not os.path.exists(sql_path):
        logger.error(f"No se encontró el archivo SQL: {sql_path}")
        sys.exit(1)

    sql = load_sql(sql_path)

    try:
        conn = get_server_connection()
    except Exception:
        sys.exit(1)

    try:
        apply_sql(conn, sql)
        apply_product_history_migrations()
    finally:
        try:
            conn.close()
        except:
            pass


if __name__ == '__main__':
    main()
