import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS
from flask_limiter import Limiter # Import Limiter
from flask_limiter.util import get_remote_address # Import strategy for identifying users
from flask_migrate import Migrate # <-- Import Migrate
from config import config_by_name

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate() # <-- Create Migrate instance
limiter = Limiter( # Initialize Limiter
    key_func=get_remote_address,
    # REMOVE default_limits to only apply limits where explicitly decorated
    # default_limits=["200 per day", "50 per hour"]
)

def create_app(config_name=None):
    """
    Application factory function.
    Creates and configures the Flask app.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'dev')

    app = Flask(__name__)

    try:
        app.config.from_object(config_by_name[config_name])
        print(f" * Loading configuration: {config_name}")
    except KeyError:
        print(f"Error: Invalid configuration name '{config_name}'. Using default 'dev'.")
        app.config.from_object(config_by_name['dev'])

    # --- Initialize CORS ---
    allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173')
    if allowed_origins_str == '*':
        origins = "*"
        print(" * CORS allowing all origins (development default)")
    else:
        origins = [origin.strip() for origin in allowed_origins_str.split(',')]
        print(f" * CORS allowing specific origins: {', '.join(origins)}")

    CORS(app, resources={r"/api/*": {"origins": origins}})
    # --- End CORS Initialization ---

    # --- Initialize Extensions with App Context ---
    db.init_app(app)
    migrate.init_app(app, db) # <-- Initialize Migrate with app and db
    limiter.init_app(app) # Initialize Limiter with the app

    # --- Import models AFTER db is initialized ---
    with app.app_context(): # Ensure we are in app context
        from . import models  # <-- ADD THIS LINE HERE

    # Register blueprints
    from .routes import api as api_blueprint
    # Ensure the blueprint is registered with the /api prefix
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # --- Add Root Route with DB Check ---
    @app.route('/')
    def index():
        try:
            # Use a more specific query if needed, SELECT 1 is fine for basic check
            db.session.execute(text('SELECT 1'))
            db_status = "connected"
        except Exception as e:
            print(f"Database connection error: {e}")
            db_status = "disconnected"

        return jsonify({
            "message": "DropNote API is running",
            "database_status": db_status
        })
    # --- End Root Route ---

    # Error handlers are registered in routes.py using @api.errorhandler

    return app
