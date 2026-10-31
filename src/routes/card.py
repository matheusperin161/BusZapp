"""Card balance, recharge, transport usage, and transaction routes (telas web).

Operam sobre o cartão do usuário (tabela cartoes), o mesmo usado pelo app em /api/cartoes.
"""
from datetime import datetime
from flask import Blueprint, jsonify, request, g

from src.models import db
from src.models.user import Transaction, BusRoute, Cartao, CARD_TYPES
from src.services.cartao_service import cartao_do_usuario, creditar, debitar
from src.services.notification_service import create_notification
from src.utils.auth import login_required

card_bp = Blueprint('card', __name__, url_prefix='/api')

VALID_PAYMENT_METHODS = ('cartao', 'pix')
LOW_BALANCE_THRESHOLD = 5.0
VALID_CARD_TYPES = CARD_TYPES


@card_bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    cartao = g.user.cartao
    return jsonify({'balance': cartao.saldo if cartao else 0.0})


@card_bp.route('/recharge', methods=['POST'])
@login_required
def recharge_card():
    data = request.get_json() or {}
    payment_method = data.get('payment_method', 'cartao')

    try:
        amount = float(data.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valor inválido'}), 400

    if amount <= 0:
        return jsonify({'error': 'Valor deve ser maior que zero'}), 400
    if payment_method not in VALID_PAYMENT_METHODS:
        return jsonify({'error': 'Método de pagamento inválido'}), 400

    user = g.user
    tx_id_suffix = f'{user.id}_{int(datetime.utcnow().timestamp())}'
    payment_info = _build_payment_info(payment_method, tx_id_suffix, amount)

    cartao = cartao_do_usuario(user, criar=True)
    transaction = creditar(cartao, round(amount * 100),
                           f'Recarga via {payment_info["method"]} - R$ {amount:.2f}')
    if not transaction:
        return jsonify({'error': 'Cartão bloqueado'}), 409

    create_notification(
        user.id,
        'Recarga Realizada',
        f'Recarga de R$ {amount:.2f} via {payment_info["method"]}. Novo saldo: R$ {cartao.saldo:.2f}.',
    )

    return jsonify({
        'message': 'Recarga realizada com sucesso',
        'new_balance': cartao.saldo,
        'transaction': transaction.to_dict(),
        'payment_info': payment_info,
    }), 200

@card_bp.route('/card/register', methods=['POST'])
@login_required
def register_card():
    data = request.get_json() or {}
    card_number = data.get('card_number', '').strip()
    holder_name = data.get('holder_name', '').strip()
    card_type   = data.get('card_type', '').strip().lower()

    if not card_number:
        return jsonify({'error': 'Número do cartão é obrigatório'}), 400
    if not holder_name:
        return jsonify({'error': 'Nome do titular é obrigatório'}), 400
    if card_type not in VALID_CARD_TYPES:
        return jsonify({'error': f'Tipo de cartão inválido. Tipos válidos: {", ".join(VALID_CARD_TYPES)}'}), 400

    user = g.user

    # Enforce 1 card per user
    if user.cartao and user.cartao.numero:
        return jsonify({'error': 'Você já possui um cartão cadastrado. Cada usuário pode ter apenas 1 cartão.'}), 409
    if Cartao.query.filter_by(numero=card_number).first():
        return jsonify({'error': 'Este número de cartão já está cadastrado.'}), 409

    cartao = cartao_do_usuario(user, criar=True)
    cartao.numero  = card_number
    cartao.titular = holder_name
    cartao.tipo    = card_type
    db.session.commit()

    create_notification(
        user.id,
        'Cartão Cadastrado',
        f'Seu cartão do tipo "{card_type}" foi cadastrado com sucesso.',
    )

    return jsonify({
        'message': 'Cartão cadastrado com sucesso',
        'card_number': card_number,
        'card_holder': holder_name,
        'card_type': card_type,
    }), 200


@card_bp.route('/card/info', methods=['GET'])
@login_required
def get_card_info():
    cartao = g.user.cartao
    return jsonify({
        'card_number': cartao.numero if cartao else None,
        'card_holder': cartao.titular if cartao else None,
        'card_type':   cartao.tipo if cartao else None,
        'card_balance': cartao.saldo if cartao else 0.0,
        'card_status': cartao.status if cartao else None,
    }), 200


def _build_payment_info(method: str, tx_suffix: str, amount: float) -> dict:
    if method == 'cartao':
        return {'method': 'Cartão de Crédito', 'status': 'Aprovado', 'transaction_id': f'CARD_{tx_suffix}'}
    return {
        'method': 'PIX',
        'status': 'Aprovado',
        'transaction_id': f'PIX_{tx_suffix}',
        'qr_code': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
    }


@card_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    transactions = (
        Transaction.query
        .filter_by(user_id=g.user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return jsonify([t.to_dict() for t in transactions])


@card_bp.route('/use-transport', methods=['POST'])
@login_required
def use_transport():
    data = request.get_json() or {}
    route_id = data.get('route_id')

    user = g.user
    route = db.session.get(BusRoute, route_id) if route_id is not None else None
    cartao = user.cartao

    if not route:
        return jsonify({'error': 'Usuário ou rota não encontrada'}), 404
    if not cartao:
        return jsonify({'error': 'Saldo insuficiente'}), 400
    if cartao.status != 'ativo':
        return jsonify({'error': 'Cartão bloqueado'}), 409

    transaction = debitar(cartao, round(route.fare * 100), f'Uso do transporte - Linha {route.route_number}')
    if not transaction:
        return jsonify({'error': 'Saldo insuficiente'}), 400

    if cartao.saldo < LOW_BALANCE_THRESHOLD:
        create_notification(
            user.id,
            'Saldo Baixo',
            f'Saldo atual: R$ {cartao.saldo:.2f}. Recarregue para evitar interrupções.',
        )

    return jsonify({
        'message': 'Transporte utilizado com sucesso',
        'new_balance': cartao.saldo,
        'transaction': transaction.to_dict(),
    }), 200
