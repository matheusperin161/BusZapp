"""Application factory and entry point."""
import os
from flask import Flask, jsonify, redirect, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_migrate import Migrate

from src.models import db
from src.config import config, DEFAULT_SECRET_KEY
from src.extensions import limiter


socketio = SocketIO()
migrate = Migrate()


def create_app(env: str = 'default') -> Flask:
    # static/ lives at the project root (one level above src/)
    project_root = os.path.dirname(os.path.dirname(__file__))
    app = Flask(__name__, static_folder=os.path.join(project_root, 'static'))
    app.config.from_object(config[env])
    if env == 'production' and app.config['SECRET_KEY'] == DEFAULT_SECRET_KEY:
        raise RuntimeError('Defina SECRET_KEY no ambiente de produção.')

    # Atrás do proxy do Render: IP real do cliente (rate limit) e esquema https
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    # Allowed origins: comma-separated list from env, fallback to localhost for dev
    _raw_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080')
    allowed_origins = [o.strip() for o in _raw_origins.split(',') if o.strip()]

    # Extensions
    CORS(app, supports_credentials=True, origins=allowed_origins)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=allowed_origins, async_mode='threading')

    # Register blueprints
    from src.routes.auth import auth_bp
    from src.routes.card import card_bp
    from src.routes.bus import bus_bp
    from src.routes.admin import admin_bp
    from src.routes.tracking import tracking_bp, set_socketio, register_socketio_handlers
    from src.routes.viagens import viagens_bp, set_socketio as set_viagens_socketio
    from src.routes.cartoes import cartoes_bp
    from src.routes.paradas import paradas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(card_bp)
    app.register_blueprint(bus_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(viagens_bp)
    app.register_blueprint(cartoes_bp)
    app.register_blueprint(paradas_bp)

    set_socketio(socketio)
    set_viagens_socketio(socketio)
    register_socketio_handlers(socketio)

    # Create tables
    with app.app_context():
        db.create_all()

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(self), camera=(), microphone=()'
        response.headers['X-XSS-Protection'] = '0'
        # Remove server fingerprint headers
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        return response

    # API sempre responde JSON (o app mobile não entende a página HTML de erro)
    # (erros não tratados chegam aqui como InternalServerError)
    @app.errorhandler(HTTPException)
    def api_http_error(e):
        if not request.path.startswith('/api/'):
            return e
        mensagem = 'Erro interno do servidor' if e.code == 500 else e.description
        return jsonify({'error': mensagem}), e.code

    # Serve frontend SPA com URLs sem .html
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder = app.static_folder

        # Rota de API inexistente não cai no index.html
        if path == 'api' or path.startswith('api/'):
            return jsonify({'error': 'Recurso não encontrado'}), 404

        # URLs sem .html: redireciona /<page>.html para /<page>
        # (exceto arquivos de verificação do Google, que bots não seguem redirect)
        if path.endswith('.html') and not path.startswith('google'):
            clean = '' if path == 'index.html' else path[:-5]
            return redirect('/' + clean, code=301)

        # Serve arquivos estáticos existentes (CSS, JS, imagens, sw, manifest, google-verify)
        if path and os.path.exists(os.path.join(static_folder, path)):
            return send_from_directory(static_folder, path)

        # URL limpa → arquivo .html correspondente (/login → login.html)
        if path:
            html_path = os.path.join(static_folder, path + '.html')
            if os.path.exists(html_path):
                return send_from_directory(static_folder, path + '.html')

        # Fallback: index.html
        index = os.path.join(static_folder, 'index.html')
        if os.path.exists(index):
            return send_from_directory(static_folder, 'index.html')
        return 'index.html not found', 404

    return app


if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    socketio.run(app, host='0.0.0.0', port=8080, debug=(env == 'development'), allow_unsafe_werkzeug=True)
