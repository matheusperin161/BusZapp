"""Authentication routes: register, login, logout, profile, password reset."""
import os
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from src.models import db
from src.models.user import User
from src.utils.auth import login_required

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
MAX_AVATAR_BYTES = 3 * 1024 * 1024  # 3 MB


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    from src.models.user import EmailVerificationToken
    from src.services.email_service import send_verification_email

    data = request.get_json() or {}
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip().lower()
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
        email_verified=False,
    )
    db.session.add(user)
    db.session.flush()  # gera o user.id sem commitar ainda

    token = secrets.token_urlsafe(32)
    verification = EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.session.add(verification)
    db.session.commit()

    sent = send_verification_email(email, username, token)

    return jsonify({
        'message': 'Conta criada! Verifique seu e-mail para ativar o acesso.',
        'email_sent': sent,
    }), 201


@auth_bp.route('/verify-email', methods=['GET'])
def verify_email():
    """Confirma o e-mail do usuário via link enviado por e-mail."""
    from src.models.user import EmailVerificationToken
    token = request.args.get('token', '').strip()

    if not token:
        return '''<html><body style="font-family:Arial;text-align:center;padding:60px">
            <h2 style="color:#e53e3e">❌ Token inválido</h2>
            <p>Link de verificação inválido.</p>
            <a href="/login.html">Ir para o login</a></body></html>''', 400

    record = EmailVerificationToken.query.filter_by(token=token).first()
    if not record or not record.is_valid():
        return '''<html><body style="font-family:Arial;text-align:center;padding:60px">
            <h2 style="color:#e53e3e">❌ Link expirado</h2>
            <p>Este link de verificação expirou ou já foi usado.</p>
            <a href="/login.html">Ir para o login</a></body></html>''', 400

    user = db.session.get(User, record.user_id)
    if not user:
        return '''<html><body style="font-family:Arial;text-align:center;padding:60px">
            <h2 style="color:#e53e3e">❌ Usuário não encontrado</h2>
            <a href="/login.html">Ir para o login</a></body></html>''', 404

    user.email_verified = True
    record.used = True
    db.session.commit()

    return '''<html>
    <head><meta charset="UTF-8"><title>E-mail confirmado — BusZapp</title>
    <meta http-equiv="refresh" content="4;url=/login.html">
    </head>
    <body style="font-family:Arial,sans-serif;text-align:center;padding:80px 20px;background:#fffbeb">
      <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:16px;padding:48px 40px;box-shadow:0 4px 24px rgba(0,0,0,0.08)">
        <div style="font-size:56px;margin-bottom:16px">✅</div>
        <h2 style="color:#92400e;margin:0 0 12px;font-size:22px">E-mail confirmado!</h2>
        <p style="color:#78716c;line-height:1.6">
          Sua conta foi ativada com sucesso.<br>
          Redirecionando para o login em instantes...
        </p>
        <a href="/login.html" style="display:inline-block;margin-top:24px;background:linear-gradient(135deg,#fbbf24,#f97316);color:#fff;text-decoration:none;padding:12px 32px;border-radius:10px;font-weight:700">
          Fazer login agora
        </a>
      </div>
    </body></html>'''


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Reenvia o e-mail de verificação para o usuário."""
    from src.models.user import EmailVerificationToken
    from src.services.email_service import send_verification_email

    data  = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'E-mail é obrigatório'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Se o e-mail estiver cadastrado, um novo link será enviado.'}), 200
    if user.email_verified:
        return jsonify({'error': 'Este e-mail já foi verificado.'}), 400

    # Invalida tokens anteriores
    EmailVerificationToken.query.filter_by(user_id=user.id, used=False).update({'used': True})

    token = secrets.token_urlsafe(32)
    db.session.add(EmailVerificationToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    ))
    db.session.commit()

    sent = send_verification_email(email, user.username, token)
    return jsonify({'message': 'Novo link de verificação enviado!', 'email_sent': sent}), 200


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'E-mail e senha são obrigatórios'}), 400

    # Check if it's a driver login first
    from src.models.user import Driver
    driver = Driver.query.filter_by(email=email).first()
    if driver and driver.password and check_password_hash(driver.password, password):
        session['driver_id'] = driver.id
        session['role'] = 'driver'
        return jsonify({
            'message': 'Login realizado com sucesso',
            'role': 'driver',
            'redirect': '/motorista.html',
            'driver': driver.to_dict(),
        }), 200

    # Regular user login by email
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        if not user.email_verified:
            return jsonify({
                'error': 'E-mail não verificado. Verifique sua caixa de entrada ou solicite um novo link.',
                'not_verified': True,
                'email': email,
            }), 403

        session['user_id'] = user.id
        session['role'] = user.role
        redirect = '/admin.html' if user.role == 'admin' else '/dashboard.html'
        return jsonify({
            'message': 'Login realizado com sucesso',
            'role': user.role,
            'redirect': redirect,
            'user': user.to_dict(),
        }), 200

    return jsonify({'error': 'E-mail ou senha inválidos'}), 401


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
    from src.models.user import PasswordResetToken
    from src.services.email_service import send_password_reset_email

    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'E-mail é obrigatório'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha'}), 200

    # Invalida tokens anteriores
    PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})

    token = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.session.add(reset_token)
    db.session.commit()

    sent = send_password_reset_email(email, user.username, token)

    return jsonify({
        'message': 'Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha.',
        'email_sent': sent,
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    from src.models.user import PasswordResetToken

    data = request.get_json() or {}
    token      = data.get('reset_token', '').strip()
    user_id    = data.get('user_id')
    new_password     = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not token or not new_password or not confirm_password:
        return jsonify({'error': 'Todos os campos são obrigatórios'}), 400
    if new_password != confirm_password:
        return jsonify({'error': 'As senhas não coincidem'}), 400
    if len(new_password) < 6:
        return jsonify({'error': 'A senha deve ter pelo menos 6 caracteres'}), 400

    reset = PasswordResetToken.query.filter_by(token=token).first()
    if not reset or not reset.is_valid():
        return jsonify({'error': 'Token inválido ou expirado. Solicite uma nova redefinição.'}), 400

    user = db.session.get(User, reset.user_id)
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    user.password = generate_password_hash(new_password)
    reset.used = True

    try:
        db.session.commit()
        return jsonify({'message': 'Senha redefinida com sucesso'}), 200
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Erro ao redefinir senha'}), 500


@auth_bp.route('/driver/me', methods=['GET'])
def driver_me():
    """Retorna dados do motorista logado na sessão atual."""
    from src.models.user import Driver
    driver_id = session.get('driver_id')
    if not driver_id:
        return jsonify({'error': 'Não autenticado'}), 401
    driver = db.session.get(Driver, driver_id)
    if not driver:
        return jsonify({'error': 'Motorista não encontrado'}), 404
    return jsonify(driver.to_dict())


@auth_bp.route('/profile/picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Faz upload da foto de perfil do usuário autenticado."""
    if 'picture' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['picture']
    if not file or file.filename == '':
        return jsonify({'error': 'Arquivo inválido'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'error': 'Formato não suportado. Use PNG, JPG, WEBP ou GIF'}), 400

    # Verifica tamanho sem consumir o stream
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_AVATAR_BYTES:
        return jsonify({'error': 'Arquivo muito grande. Máximo 3 MB'}), 400

    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"avatar_{user.id}.{ext}"

    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)

    # Remove foto anterior se existir (extensão diferente)
    for old in os.listdir(upload_dir):
        if old.startswith(f"avatar_{user.id}."):
            os.remove(os.path.join(upload_dir, old))

    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    user.profile_picture = f"/uploads/avatars/{filename}"
    db.session.commit()

    return jsonify({'profile_picture': user.profile_picture}), 200


@auth_bp.route('/profile/picture', methods=['DELETE'])
@login_required
def delete_profile_picture():
    """Remove a foto de perfil do usuário."""
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'Usuário não encontrado'}), 404

    if user.profile_picture:
        filepath = os.path.join(current_app.static_folder, user.profile_picture.lstrip('/'))
        if os.path.exists(filepath):
            os.remove(filepath)
        user.profile_picture = None
        db.session.commit()

    return jsonify({'message': 'Foto removida'}), 200
