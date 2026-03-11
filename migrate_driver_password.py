"""Migration: add password column to driver table."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['DATABASE_URL'] = f"sqlite:///{os.path.join(BASE_DIR, 'src', 'instance', 'app.db')}"

from src.main import create_app
from src.models import db
import sqlalchemy as sa

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        # Check if column already exists
        inspector = sa.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('driver')]
        if 'password' not in columns:
            conn.execute(sa.text('ALTER TABLE driver ADD COLUMN password VARCHAR(255)'))
            conn.commit()
            print('✓ Coluna password adicionada à tabela driver')
        else:
            print('! Coluna password já existe')

print('✅ Migration concluída!')
