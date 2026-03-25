"""Card balance, recharge, transport usage, and transaction routes."""
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from src.models import db
from src.models.user import User, Transaction, BusRoute
from src.services.notification_service import create_notification
from src.utils.auth import login_required

card_bp = Blueprint('card', __name__, url_prefix='/api')

VALID_PAYMENT_METHODS = ('cartao', 'pix', 'boleto')
LOW_BALANCE_THRESHOLD = 5.0
VALID_CARD_TYPES = ('cidadao', 'normal', 'estudante', 'idoso', 'acompanhante', 'carteiro', 'colaborador', 'pcd')


@card_bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({'balance': user.card_balance})


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

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    tx_id_suffix = f'{user.id}_{int(datetime.utcnow().timestamp())}'
    payment_info = _build_payment_info(payment_method, tx_id_suffix, amount)

    user.card_balance += amount
    transaction = Transaction(
        user_id=user.id,
        amount=amount,
        transaction_type='recharge',
        description=f'Recarga via {payment_info["method"]} - R$ {amount:.2f}',
    )
    db.session.add(transaction)
    db.session.commit()

    create_notification(
        user.id,
        'Recarga Realizada',
        f'Recarga de R$ {amount:.2f} via {payment_info["method"]}. Novo saldo: R$ {user.card_balance:.2f}.',
    )

    return jsonify({
        'message': 'Recarga realizada com sucesso',
        'new_balance': user.card_balance,
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

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    user.card_number = card_number
    user.card_holder = holder_name
    user.card_type   = card_type
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
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify({
        'card_number': user.card_number,
        'card_holder': user.card_holder,
        'card_type':   user.card_type,
        'card_balance': user.card_balance,
    }), 200


def _build_payment_info(method: str, tx_suffix: str, amount: float) -> dict:
    if method == 'cartao':
        return {'method': 'Cartão de Crédito', 'status': 'Aprovado', 'transaction_id': f'CARD_{tx_suffix}'}
    if method == 'pix':
        return {
            'method': 'PIX',
            'status': 'Aprovado',
            'transaction_id': f'PIX_{tx_suffix}',
            'qr_code': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
        }
    # boleto
    return {
        'method': 'Boleto Bancário',
        'status': 'Aprovado',
        'transaction_id': f'BOL_{tx_suffix}',
        'barcode': '23793.39001 60000.000001 00000.000000 1 84770000010000',
    }


@card_bp.route('/transactions', methods=['GET'])
@login_required
def get_transactions():
    transactions = (
        Transaction.query
        .filter_by(user_id=session['user_id'])
        .order_by(Transaction.created_at.desc())
        .all()
    )
    return jsonify([t.to_dict() for t in transactions])


@card_bp.route('/use-transport', methods=['POST'])
@login_required
def use_transport():
    data = request.get_json() or {}
    route_id = data.get('route_id')

    user = db.session.get(User, session['user_id'])
    route = db.session.get(BusRoute, route_id)

    if not user or not route:
        return jsonify({'error': 'Usuário ou rota não encontrada'}), 404
    if user.card_balance < route.fare:
        return jsonify({'error': 'Saldo insuficiente'}), 400

    user.card_balance -= route.fare
    transaction = Transaction(
        user_id=user.id,
        amount=-route.fare,
        transaction_type='usage',
        description=f'Uso do transporte - Linha {route.route_number}',
    )
    db.session.add(transaction)
    db.session.commit()

    if user.card_balance < LOW_BALANCE_THRESHOLD:
        create_notification(
            user.id,
            'Saldo Baixo',
            f'Saldo atual: R$ {user.card_balance:.2f}. Recarregue para evitar interrupções.',
        )

    return jsonify({
        'message': 'Transporte utilizado com sucesso',
        'new_balance': user.card_balance,
        'transaction': transaction.to_dict(),
    }), 200
