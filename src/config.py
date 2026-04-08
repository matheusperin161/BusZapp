import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_database_url() -> str:
    """Resolve DATABASE_URL, corrigindo prefixo legado do Heroku/Render."""
    url = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}")
    # Heroku/Render ainda pode retornar 'postgres://' — SQLAlchemy 2.x exige 'postgresql://'
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _get_database_url()

    # Pool settings — ignorados pelo SQLite, usados pelo PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,       # verifica conexão antes de usar
        'pool_recycle': 300,         # recicla conexões a cada 5 min
        'pool_size': 3,              # conservador para tier gratuito do Neon
        'max_overflow': 5,
        'connect_args': {'options': '-c timezone=America/Sao_Paulo'}
    }


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Google Maps / Tracking
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
ROUTE_ORIGIN_LAT = float(os.getenv('ROUTE_ORIGIN_LAT', -27.10597))
ROUTE_ORIGIN_LON = float(os.getenv('ROUTE_ORIGIN_LON', -52.61336))
ROUTE_DEST_LAT = float(os.getenv('ROUTE_DEST_LAT', -27.07171))
ROUTE_DEST_LON = float(os.getenv('ROUTE_DEST_LON', -52.63635))

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Google Maps / Tracking
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')
ROUTE_ORIGIN_LAT = float(os.getenv('ROUTE_ORIGIN_LAT', -27.10597))
ROUTE_ORIGIN_LON = float(os.getenv('ROUTE_ORIGIN_LON', -52.61336))
ROUTE_DEST_LAT = float(os.getenv('ROUTE_DEST_LAT', -27.07171))
ROUTE_DEST_LON = float(os.getenv('ROUTE_DEST_LON', -52.63635))