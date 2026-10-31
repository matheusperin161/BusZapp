"""Authentication helpers.

O web autentica pela sessão (cookie). O app mobile manda `Authorization: Bearer <token>`,
recebido no login com `"client": "mobile"`. Os decorators aceitam os dois e deixam o
usuário em g.user.
"""
from functools import wraps
from flask import session, jsonify, g, request, current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature

from src.models import db
from src.models.user import User, Motorista

TOKEN_MAX_AGE = 30 * 24 * 3600  # 30 dias, igual ao PERMANENT_SESSION_LIFETIME


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='api-token')


def gerar_token(user: User) -> str:
    # token_version: incrementar invalida todos os tokens já emitidos para o usuário
    return _serializer().dumps({'uid': user.id, 'v': user.token_version})


def _usuario_do_token() -> User | None:
    cabecalho = request.headers.get('Authorization', '')
    if not cabecalho.startswith('Bearer '):
        return None
    try:
        dados = _serializer().loads(cabecalho[7:].strip(), max_age=TOKEN_MAX_AGE)
    except BadSignature:  # inclui SignatureExpired
        return None
    user = db.session.get(User, dados.get('uid'))
    if not user or user.token_version != dados.get('v'):
        return None
    return user


def get_current_user() -> User | None:
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return _usuario_do_token()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        if user.role != 'admin':
            return jsonify({'error': 'Acesso negado: requer privilégios de administrador'}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated


def motorista_required(f):
    """Exige usuário com perfil motorista; disponibiliza o cadastro em g.motorista."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        motorista = Motorista.query.filter_by(usuario_id=user.id).first()
        if not motorista:
            return jsonify({'error': 'Acesso negado: requer perfil de motorista'}), 403
        g.user = user
        g.motorista = motorista
        return f(*args, **kwargs)
    return decorated
