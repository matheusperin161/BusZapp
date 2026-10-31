"""Cartão de transporte para o app mobile (CA06): um cartão por usuário, saldo em centavos."""
import re
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from src.extensions import limiter
from src.models import db
from src.models.user import Cartao, Transaction, CARD_TYPES, CARTAO_STATUSES
from src.routes.card import VALID_PAYMENT_METHODS, _build_payment_info
from src.services.cartao_service import cartao_do_usuario, creditar
from src.services.notification_service import create_notification
from src.utils.auth import admin_required, login_required

cartoes_bp = Blueprint('cartoes', __name__, url_prefix='/api')

NUMERO_CARTAO = re.compile(r'^\d{8,16}$')
RECARGA_MAX_CENTAVOS = 100_000  # R$ 1.000,00 por recarga


def _cartao_do_dono(cartao_id):
    """(cartão, None) ou (None, resposta de erro): 404 inexistente, 403 de outro usuário."""
    cartao = db.session.get(Cartao, cartao_id)
    if not cartao:
        return None, (jsonify({'error': 'Cartão não encontrado'}), 404)
    if cartao.usuario_id != g.user.id:
        return None, (jsonify({'error': 'Este cartão pertence a outro usuário'}), 403)
    return cartao, None


@cartoes_bp.route('/cartoes', methods=['GET'])
@login_required
def meus_cartoes():
    cartao = g.user.cartao
    return jsonify([cartao.to_dict()] if cartao else [])


@cartoes_bp.route('/cartoes/<int:cartao_id>', methods=['GET'])
@login_required
def obter_cartao(cartao_id):
    cartao, erro = _cartao_do_dono(cartao_id)
    return erro or jsonify(cartao.to_dict())


@cartoes_bp.route('/cartoes', methods=['POST'])
@login_required
@limiter.limit('10 per hour')  # dificulta descobrir números já cadastrados por tentativa
def cadastrar_cartao():
    data = request.get_json() or {}
    numero = re.sub(r'\D', '', str(data.get('numero') or ''))
    titular = str(data.get('titular') or '').strip() or None
    tipo = str(data.get('tipo') or '').strip().lower() or None

    if not NUMERO_CARTAO.match(numero):
        return jsonify({'error': 'Número do cartão deve ter de 8 a 16 dígitos'}), 400
    if tipo and tipo not in CARD_TYPES:
        return jsonify({'error': f'Tipo inválido. Use: {", ".join(CARD_TYPES)}'}), 400

    user = g.user
    if user.cartao and user.cartao.numero:
        return jsonify({'error': 'Você já possui um cartão cadastrado. Cada usuário pode ter apenas 1 cartão.'}), 409
    if Cartao.query.filter_by(numero=numero).first():
        return jsonify({'error': 'Este número de cartão já está cadastrado.'}), 409

    # Quem recarregou pelo web antes de cadastrar já tem um cartão sem número (com o saldo)
    cartao = cartao_do_usuario(user, criar=True)
    cartao.numero, cartao.titular, cartao.tipo = numero, titular, tipo
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Este número de cartão já está cadastrado.'}), 409

    create_notification(user.id, 'Cartão Cadastrado', f'Cartão final {numero[-4:]} cadastrado com sucesso.')
    return jsonify(cartao.to_dict()), 201


@cartoes_bp.route('/cartoes/<int:cartao_id>/bloquear', methods=['POST'])
@login_required
def bloquear_cartao(cartao_id):
    cartao, erro = _cartao_do_dono(cartao_id)
    if erro:
        return erro
    if cartao.status == 'bloqueado':
        return jsonify({'error': 'Cartão já está bloqueado'}), 409
    cartao.status = 'bloqueado'
    db.session.commit()
    return jsonify(cartao.to_dict())


@cartoes_bp.route('/cartoes/<int:cartao_id>/recarga', methods=['POST'])
@login_required
def recarregar_cartao(cartao_id):
    cartao, erro = _cartao_do_dono(cartao_id)
    if erro:
        return erro

    data = request.get_json() or {}
    valor = data.get('valor_centavos')
    metodo = data.get('payment_method', 'pix')
    if not isinstance(valor, int) or isinstance(valor, bool) or not (0 < valor <= RECARGA_MAX_CENTAVOS):
        return jsonify({'error': f'valor_centavos deve ser um inteiro entre 1 e {RECARGA_MAX_CENTAVOS}'}), 400
    if metodo not in VALID_PAYMENT_METHODS:
        return jsonify({'error': f'Método de pagamento inválido. Use: {", ".join(VALID_PAYMENT_METHODS)}'}), 400
    if cartao.status != 'ativo':
        return jsonify({'error': 'Cartão bloqueado não pode ser recarregado'}), 409

    reais = valor / 100
    pagamento = _build_payment_info(metodo, f'{g.user.id}_{int(datetime.utcnow().timestamp())}', reais)
    transacao = creditar(cartao, valor, f'Recarga via {pagamento["method"]} - R$ {reais:.2f}')
    if not transacao:
        return jsonify({'error': 'Cartão bloqueado não pode ser recarregado'}), 409

    create_notification(g.user.id, 'Recarga Realizada',
                        f'Recarga de R$ {reais:.2f} via {pagamento["method"]}. Novo saldo: R$ {cartao.saldo:.2f}.')
    return jsonify({'cartao': cartao.to_dict(), 'transacao': transacao.to_dict(), 'pagamento': pagamento}), 201


@cartoes_bp.route('/cartoes/<int:cartao_id>/transacoes', methods=['GET'])
@login_required
def extrato(cartao_id):
    cartao, erro = _cartao_do_dono(cartao_id)
    if erro:
        return erro
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    pagina = (Transaction.query.filter_by(cartao_id=cartao.id)
              .order_by(Transaction.created_at.desc(), Transaction.id.desc())
              .paginate(page=page, per_page=per_page, error_out=False))
    return jsonify({
        'itens': [t.to_dict() for t in pagina.items],
        'page': pagina.page,
        'per_page': pagina.per_page,
        'total': pagina.total,
    })


@cartoes_bp.route('/admin/cartoes', methods=['GET'])
@admin_required
def listar_cartoes_admin():
    """Somente leitura (CA06.5/CA06.7)."""
    status = request.args.get('status')
    query = Cartao.query.order_by(Cartao.criado_em.desc())
    if status:
        if status not in CARTAO_STATUSES:
            return jsonify({'error': f'Status inválido. Use: {", ".join(CARTAO_STATUSES)}'}), 400
        query = query.filter_by(status=status)
    return jsonify([
        {**c.to_dict(), 'usuario': {'id': c.usuario.id, 'username': c.usuario.username, 'email': c.usuario.email}}
        for c in query.all()
    ])
