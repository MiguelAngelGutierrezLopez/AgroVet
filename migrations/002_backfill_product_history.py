"""Backfill product snapshots for existing sales and supplier purchases."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


CHECKS = {
    'detalle_venta': {
        'orphans': """
            SELECT COUNT(*)
            FROM detalle_venta dv
            LEFT JOIN productos p ON p.id = dv.id_producto
            WHERE p.id IS NULL
        """,
        'missing': """
            SELECT COUNT(*)
            FROM detalle_venta
            WHERE producto_id_historico IS NULL
               OR producto_nombre_historico IS NULL
               OR producto_categoria_historica IS NULL
               OR costo_unitario_historico IS NULL
        """,
    },
    'compras_proveedor': {
        'orphans': """
            SELECT COUNT(*)
            FROM compras_proveedor cp
            LEFT JOIN productos p ON p.id = cp.producto_id
            WHERE p.id IS NULL
        """,
        'missing': """
            SELECT COUNT(*)
            FROM compras_proveedor
            WHERE producto_id_historico IS NULL
               OR producto_nombre_historico IS NULL
               OR producto_categoria_historica IS NULL
        """,
    },
}


BACKFILL_SQL = {
    'detalle_venta': """
        UPDATE detalle_venta dv
        JOIN productos p ON p.id = dv.id_producto
        SET dv.producto_id_historico = COALESCE(
                dv.producto_id_historico, dv.id_producto
            ),
            dv.producto_nombre_historico = COALESCE(
                dv.producto_nombre_historico, p.nombre
            ),
            dv.producto_categoria_historica = COALESCE(
                dv.producto_categoria_historica, p.categoria
            ),
            dv.producto_presentacion_historica = COALESCE(
                dv.producto_presentacion_historica, p.presentacion
            ),
            dv.costo_unitario_historico = COALESCE(
                dv.costo_unitario_historico, p.precio_costo, 0
            )
        WHERE dv.producto_id_historico IS NULL
           OR dv.producto_nombre_historico IS NULL
           OR dv.producto_categoria_historica IS NULL
           OR dv.producto_presentacion_historica IS NULL
           OR dv.costo_unitario_historico IS NULL
    """,
    'compras_proveedor': """
        UPDATE compras_proveedor cp
        JOIN productos p ON p.id = cp.producto_id
        SET cp.producto_id_historico = COALESCE(
                cp.producto_id_historico, cp.producto_id
            ),
            cp.producto_nombre_historico = COALESCE(
                cp.producto_nombre_historico, p.nombre
            ),
            cp.producto_categoria_historica = COALESCE(
                cp.producto_categoria_historica, p.categoria
            ),
            cp.producto_presentacion_historica = COALESCE(
                cp.producto_presentacion_historica, p.presentacion
            )
        WHERE cp.producto_id_historico IS NULL
           OR cp.producto_nombre_historico IS NULL
           OR cp.producto_categoria_historica IS NULL
           OR cp.producto_presentacion_historica IS NULL
    """,
}


def get_count(cursor, query):
    cursor.execute(query)
    return cursor.fetchone()[0]


def inspect(cursor):
    results = {}
    for table, checks in CHECKS.items():
        orphans = get_count(cursor, checks['orphans'])
        missing = get_count(cursor, checks['missing'])
        results[table] = {'orphans': orphans, 'missing': missing}
        print(f'{table}: missing_snapshots={missing}, orphan_rows={orphans}')
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Backfill product-history snapshots from the current catalog.'
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Write missing snapshots. Without this flag, only inspect the data.',
    )
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        before = inspect(cursor)
        orphan_tables = [
            table for table, counts in before.items() if counts['orphans']
        ]
        if orphan_tables:
            raise RuntimeError(
                'Cannot backfill rows without a matching product: '
                + ', '.join(orphan_tables)
            )

        if not args.apply:
            print('Inspection only. Re-run with --apply to backfill missing snapshots.')
            return

        connection.commit()
        connection.start_transaction()
        updated = {}
        for table, query in BACKFILL_SQL.items():
            cursor.execute(query)
            updated[table] = cursor.rowcount

        after = inspect(cursor)
        remaining = [
            table for table, counts in after.items() if counts['missing']
        ]
        if remaining:
            raise RuntimeError(
                'Snapshots remain incomplete for: ' + ', '.join(remaining)
            )

        connection.commit()
        for table, count in updated.items():
            print(f'{table}: rows_backfilled={count}')
        print('Backfill completed and verified.')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()