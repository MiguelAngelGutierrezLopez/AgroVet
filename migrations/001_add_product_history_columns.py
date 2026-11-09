"""Add nullable snapshot columns before migrating product history."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


COLUMNS = {
    'detalle_venta': {
        'producto_id_historico': 'INT NULL',
        'producto_nombre_historico': 'VARCHAR(100) NULL',
        'producto_categoria_historica': 'VARCHAR(50) NULL',
        'producto_presentacion_historica': 'VARCHAR(50) NULL',
        'costo_unitario_historico': 'DECIMAL(12,2) NULL',
    },
    'compras_proveedor': {
        'producto_id_historico': 'INT NULL',
        'producto_nombre_historico': 'VARCHAR(100) NULL',
        'producto_categoria_historica': 'VARCHAR(50) NULL',
        'producto_presentacion_historica': 'VARCHAR(50) NULL',
    },
}


def get_missing_columns(cursor, schema):
    missing = {}

    for table, columns in COLUMNS.items():
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """,
            (schema, table),
        )
        existing = {row[0] for row in cursor.fetchall()}
        if not existing:
            raise RuntimeError(f'Required table is missing: {table}')

        missing[table] = {
            name: definition
            for name, definition in columns.items()
            if name not in existing
        }

    return missing


def main():
    parser = argparse.ArgumentParser(
        description='Add nullable product-history snapshot columns.'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply missing columns. Without this flag, only inspect the schema.',
    )
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        missing = get_missing_columns(cursor, Config.DB_CONFIG['database'])
        changes_found = False

        for table, columns in missing.items():
            if not columns:
                print(f'{table}: already up to date')
                continue

            changes_found = True
            for name, definition in columns.items():
                if args.apply:
                    cursor.execute(
                        f'ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}'
                    )
                    print(f'Added {table}.{name}')
                else:
                    print(f'Missing {table}.{name} (would add {definition})')

        if args.apply:
            connection.commit()
        elif not changes_found:
            print('Schema is already up to date.')
        else:
            print('Inspection only. Re-run with --apply to add these columns.')
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()