import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_default_secret_key_for_dev')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    if SQLALCHEMY_DATABASE_URI and not SQLALCHEMY_DATABASE_URI.startswith("postgresql+psycopg2://"):
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql+psycopg2://", 1)
        elif SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
             SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgresql://", "postgresql+psycopg2://", 1)
        else:
            print(f"Warning: DATABASE_URL scheme might be incorrect for SQLAlchemy/psycopg2: {SQLALCHEMY_DATABASE_URI}")
            if '@' in SQLALCHEMY_DATABASE_URI and '/' in SQLALCHEMY_DATABASE_URI:
                 SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{SQLALCHEMY_DATABASE_URI}"


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

config_by_name = dict(
    dev=DevelopmentConfig,
    prod=ProductionConfig
)

key = Config.SECRET_KEY