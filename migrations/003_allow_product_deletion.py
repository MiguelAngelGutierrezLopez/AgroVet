"""Detach historical rows from the live catalog before product deletion."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


TABLES = {
    'detalle_venta': {
        'reference_column': 'id_producto',
        'foreign_key': 'fk_detalle_venta_producto_actual',
        'reference_definition': 'INT NULL',
        'snapshot_definitions': {
            'producto_id_historico': 'INT NOT NULL',
            'producto_nombre_historico': 'VARCHAR(100) NOT NULL',
            'producto_categoria_historica': 'VARCHAR(50) NOT NULL',
            'producto_presentacion_historica': 'VARCHAR(50) NULL',
            'costo_unitario_historico': 'DECIMAL(12,2) NOT NULL DEFAULT 0.00',
        },
        'missing_query': """
            SELECT COUNT(*)
            FROM detalle_venta
            WHERE producto_id_historico IS NULL
               OR producto_nombre_historico IS NULL
               OR producto_categoria_historica IS NULL
               OR costo_unitario_historico IS NULL
        """,
        'index': 'idx_detalle_venta_producto_historico',
    },
    'compras_proveedor': {
        'reference_column': 'producto_id',
        'foreign_key': 'fk_compras_producto_actual',
        'reference_definition': 'INT NULL',
        'snapshot_definitions': {
            'producto_id_historico': 'INT NOT NULL',
            'producto_nombre_historico': 'VARCHAR(100) NOT NULL',
            'producto_categoria_historica': 'VARCHAR(50) NOT NULL',
            'producto_presentacion_historica': 'VARCHAR(50) NULL',
        },
        'missing_query': """
            SELECT COUNT(*)
            FROM compras_proveedor
            WHERE producto_id_historico IS NULL
               OR producto_nombre_historico IS NULL
               OR producto_categoria_historica IS NULL
        """,
        'index': 'idx_compras_producto_historico',
    },
}


def get_missing_count(cursor, query):
    cursor.execute(query)
    return cursor.fetchone()[0]


def get_product_foreign_keys(cursor, schema, table, column):
    cursor.execute(
        """
        SELECT kcu.CONSTRAINT_NAME, rc.DELETE_RULE
        FROM information_schema.KEY_COLUMN_USAGE AS kcu
        JOIN information_schema.REFERENTIAL_CONSTRAINTS AS rc
          ON rc.CONSTRAINT_SCHEMA = kcu.CONSTRAINT_SCHEMA
         AND rc.TABLE_NAME = kcu.TABLE_NAME
         AND rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
        WHERE kcu.TABLE_SCHEMA = %s
          AND kcu.TABLE_NAME = %s
          AND kcu.COLUMN_NAME = %s
          AND kcu.REFERENCED_TABLE_NAME = 'productos'
        """,
        (schema, table, column),
    )
    return cursor.fetchall()


def index_exists(cursor, schema, table, index):
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
        LIMIT 1
        """,
        (schema, table, index),
    )
    return cursor.fetchone() is not None


def inspect(cursor, schema):
    result = {}
    for table, definition in TABLES.items():
        missing = get_missing_count(cursor, definition['missing_query'])
        foreign_keys = get_product_foreign_keys(
            cursor, schema, table, definition['reference_column']
        )
        final_key = (
            len(foreign_keys) == 1
            and foreign_keys[0][0] == definition['foreign_key']
            and foreign_keys[0][1] == 'SET NULL'
        )
        result[table] = {
            'missing_snapshots': missing,
            'foreign_keys': foreign_keys,
            'final_foreign_key': final_key,
            'index_exists': index_exists(
                cursor, schema, table, definition['index']
            ),
        }
        print(
            f"{table}: missing_snapshots={missing}, "
            f"foreign_keys={foreign_keys}, "
            f"historical_index={result[table]['index_exists']}"
        )
    return result


def apply_table(cursor, schema, table, definition, state):
    if not state['final_foreign_key']:
        for constraint_name, _ in state['foreign_keys']:
            cursor.execute(
                f"ALTER TABLE `{table}` DROP FOREIGN KEY `{constraint_name}`"
            )
            print(f'Dropped {table}.{constraint_name}')

    cursor.execute(
        f"ALTER TABLE `{table}` MODIFY COLUMN "
        f"`{definition['reference_column']}` {definition['reference_definition']}"
    )
    for column, column_definition in definition['snapshot_definitions'].items():
        cursor.execute(
            f"ALTER TABLE `{table}` MODIFY COLUMN `{column}` {column_definition}"
        )

    if not state['index_exists']:
        cursor.execute(
            f"ALTER TABLE `{table}` ADD KEY `{definition['index']}` "
            "(`producto_id_historico`)"
        )
        print(f'Added index {table}.{definition["index"]}')

    if not state['final_foreign_key']:
        update_rule = ' ON UPDATE CASCADE' if table == 'compras_proveedor' else ''
        cursor.execute(
            f"ALTER TABLE `{table}` ADD CONSTRAINT "
            f"`{definition['foreign_key']}` "
            f"FOREIGN KEY (`{definition['reference_column']}`) "
            f"REFERENCES `productos` (`id`){update_rule} ON DELETE SET NULL"
        )
        print(f'Added {table}.{definition["foreign_key"]} with ON DELETE SET NULL')


def main():
    parser = argparse.ArgumentParser(
        description='Allow physical product deletion without deleting historical rows.'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply the constraint changes. Without this flag, only inspect.',
    )
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        schema = Config.DB_CONFIG['database']
        state = inspect(cursor, schema)
        incomplete = [
            table
            for table, details in state.items()
            if details['missing_snapshots']
        ]
        if incomplete:
            raise RuntimeError(
                'Snapshots must be complete before changing foreign keys: '
                + ', '.join(incomplete)
            )

        if not args.apply:
            print('Inspection only. Re-run with --apply to change foreign keys.')
            return

        for table, definition in TABLES.items():
            apply_table(cursor, schema, table, definition, state[table])
        connection.commit()

        final_state = inspect(cursor, schema)
        if any(not details['final_foreign_key'] for details in final_state.values()):
            raise RuntimeError('Final ON DELETE SET NULL constraints were not verified.')
        print('Product deletion constraints applied and verified.')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()