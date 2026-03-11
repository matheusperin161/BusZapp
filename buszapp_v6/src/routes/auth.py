"""Authentication routes: register, login, logout, profile, password reset."""
import secrets
from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash, check_password_hash

from src.models import db
from src.models.user import User
from src.utils.auth import login_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'error': 'Usuário, e-mail e senha são obrigatórios'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Usuário já existe'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'E-mail já cadastrado'}), 400

    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        card_balance=0.0,
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'Usuário criado com sucesso', 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    print(f"[DEBUG] Tentando login: username='{data.get('username')}'")
    print(f"[DEBUG] DB URI: {db.engine.url}")
    
    user = User.query.filter_by(username=data.get('username', '')).first()
    print(f"[DEBUG] Usuário encontrado: {user}")
    
    if user:
        from werkzeug.security import check_password_hash
        ok = check_password_hash(user.password, data.get('password', ''))
        print(f"[DEBUG] Senha válida: {ok}")

    if user and check_password_hash(user.password, data.get('password', '')):
        session['user_id'] = user.id
        return jsonify({'message': 'Login realizado com sucesso', 'user': user.to_dict()}), 200

    return jsonify({'error': 'Credenciais inválidas'}), 401

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logout realizado com sucesso'}), 200


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404
    return jsonify(user.to_dict())


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()

    if not username or not email:
        return jsonify({'error': 'Nome de usuário e e-mail são obrigatórios'}), 400

    if User.query.filter(User.username == username, User.id != user.id).first():
        return jsonify({'error': 'Nome de usuário já existe'}), 400
    if User.query.filter(User.email == email, User.id != user.id).first():
        return jsonify({'error': 'E-mail já cadastrado'}), 400

    user.username = username
    user.email = email
    if data.get('password'):
        user.password = generate_password_hash(data['password'])

    try:
        db.session.commit()
        return jsonify({
            'message': 'Perfil atualizado com sucesso',
            'username': user.username,
            'email': user.email,
        }), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao atualizar perfil'}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'E-mail é obrigatório'}), 400

    user = User.query.filter_by(email=email).first()
    # Security: do not reveal whether the e-mail exists
    response = {'message': 'Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha'}

    if user:
        reset_token = secrets.token_urlsafe(32)
        # NOTE: In production, persist the token with expiry and send via email service.
        response['reset_token'] = reset_token   # Demo only – remove in production
        response['user_id'] = user.id           # Demo only – remove in production

    return jsonify(response), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not user_id or not new_password or not confirm_password:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'As senhas não coincidem'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'A senha deve ter pelo menos 6 caracteres'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    user.password = generate_password_hash(new_password)
    try:
        db.session.commit()
        return jsonify({'message': 'Senha redefinida com sucesso'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao redefinir senha'}), 500
