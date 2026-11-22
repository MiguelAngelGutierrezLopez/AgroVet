"""Create the daily cash-close snapshot table."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cierre_caja (
    id INT NOT NULL AUTO_INCREMENT,
    fecha_cierre DATE NOT NULL,
    fecha_inicio_movimientos DATE NOT NULL,
    saldo_inicial_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    saldo_inicial_banco DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ingresos_manuales_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ventas_contado_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    anticipos_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    abonos_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    egresos_manuales_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ingresos_banco_registrados DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    ajuste_banco_externo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    saldo_final_efectivo DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    saldo_final_banco DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_final DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cierre_caja_fecha (fecha_cierre),
    KEY idx_cierre_caja_fecha (fecha_inicio_movimientos, fecha_cierre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
"""


def main():
    parser = argparse.ArgumentParser(description='Create the daily cash-close table.')
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Create the table. Without this flag, only inspect the schema.',
    )
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'cierre_caja'
            """,
            (Config.DB_CONFIG['database'],),
        )
        exists = cursor.fetchone() is not None
        if exists:
            print('cierre_caja: already exists')
            return

        print('cierre_caja: missing')
        if not args.apply:
            print('Inspection only. Re-run with --apply to create the table.')
            return

        cursor.execute(CREATE_TABLE_SQL)
        connection.commit()
        print('cierre_caja: created')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()