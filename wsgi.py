"""WSGI entry point para deploy no Render/gunicorn."""
import os
from src.main import create_app, socketio

app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    socketio.run(app)
