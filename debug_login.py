import sys, os
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"

from src.main import create_app
from src.models import db
from src.models.user import User
from werkzeug.security import check_password_hash

app = create_app()

with app.app_context():
    # Listar todos os usuários
    users = User.query.all()
    print(f"Total de usuários no banco: {len(users)}")
    for u in users:
        ok = check_password_hash(u.password, 'admin123')
        print(f"  id={u.id} username='{u.username}' role={u.role} senha_ok={ok}")
    
    # Simular exatamente o que a rota faz
    print("\n--- Simulando rota /api/auth/login ---")
    user = User.query.filter_by(username='admin').first()
    print(f"User encontrado: {user}")
    if user:
        print(f"Hash salvo: {user.password[:40]}...")
        print(f"check_password_hash: {check_password_hash(user.password, 'admin123')}")