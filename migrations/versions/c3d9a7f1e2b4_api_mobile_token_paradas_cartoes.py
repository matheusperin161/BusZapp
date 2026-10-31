"""API para o app mobile: token Bearer, paradas por sentido e cartões

- user.token_version (revogação dos tokens Bearer).
- paradas + linha_parada: cada stop_point vira uma Parada e uma associação 'ida'
  com a mesma ordem (renumerada 1..n). A volta usa a ida ao contrário até ser cadastrada.
- cartoes: um por usuário, copiado de user.card_* (saldo em centavos).
- transaction.cartao_id, preenchido com o cartão do usuário.

Idempotente: o app roda db.create_all() ao subir, então as tabelas novas podem
já existir (vazias) quando este upgrade rodar. As colunas e a tabela antigas
(user.card_*, stop_point) ficam no banco, sem uso.

Revision ID: c3d9a7f1e2b4
Revises: b7e4c1a9d2f3
Create Date: 2026-10-31 12:00:00.000000

"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = 'c3d9a7f1e2b4'
down_revision = 'b7e4c1a9d2f3'
branch_labels = None
depends_on = None


def _tabelas():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _colunas(tabela):
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns(tabela)}


def _vazia(tabela):
    return not op.get_bind().execute(sa.text(f'SELECT COUNT(*) FROM {tabela}')).scalar()


def _criar_tabelas_paradas():
    tabelas = _tabelas()
    if 'paradas' not in tabelas:
        op.create_table(
            'paradas',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('nome', sa.String(120), nullable=False),
            sa.Column('endereco', sa.String(255), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=False),
            sa.Column('longitude', sa.Float(), nullable=False),
            sa.Column('status', sa.String(10), nullable=False, server_default='ativa'),
            sa.Column('criado_em', sa.DateTime(), nullable=False),
        )
    if 'linha_parada' not in tabelas:
        op.create_table(
            'linha_parada',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('linha_id', sa.Integer(), sa.ForeignKey('route.id', ondelete='CASCADE'), nullable=False),
            sa.Column('parada_id', sa.Integer(), sa.ForeignKey('paradas.id'), nullable=False),
            sa.Column('sentido', sa.String(5), nullable=False),
            sa.Column('ordem', sa.Integer(), nullable=False),
            sa.Column('tempo_estimado_minutos', sa.Float(), nullable=True),
            sa.UniqueConstraint('linha_id', 'sentido', 'parada_id', name='uq_linha_sentido_parada'),
        )
        op.create_index('ix_linha_parada_linha_id', 'linha_parada', ['linha_id'])


def _migrar_stop_points():
    if 'stop_point' not in _tabelas() or not (_vazia('paradas') and _vazia('linha_parada')):
        return
    bind = op.get_bind()
    agora = datetime.utcnow()
    pontos = bind.execute(sa.text(
        'SELECT id, route_id, name, latitude, longitude, "order", tempo_ate_proxima_min '
        'FROM stop_point ORDER BY route_id, "order", id')).mappings().all()
    ordem_por_linha = {}
    for p in pontos:
        parada_id = bind.execute(sa.text(
            'INSERT INTO paradas (nome, endereco, latitude, longitude, status, criado_em) '
            "VALUES (:n, NULL, :lat, :lon, 'ativa', :c) RETURNING id"),
            {'n': p['name'], 'lat': p['latitude'], 'lon': p['longitude'], 'c': agora}).scalar()
        ordem = ordem_por_linha[p['route_id']] = ordem_por_linha.get(p['route_id'], 0) + 1
        bind.execute(sa.text(
            'INSERT INTO linha_parada (linha_id, parada_id, sentido, ordem, tempo_estimado_minutos) '
            "VALUES (:l, :p, 'ida', :o, :t)"),
            {'l': p['route_id'], 'p': parada_id, 'o': ordem, 't': p['tempo_ate_proxima_min']})
    print(f'  paradas: {len(pontos)} stop_point copiados para paradas/linha_parada')


def _criar_tabela_cartoes():
    if 'cartoes' in _tabelas():
        return
    op.create_table(
        'cartoes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('numero', sa.String(25), nullable=True),
        sa.Column('titular', sa.String(100), nullable=True),
        sa.Column('tipo', sa.String(30), nullable=True),
        sa.Column('saldo_centavos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(10), nullable=False, server_default='ativo'),
        sa.Column('criado_em', sa.DateTime(), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('usuario_id', name='uq_cartoes_usuario_id'),
        sa.UniqueConstraint('numero', name='uq_cartoes_numero'),
        sa.CheckConstraint('saldo_centavos >= 0', name='ck_cartoes_saldo_nao_negativo'),
    )


def _migrar_cartoes():
    if not _vazia('cartoes'):
        return
    bind = op.get_bind()
    agora = datetime.utcnow()
    usuarios = bind.execute(sa.text(
        'SELECT id, card_number, card_holder, card_type, card_balance FROM "user" '
        "WHERE (card_number IS NOT NULL AND TRIM(card_number) <> '') OR card_balance <> 0 "
        'ORDER BY id')).mappings().all()
    numeros = set()
    for u in usuarios:
        numero = (u['card_number'] or '').strip() or None
        if numero in numeros:
            print(f'  ! usuário {u["id"]}: número de cartão {numero} repetido; cartão criado sem número')
            numero = None
        numeros.add(numero)
        saldo = round((u['card_balance'] or 0) * 100)
        if saldo < 0:
            print(f'  ! usuário {u["id"]}: saldo negativo ({u["card_balance"]}) zerado')
            saldo = 0
        bind.execute(sa.text(
            'INSERT INTO cartoes (usuario_id, numero, titular, tipo, saldo_centavos, status, criado_em, atualizado_em) '
            "VALUES (:u, :n, :h, :t, :s, 'ativo', :c, :c)"),
            {'u': u['id'], 'n': numero, 'h': u['card_holder'], 't': u['card_type'], 's': saldo, 'c': agora})
    print(f'  cartões: {len(usuarios)} copiados de user.card_*')


def upgrade():
    if 'token_version' not in _colunas('user'):
        with op.batch_alter_table('user') as batch:
            batch.add_column(sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))

    _criar_tabelas_paradas()
    _migrar_stop_points()

    _criar_tabela_cartoes()
    _migrar_cartoes()

    if 'cartao_id' not in _colunas('transaction'):
        with op.batch_alter_table('transaction') as batch:
            batch.add_column(sa.Column('cartao_id', sa.Integer(), nullable=True))
            batch.create_foreign_key('fk_transaction_cartao_id', 'cartoes', ['cartao_id'], ['id'],
                                     ondelete='SET NULL')
            batch.create_index('ix_transaction_cartao_id', ['cartao_id'])
    op.get_bind().execute(sa.text(
        'UPDATE "transaction" SET cartao_id = (SELECT c.id FROM cartoes c WHERE c.usuario_id = "transaction".user_id) '
        'WHERE cartao_id IS NULL'))


def downgrade():
    raise NotImplementedError(
        'Migração de dados (stop_point → paradas, user.card_* → cartoes). Restaure o backup do banco para voltar.')
