"""Add observations and people present to daily cash closures."""

import argparse
import sys
from pathlib import Path

import mysql.connector

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import Config


def get_columns(cursor, schema):
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'cierre_caja'
        """,
        (schema,),
    )
    return {row[0] for row in cursor.fetchall()}


def main():
    parser = argparse.ArgumentParser(description='Add observations and people present to cash closures.')
    parser.add_argument('--apply', action='store_true', help='Apply migration.')
    args = parser.parse_args()

    connection = mysql.connector.connect(**Config.DB_CONFIG)
    cursor = connection.cursor()
    try:
        schema = Config.DB_CONFIG['database']
        columns = get_columns(cursor, schema)
        if not columns:
            raise RuntimeError('The cierre_caja table does not exist.')

        changes = {
            'observaciones': 'TEXT NULL',
            'responsables_presentes': 'VARCHAR(500) NULL',
        }
        missing = {name: definition for name, definition in changes.items() if name not in columns}

        for name, definition in missing.items():
            print(f'cierre_caja.{name}: missing')
            if args.apply:
                cursor.execute(f'ALTER TABLE cierre_caja ADD COLUMN `{name}` {definition}')
                print(f'cierre_caja.{name}: added')

        if missing and not args.apply:
            print('Inspection only. Re-run with --apply to add these columns.')
        elif not missing:
            print('cierre_caja observations: already up to date')
        else:
            connection.commit()
            print('cierre_caja observations: migration completed')
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == '__main__':
    main()
