import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'app.db')}"
    )

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