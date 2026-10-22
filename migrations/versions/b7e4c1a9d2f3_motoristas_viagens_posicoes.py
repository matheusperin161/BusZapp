"""motoristas (RF23), viagens e posicoes

- driver → motoristas: renomeia colunas, adiciona CNH/telefone/status e cria um
  User (role='motorista') para cada motorista existente, levando e-mail e senha.
- route.active e stop_point.tempo_ate_proxima_min.
- novas tabelas viagens e posicoes.

Idempotente: o app roda db.create_all() ao subir, então as tabelas novas podem
já existir (vazias) quando este upgrade rodar.

Revision ID: b7e4c1a9d2f3
Revises: 6c9684a00d87
Create Date: 2026-10-21 23:00:00.000000

"""
import re
import secrets
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


revision = 'b7e4c1a9d2f3'
down_revision = '6c9684a00d87'
branch_labels = None
depends_on = None


def _tabelas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def _migrar_driver():
    bind = op.get_bind()
    tabelas = _tabelas()

    # create_all pode ter criado as tabelas novas antes do upgrade — só se estiverem vazias
    for nova in ('posicoes', 'viagens', 'motoristas'):
        if nova in tabelas:
            if bind.execute(sa.text(f'SELECT COUNT(*) FROM {nova}')).scalar():
                raise RuntimeError(f'Tabela {nova} já tem dados; migre manualmente.')
            op.drop_table(nova)

    op.rename_table('driver', 'motoristas')

    for indice in sa.inspect(bind).get_indexes('motoristas'):
        if indice['column_names'] == ['email']:
            op.drop_index(indice['name'], table_name='motoristas')

    with op.batch_alter_table('motoristas') as batch:
        batch.alter_column('name', new_column_name='nome', existing_type=sa.String(100), existing_nullable=False)
        batch.alter_column('cnh', new_column_name='cnh_numero', type_=sa.String(20),
                           existing_type=sa.String(11), existing_nullable=False)
        batch.alter_column('created_at', new_column_name='criado_em', existing_type=sa.DateTime(),
                           existing_nullable=False)
        batch.alter_column('bus_line', existing_type=sa.String(100), nullable=True)
        batch.alter_column('code', existing_type=sa.String(50), nullable=True)
        batch.add_column(sa.Column('usuario_id', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('cnh_categoria', sa.String(2), nullable=True))
        batch.add_column(sa.Column('cnh_validade', sa.Date(), nullable=True))
        batch.add_column(sa.Column('telefone', sa.String(20), nullable=True))
        batch.add_column(sa.Column('status', sa.String(10), nullable=False, server_default='ativo'))
        batch.add_column(sa.Column('atualizado_em', sa.DateTime(), nullable=True))

    # Cada motorista ganha um acesso de usuário com perfil motorista
    motoristas = bind.execute(sa.text(
        'SELECT id, nome, email, password, cpf, criado_em FROM motoristas')).mappings().all()
    for m in motoristas:
        email = (m['email'] or '').strip().lower()
        if bind.execute(sa.text('SELECT 1 FROM "user" WHERE email = :e'), {'e': email}).first():
            # e-mail já usado por um passageiro/admin: o acesso do motorista recebe um alias
            local, _, dominio = email.partition('@')
            email = f'{local}+motorista{m["id"]}@{dominio}'
            print(f'  ! motorista {m["id"]}: e-mail já existia em user; acesso criado como {email}')

        username, n = m['nome'][:70], 2
        while bind.execute(sa.text('SELECT 1 FROM "user" WHERE username = :u'), {'u': username}).first():
            username, n = f'{m["nome"][:70]} ({n})', n + 1

        senha = m['password'] or generate_password_hash(secrets.token_urlsafe(16))
        agora = m['criado_em'] or datetime.utcnow()
        bind.execute(sa.text(
            'INSERT INTO "user" (username, email, password, role, card_balance, email_verified, created_at) '
            "VALUES (:u, :e, :p, 'motorista', 0, :v, :c)"),
            {'u': username, 'e': email, 'p': senha, 'v': True, 'c': agora})
        usuario_id = bind.execute(sa.text('SELECT id FROM "user" WHERE email = :e'), {'e': email}).scalar()
        bind.execute(sa.text(
            'UPDATE motoristas SET usuario_id = :u, cpf = :cpf, atualizado_em = :a WHERE id = :id'),
            {'u': usuario_id, 'cpf': re.sub(r'\D', '', m['cpf'] or ''), 'a': agora, 'id': m['id']})

    with op.batch_alter_table('motoristas') as batch:
        batch.alter_column('usuario_id', existing_type=sa.Integer(), nullable=False)
        batch.alter_column('atualizado_em', existing_type=sa.DateTime(), nullable=False)
        batch.alter_column('cpf', type_=sa.String(11), existing_type=sa.String(14), existing_nullable=False)
        batch.create_unique_constraint('uq_motoristas_usuario_id', ['usuario_id'])
        batch.create_foreign_key('fk_motoristas_usuario_id', 'user', ['usuario_id'], ['id'])
        batch.drop_column('email')
        batch.drop_column('password')


def upgrade():
    if 'driver' in _tabelas():
        _migrar_driver()

    if 'active' not in _colunas('route'):
        with op.batch_alter_table('route') as batch:
            batch.add_column(sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))

    if 'tempo_ate_proxima_min' not in _colunas('stop_point'):
        with op.batch_alter_table('stop_point') as batch:
            batch.add_column(sa.Column('tempo_ate_proxima_min', sa.Float(), nullable=True))

    tabelas = _tabelas()
    if 'viagens' not in tabelas:
        op.create_table(
            'viagens',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('linha_id', sa.Integer(), sa.ForeignKey('route.id'), nullable=False),
            sa.Column('veiculo_id', sa.Integer(), sa.ForeignKey('vehicle.id'), nullable=False),
            sa.Column('motorista_id', sa.Integer(), sa.ForeignKey('motoristas.id'), nullable=False),
            sa.Column('sentido', sa.String(5), nullable=False),
            sa.Column('status', sa.String(12), nullable=False),
            sa.Column('iniciada_em', sa.DateTime(), nullable=True),
            sa.Column('finalizada_em', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_viagens_linha_id', 'viagens', ['linha_id'])
        op.create_index('ix_viagens_status', 'viagens', ['status'])
        ativa = sa.text("status = 'em_andamento'")
        op.create_index('uq_viagem_ativa_motorista', 'viagens', ['motorista_id'], unique=True,
                        postgresql_where=ativa, sqlite_where=ativa)
        op.create_index('uq_viagem_ativa_veiculo', 'viagens', ['veiculo_id'], unique=True,
                        postgresql_where=ativa, sqlite_where=ativa)

    if 'posicoes' not in tabelas:
        op.create_table(
            'posicoes',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('viagem_id', sa.Integer(), sa.ForeignKey('viagens.id', ondelete='CASCADE'), nullable=False),
            sa.Column('latitude', sa.Float(), nullable=False),
            sa.Column('longitude', sa.Float(), nullable=False),
            sa.Column('velocidade', sa.Float(), nullable=True),
            sa.Column('registrado_em', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_posicoes_viagem_registro', 'posicoes', ['viagem_id', 'registrado_em'])


def downgrade():
    raise NotImplementedError(
        'Migração de dados (driver → motoristas + usuários). Restaure o backup do banco para voltar.')
