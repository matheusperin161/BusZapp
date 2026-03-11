import sys, os
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"

from src.main import create_app
from src.models import db
from src.models.user import User
from werkzeug.security import generate_password_hash, check_password_hash

app = create_app()

with app.app_context():
    user = User.query.filter_by(username='admin').first()
    
    if user:
        # Resetar senha
        user.password = generate_password_hash('admin123')
        user.role = 'admin'
        db.session.commit()
        
        # Verificar se funcionou
        ok = check_password_hash(user.password, 'admin123')
        print(f'Usuário: {user.username}')
        print(f'Role: {user.role}')
        print(f'Senha admin123 válida: {ok}')
    else:
        print('Admin não encontrado, criando...')
        admin = User(
            username='admin',
            email='admin@buszapp.com',
            password=generate_password_hash('admin123'),
            role='admin',
            card_balance=100.0
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin criado! Login: admin / admin123')