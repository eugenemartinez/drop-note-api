# DropNote Backend

This is the Flask backend API for the DropNote application.

## Features

*   API for note operations (Create, Read, Update, Delete)
*   Public/private notes, tagging, search, sorting, random note retrieval
*   Modification codes for secure updates/deletes
*   Rate limiting

## Setup

### Prerequisites

*   Python 3.9
*   PostgreSQL
*   `pip`

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <https://github.com/eugenemartinez/drop-note-api>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the `backend` directory. Add the following, adjusting values as needed:
    ```dotenv
    # .env
    DATABASE_URL='postgresql+psycopg2://<user>:<password>@<host>:<port>/<database>?sslmode=require' # Your Neon DB URL or other PostgreSQL URL
    CORS_ALLOWED_ORIGINS='http://localhost:5173' # Or your frontend deployment URL

    ```
    *Ensure your PostgreSQL database is running and accessible.*

5.  **Database Setup:**
    You may need to create the necessary tables. If using SQLAlchemy models, you can often do this from a Flask shell:
    ```bash
    flask shell
    >>> from app import db
    >>> db.create_all()
    >>> exit()
    ```
    *Alternatively, run the `schema.sql` script directly against your database if you are not using `db.create_all()`.*

### Running the Development Server

```bash
flask run
```
The API should now be running, typically at `http://127.0.0.1:5333`.

## API Endpoints

### Notes

*   **`POST /api/notes`**
    *   Creates a new note.
    *   **Body (JSON):** `{ "title": "string", "content": "string (HTML)", "tags": ["string"], "visibility": "public|private", "username": "string (optional)" }`
    *   **Response:** `201 Created` with the new note object including `id` and `modification_code`.

*   **`GET /api/notes`**
    *   Retrieves a list of public notes.
    *   **Query Parameters:**
        *   `page` (int, default: 1): Page number for pagination.
        *   `limit` (int, default: 10, max: 100): Number of notes per page.
        *   `tag` (string): Filter notes by a specific tag.
        *   `search` (string): Search term for title and content (case-insensitive).
        *   `sort` (string, default: `updated_at_desc`): Sort order (e.g., `title_asc`, `created_at_desc`).
    *   **Response:** `200 OK` with `{ "notes": [...], "pagination": {...} }`.

*   **`GET /api/notes/random`**
    *   Retrieves a single random public note.
    *   **Response:** `200 OK` with the note object, or `404 Not Found`.

*   **`GET /api/notes/<uuid:note_id>`**
    *   Retrieves a specific note by its UUID.
    *   **Response:** `200 OK` with the note object, or `404 Not Found`.

*   **`PUT /api/notes/<uuid:note_id>`**
    *   Updates an existing note. Requires the correct modification code.
    *   **Body (JSON):** `{ "modification_code": "string", "title": "string (optional)", "content": "string (HTML, optional)", "tags": ["string", optional], "visibility": "public|private (optional)" }`
    *   **Response:** `200 OK` with the updated note object, `400 Bad Request`, `403 Forbidden`, or `404 Not Found`.

*   **`DELETE /api/notes/<uuid:note_id>`**
    *   Deletes an existing note. Requires the correct modification code.
    *   **Body (JSON):** `{ "modification_code": "string" }`
    *   **Response:** `204 No Content`, `400 Bad Request`, `403 Forbidden`. (Returns 204 even if note was already deleted).

*   **`POST /api/notes/batch`**
    *   Retrieves details for multiple notes by their UUIDs.
    *   **Body (JSON):** `{ "ids": ["uuid_string", "uuid_string", ...] }`
    *   **Response:** `200 OK` with `{ "notes": [...] }` containing found notes.

### Tags

*   **`GET /api/tags`**
    *   Retrieves a list of unique tags used in public notes.
    *   **Response:** `200 OK` with `{ "tags": ["string", ...] }`.

## Testing

(Optional) If you wish to run tests:

1.  Install testing dependencies:
    ```bash
    pip install pytest pytest-flask
    ```
2.  Configure a separate test database or use SQLite in `config.py` (if applicable).
3.  Run tests:
    ```bash
    pytest
    ```