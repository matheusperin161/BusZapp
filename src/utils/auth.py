"""Authentication helpers."""
from functools import wraps
from flask import session, jsonify, g
from src.models import db
from src.models.user import User, Motorista


def get_current_user() -> User | None:
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        user = db.session.get(User, user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Acesso negado: requer privilégios de administrador'}), 403
        return f(*args, **kwargs)
    return decorated


def motorista_required(f):
    """Exige usuário com perfil motorista; disponibiliza o cadastro em g.motorista."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Usuário não autenticado'}), 401
        motorista = Motorista.query.filter_by(usuario_id=user_id).first()
        if not motorista:
            return jsonify({'error': 'Acesso negado: requer perfil de motorista'}), 403
        g.motorista = motorista
        return f(*args, **kwargs)
    return decorated
