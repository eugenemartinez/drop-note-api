import os
from app import create_app

# Determine the configuration name (e.g., 'dev' or 'prod')
# Vercel typically sets NODE_ENV=production, we can use that or define our own like FLASK_CONFIG
config_name = os.getenv('FLASK_CONFIG', 'prod' if os.getenv('NODE_ENV') == 'production' else 'dev')

# Create the Flask app instance using the factory
app = create_app(config_name)

if __name__ == "__main__":
    # This part is for running locally using `python wsgi.py`
    # For production, Gunicorn will directly use the 'app' variable.
    # Use Flask's built-in server for local development (or `flask run`)
    # The port 5333 is often used by Flask dev server, but can be anything
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=app.config.get('DEBUG', False))
