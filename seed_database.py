# filepath: backend/seed_database.py
import json
import os
import uuid
import random
import string
from sqlalchemy import create_engine, text, exc
from dotenv import load_dotenv

# --- Configuration ---
JSON_FILE_PATH = 'sample_notes.json' # Path to the generated JSON file

# --- Load Environment Variables (for DATABASE_URL) ---
load_dotenv() # Load variables from .env file in the current directory
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set.")
    print("Please ensure your .env file is in the backend directory and contains DATABASE_URL.")
    exit(1)

# --- Helper Function ---
def generate_modification_code(length=8):
    """Generates a random alphanumeric modification code."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# --- Main Seeding Logic ---
def seed_data():
    print(f"Connecting to database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            print("Database connection successful.")
            print(f"Reading data from '{JSON_FILE_PATH}'...")
            try:
                with open(JSON_FILE_PATH, 'r') as f:
                    notes_to_seed = json.load(f)
            except FileNotFoundError:
                print(f"Error: JSON file not found at '{JSON_FILE_PATH}'.")
                print("Please run generate_seeds.py first.")
                return
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from '{JSON_FILE_PATH}'.")
                return

            print(f"Found {len(notes_to_seed)} notes to seed.")

            # Begin transaction
            with connection.begin():
                print("Starting transaction...")
                insert_count = 0
                for i, note_data in enumerate(notes_to_seed):
                    note_id = uuid.uuid4()
                    mod_code = generate_modification_code()

                    insert_sql = text("""
                        INSERT INTO drop_note
                        (id, title, content, username, tags, visibility, modification_code)
                        VALUES
                        (:id, :title, :content, :username, :tags, :visibility, :modification_code)
                    """)

                    try:
                        connection.execute(insert_sql, {
                            'id': note_id,
                            'title': note_data.get('title', 'Untitled'),
                            'content': note_data.get('content', ''),
                            'username': note_data.get('username', 'anonymous'),
                            'tags': note_data.get('tags', []), # Pass list directly
                            'visibility': note_data.get('visibility', 'public'),
                            'modification_code': mod_code
                        })
                        insert_count += 1
                        # Print progress occasionally
                        if (i + 1) % 10 == 0 or (i + 1) == len(notes_to_seed):
                            print(f"  Inserted note {i + 1}/{len(notes_to_seed)}")

                    except exc.SQLAlchemyError as e:
                        print(f"\nError inserting note {i+1} ({note_data.get('title')}): {e}")
                        print("Rolling back transaction.")
                        # The 'with connection.begin()' handles the rollback on error
                        raise # Re-raise to exit the loop and trigger rollback

                print("Transaction successful. Committing...")
            # Transaction is automatically committed here if no errors occurred

            print(f"\nSuccessfully inserted {insert_count} notes into the database.")

    except exc.SQLAlchemyError as e:
        print(f"\nDatabase connection or operation failed: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

# --- Run the Seeder ---
if __name__ == "__main__":
    seed_data()