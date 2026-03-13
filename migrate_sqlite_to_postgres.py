"""
migrate_sqlite_to_postgres.py
Migra todos os dados do banco SQLite para o PostgreSQL configurado em DATABASE_URL.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'src', 'instance', 'app.db')
PG_URL = os.getenv('DATABASE_URL', '')

if not PG_URL or not PG_URL.startswith('postgresql'):
    print('❌  DATABASE_URL não aponta para PostgreSQL. Verifique o .env.')
    sys.exit(1)

if not os.path.exists(SQLITE_PATH):
    print(f'❌  Banco SQLite não encontrado em: {SQLITE_PATH}')
    sys.exit(1)

from sqlalchemy import create_engine, text, inspect

sqlite_engine = create_engine(f'sqlite:///{SQLITE_PATH}')
pg_engine = create_engine(PG_URL)

from src.models import db
from src.models.user import User, Transaction, BusRoute, BusLocation, Notification, Driver, Rating, Vehicle
from src.models.tracking import Route, StopPoint, BusSchedule

# Ordem respeita chaves estrangeiras
TABLES_IN_ORDER = [
    'bus_route',
    'route',
    'driver',
    'user',
    'vehicle',
    'stop_point',
    'bus_schedule',
    'bus_location',
    'transaction',
    'notification',
    'rating',
]

# Colunas boolean por tabela (SQLite guarda como 0/1)
BOOLEAN_COLUMNS = {
    'bus_route':    ['active'],
    'notification': ['read'],
    'bus_schedule': ['active'],
}


def create_tables_in_postgres():
    print('📦  Criando tabelas no PostgreSQL (se não existirem)...')
    db.metadata.create_all(pg_engine)
    print('    ✅  Tabelas OK.')


def clear_tables():
    print('\n🧹  Limpando dados existentes no PostgreSQL...')
    with pg_engine.begin() as conn:
        conn.execute(text('SET session_replication_role = replica'))
        for table in reversed(TABLES_IN_ORDER):
            try:
                conn.execute(text(f'DELETE FROM "{table}"'))
                print(f'    🗑️   {table} limpa.')
            except Exception as e:
                print(f'    ⚠️   {table}: {e}')
        conn.execute(text('SET session_replication_role = DEFAULT'))


def convert_row(table_name, row):
    bool_cols = BOOLEAN_COLUMNS.get(table_name, [])
    result = dict(row)
    for col in bool_cols:
        if col in result and result[col] is not None:
            result[col] = bool(result[col])
    return result


def get_valid_ids(table_name):
    with pg_engine.connect() as conn:
        return {r[0] for r in conn.execute(text(f'SELECT id FROM "{table_name}"')).fetchall()}


def migrate_table(table_name):
    # Verifica se a tabela existe no SQLite
    with sqlite_engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
    if table_name not in tables:
        print(f'    ⚪  {table_name}: não existe no SQLite, pulando.')
        return

    with sqlite_engine.connect() as sqlite_conn:
        rows = sqlite_conn.execute(text(f'SELECT * FROM "{table_name}"')).mappings().all()

    if not rows:
        print(f'    ⚪  {table_name}: vazia, pulando.')
        return

    data = [convert_row(table_name, row) for row in rows]

    # Filtros de FK
    if table_name == 'bus_location':
        valid_routes = get_valid_ids('bus_route')
        before = len(data)
        data = [r for r in data if r.get('route_id') is None or r['route_id'] in valid_routes]
        if before - len(data):
            print(f'    ⚠️   bus_location: {before - len(data)} registro(s) ignorado(s) (route_id inválido).')

    if table_name == 'stop_point':
        valid_routes = get_valid_ids('route')
        before = len(data)
        data = [r for r in data if r.get('route_id') in valid_routes]
        if before - len(data):
            print(f'    ⚠️   stop_point: {before - len(data)} registro(s) ignorado(s) (route_id inválido).')

    if table_name == 'bus_schedule':
        valid_routes = get_valid_ids('route')
        before = len(data)
        data = [r for r in data if r.get('route_id') in valid_routes]
        if before - len(data):
            print(f'    ⚠️   bus_schedule: {before - len(data)} registro(s) ignorado(s) (route_id inválido).')

    if not data:
        print(f'    ⚪  {table_name}: nenhum dado válido.')
        return

    columns = list(data[0].keys())
    col_str = ', '.join(f'"{c}"' for c in columns)
    placeholders = ', '.join(f':{c}' for c in columns)

    with pg_engine.begin() as pg_conn:
        pg_conn.execute(text(f'INSERT INTO "{table_name}" ({col_str}) VALUES ({placeholders})'), data)
    print(f'    ✅  {table_name}: {len(data)} registro(s) inserido(s).')


def reset_sequences():
    print('\n🔄  Resetando sequences de ID...')
    inspector = inspect(pg_engine)
    with pg_engine.begin() as conn:
        for table in TABLES_IN_ORDER:
            if not inspector.has_table(table):
                continue
            try:
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM \"{table}\"), 0) + 1, false)"
                ))
                print(f'    ✅  sequence de {table} resetada.')
            except Exception as e:
                print(f'    ⚠️   {table}: não foi possível resetar sequence — {e}')


def main():
    print('=' * 55)
    print('  BusZapp — Migração SQLite → PostgreSQL')
    print('=' * 55)

    create_tables_in_postgres()
    clear_tables()

    print('\n📤  Migrando dados...')
    for table in TABLES_IN_ORDER:
        try:
            migrate_table(table)
        except Exception as exc:
            print(f'    ❌  Erro na tabela {table}: {exc}')

    reset_sequences()

    print('\n🎉  Migração concluída!')
    print('    Verifique os dados no pgAdmin.')


if __name__ == '__main__':
    main()
