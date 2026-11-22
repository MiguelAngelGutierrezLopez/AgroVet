"""Create bank adjustments and keep closure editing traceable."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cierre_caja_ajuste_banco (
    id INT NOT NULL AUTO_INCREMENT,
    fecha_cierre DATE NOT NULL,
    tipo ENUM('entrada', 'retiro') NOT NULL,
    monto DECIMAL(12,2) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    referencia VARCHAR(100) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_cierre_caja_ajuste_fecha (fecha_cierre),
    CONSTRAINT fk_cierre_caja_ajuste
        FOREIGN KEY (fecha_cierre) REFERENCES cierre_caja(fecha_cierre)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci
"""


def main():
    parser = argparse.ArgumentParser(description='Create bank adjustments for cash closures.')
    parser.add_argument('--apply', action='store_true', help='Apply migration.')
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'cierre_caja_ajuste_banco'
            """,
            (Config.DB_CONFIG['database'],),
        )
        exists = cursor.fetchone() is not None
        print('cierre_caja_ajuste_banco: ' + ('already exists' if exists else 'missing'))

        if exists:
            return
        if not args.apply:
            print('Inspection only. Re-run with --apply to create the table.')
            return

        cursor.execute(CREATE_TABLE_SQL)
        connection.commit()
        print('cierre_caja_ajuste_banco: created')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()
