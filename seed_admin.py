import sys
from src.main import create_app
from src.models import db
from src.models.user import User
from werkzeug.security import generate_password_hash

app = create_app('development')

with app.app_context():
    email = 'buszapp.email@gmail.com'
    admin = User.query.filter_by(email=email).first()
    
    if admin:
        print(f"O usuário {email} já existe. Atualizando a senha para 'admin123' e ativando o e-mail.")
        admin.password = generate_password_hash('admin123')
        admin.role = 'admin'
        admin.email_verified = True
    else:
        print(f"Criando no banco o usuário admin {email} com a senha 'admin123'...")
        admin = User(
            username='Administrador',
            email=email,
            password=generate_password_hash('admin123'),
            role='admin',
            email_verified=True,  # Muito importante para conseguir logar!
            card_balance=0.0
        )
        db.session.add(admin)
    
    db.session.commit()
    print("Sucesso! Usuário admin está pronto para login.")
