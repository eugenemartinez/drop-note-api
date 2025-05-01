import pytest
import os
from sqlalchemy import text # <<< Import text
from app import create_app, db # Import your factory and db instance

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    # Ensure the environment variable is used for the database URI
    # If FLASK_CONFIG isn't set, create_app defaults to 'dev', which reads DATABASE_URL
    # You might explicitly set a 'testing' config if you have one that also reads DATABASE_URL
    config_name = os.getenv('FLASK_CONFIG', 'dev') # Or 'testing' if you define one
    app = create_app(config_name=config_name)

    # Establish an application context before running tests
    with app.app_context():
         # Optional: Create tables if they don't exist in the test DB
         # db.create_all() # Be careful with this on a persistent test DB
         yield app
         # Optional: Clean up tables after tests
         # db.drop_all()

@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function', autouse=True)
def setup_database(app):
     """Clean database before each test function."""
     with app.app_context():
         # --- Simplified Deletion ---
         with db.engine.connect() as connection:
             with connection.begin():
                 # Explicitly delete all rows from drop_note table
                 connection.execute(text("DELETE FROM drop_note"))
                 # If using Alembic migrations table, clear it too (optional but good practice)
                 # try:
                 #     connection.execute(text("DELETE FROM alembic_version"))
                 # except Exception: # Handle case where table might not exist yet
                 #     pass
         # --- End Simplified Deletion ---

         yield # Let the test run

         # No explicit cleanup needed after yield if done before