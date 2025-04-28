import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_cors import CORS
from flask_limiter import Limiter # Import Limiter
from flask_limiter.util import get_remote_address # Import strategy for identifying users
from config import config_by_name

# Initialize extensions
db = SQLAlchemy()
limiter = Limiter( # Initialize Limiter
    key_func=get_remote_address, # Use remote IP address to track requests
    default_limits=["200 per day", "50 per hour"] # Default limits for routes not explicitly decorated
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
    # Read allowed origins from environment variable, fallback to '*' for development
    # Example production value for CORS_ALLOWED_ORIGINS: "https://yourfrontend.com,https://www.yourfrontend.com"
    allowed_origins_str = os.getenv('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:5333/')
    if allowed_origins_str == '*':
        origins = "*"
        print(" * CORS allowing all origins (development default)")
    else:
        # Split comma-separated string into a list
        origins = [origin.strip() for origin in allowed_origins_str.split(',')]
        print(f" * CORS allowing specific origins: {', '.join(origins)}")

    # Apply CORS settings
    CORS(app, resources={r"/api/*": {"origins": origins}})
    # --- End CORS Initialization ---

    # --- Initialize Extensions with App Context ---
    db.init_app(app)
    limiter.init_app(app) # Initialize Limiter with the app

    # Register blueprints
    from .routes import api as api_blueprint
    app.register_blueprint(api_blueprint)

    # --- Add Root Route with DB Check ---
    @app.route('/')
    def index():
        try:
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

    return app
