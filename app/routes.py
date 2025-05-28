import os
import secrets
import uuid
import bleach
from flask import Blueprint, request, jsonify, abort, current_app # Add current_app
from sqlalchemy import text, exc as sqlalchemy_exc
from werkzeug.exceptions import HTTPException
from . import db
from . import limiter

api = Blueprint('api', __name__, url_prefix='/api')

# Define the specific rate limit string
write_limit = "500 per day"
# --- NEW: Define the hard limit for total notes ---
MAX_TOTAL_NOTES = 50 # Or get from app.config or os.environ for more flexibility

# --- Centralized Error Handlers ---

@api.errorhandler(400) # Handles werkzeug.exceptions.BadRequest
@api.errorhandler(ValueError) # Handles potential ValueErrors (e.g., bad UUID format)
def handle_bad_request(error):
    """Handles 400 Bad Request errors and ValueErrors."""
    message = getattr(error, 'description', "Invalid input or request format.")
    details = getattr(error, 'details', None)
    response = {"error": message}
    if details:
        response["details"] = details
    current_app.logger.warning(f"Bad Request/ValueError: {error}") # Use logger.warning
    return jsonify(response), 400

@api.errorhandler(404) # Handles werkzeug.exceptions.NotFound
def handle_not_found(error):
    """Handles 404 Not Found errors."""
    message = getattr(error, 'description', "Resource not found.")
    current_app.logger.warning(f"Not Found: {error}") # Use logger.warning
    return jsonify({"error": message}), 404

@api.errorhandler(403) # Handles werkzeug.exceptions.Forbidden
def handle_forbidden(error):
    """Handles 403 Forbidden errors (e.g., invalid modification code)."""
    message = getattr(error, 'description', "Access forbidden.")
    current_app.logger.warning(f"Forbidden: {error}") # Use logger.warning
    return jsonify({"error": message}), 403

@api.errorhandler(429) # Handles Rate Limit Exceeded from Flask-Limiter
def handle_rate_limit_exceeded(error):
    """Handles 429 Too Many Requests errors."""
    message = f"Rate limit exceeded: {error.description}"
    current_app.logger.warning(f"Rate Limit Exceeded: {error}") # Use logger.warning
    return jsonify({"error": message}), 429

@api.errorhandler(sqlalchemy_exc.SQLAlchemyError) # Catch specific DB errors
def handle_database_error(error):
    """Handles database-related errors."""
    db.session.rollback()
    current_app.logger.exception("Database Error:") # Use logger.exception for traceback
    return jsonify({"error": "A database error occurred."}), 500

@api.errorhandler(Exception) # Catch-all for any other exceptions
def handle_generic_exception(error):
    """Handles any other unexpected exceptions."""
    if isinstance(error, HTTPException):
        current_app.logger.error(f"HTTP Exception {error.code}: {error}") # Use logger.error
        return jsonify({"error": getattr(error, 'description', "An unexpected error occurred.")}), error.code

    current_app.logger.exception("Unhandled Exception:") # Use logger.exception for traceback
    return jsonify({"error": "An internal server error occurred."}), 500

# --- End Error Handlers ---

# --- Validation Helper ---

# --- Define allowed HTML for content (example) ---
ALLOWED_TAGS = [
    'p', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li', 'blockquote', 'hr',
    'h2', 'h3', 'code', 'pre' # Add tags allowed by TipTap
    # Add 'a' if you allow links, configure attributes below
]
ALLOWED_ATTRIBUTES = {
    # Example: Allow 'href' and 'title' on 'a' tags
    # 'a': ['href', 'title'],
}
# --- End Allowed HTML ---

def validate_note_data(data, is_create=False):
    """
    Validates note data fields (title, content, tags, visibility).

    Args:
        data (dict): The input data dictionary from the request.
        is_create (bool): If True, checks for required fields (title, content).

    Returns:
        tuple: A tuple containing:
            - validated_data (dict): Dictionary of valid fields found.
            - errors (dict): Dictionary of validation errors keyed by field name.
    """
    validated_data = {}
    errors = {}
    required_fields = ['title', 'content']

    # Check for required fields during creation
    if is_create:
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            # Add missing fields error, but continue validating others if present
            errors['required'] = f"Missing required fields: {', '.join(missing_fields)}"
            # Don't immediately return, allow other field validations to run

    # Validate title (required for create, optional for update)
    if 'title' in data:
        title = data['title']
        if isinstance(title, str) and title: # Ensure non-empty string
            validated_data['title'] = title
        else:
            errors['title'] = "Title must be a non-empty string"
    elif is_create and 'required' not in errors: # Only add if not already caught by missing fields
         errors['title'] = "Title is required"

    # Validate content (required for create, optional for update)
    if 'content' in data:
        content = data['content']
        if isinstance(content, str) and content: # Ensure non-empty string
            validated_data['content'] = content
        else:
            errors['content'] = "Content must be a non-empty string"
    elif is_create and 'required' not in errors: # Only add if not already caught by missing fields
        errors['content'] = "Content is required"

    # Validate tags (optional for both)
    if 'tags' in data:
        tags = data['tags']
        # Allow empty list, but if present, validate structure
        if isinstance(tags, list):
            if len(tags) > 10:
                errors['tags'] = "Maximum of 10 tags allowed"
            elif not all(isinstance(t, str) for t in tags):
                errors['tags'] = "All tags must be strings"
            else:
                 validated_data['tags'] = tags # Store valid tags
        else:
            errors['tags'] = "Tags must be a list of strings"
    elif is_create:
        validated_data['tags'] = [] # Default to empty list if not provided on create

    # Validate visibility (optional for both, defaults handled elsewhere if needed)
    if 'visibility' in data:
        visibility = str(data['visibility']).lower() # Ensure string and lowercase
        if visibility in ['public', 'private']:
            validated_data['visibility'] = visibility
        else:
            errors['visibility'] = "Visibility must be 'public' or 'private'"
    elif is_create:
        validated_data['visibility'] = 'public' # Default to public if not provided on create

    # --- Sanitize Content ---
    if 'content' in validated_data:
        # Clean content using bleach, allowing specific tags/attributes
        validated_data['content'] = bleach.clean(
            validated_data['content'],
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True # Remove disallowed tags completely
        )
        # Add length check after cleaning
        if len(validated_data['content']) > 10000: # Example limit
             errors['content'] = "Content exceeds maximum length"


    # --- Sanitize Title (strip all HTML) ---
    if 'title' in validated_data:
        original_title = validated_data['title']
        validated_data['title'] = bleach.clean(original_title, tags=[], strip=True).strip()
        if not validated_data['title']: # Check if empty after stripping
             errors['title'] = "Title cannot be empty or only contain HTML tags"
        elif len(validated_data['title']) > 255: # Example limit
             errors['title'] = "Title exceeds maximum length"

    # --- Sanitize Tags (strip all HTML) ---
    if 'tags' in validated_data:
        cleaned_tags = []
        valid_tags = True
        for tag in validated_data['tags']:
            cleaned_tag = bleach.clean(tag, tags=[], strip=True).strip()
            if not cleaned_tag: # Disallow empty tags or tags with only HTML
                errors['tags'] = "Tags cannot be empty or contain only HTML"
                valid_tags = False
                break
            if len(cleaned_tag) > 50: # Example limit
                 errors['tags'] = f"Tag '{cleaned_tag[:20]}...' exceeds maximum length"
                 valid_tags = False
                 break
            cleaned_tags.append(cleaned_tag)
        if valid_tags:
            validated_data['tags'] = cleaned_tags
        else:
             # Remove tags from validated_data if an error occurred during cleaning
             if 'tags' in validated_data: del validated_data['tags']


    # --- Sanitize Username (strip all HTML) ---
    # (Assuming username is handled separately for now, but apply similar logic)
    # if 'username' in validated_data:
    #    validated_data['username'] = bleach.clean(validated_data['username'], tags=[], strip=True).strip()
    #    if not validated_data['username']: errors['username'] = "Username cannot be empty..."
    #    elif len(validated_data['username']) > 100: errors['username'] = "Username exceeds..."


    return validated_data, errors

# --- End Validation Helper ---

def generate_modification_code(length=8):
    """Generates a secure random hex string."""
    return secrets.token_hex(length // 2)

# --- Routes ---

@api.route('/notes', methods=['POST'])
@limiter.limit(write_limit)
def create_note():
    """
    Creates a new note using centralized validation.
    Stops accepting new notes if MAX_TOTAL_NOTES is reached.
    """
    # --- NEW: Check total notes count ---
    try:
        current_notes_count = db.session.execute(text("SELECT COUNT(*) FROM drop_note")).scalar_one()
        if current_notes_count >= MAX_TOTAL_NOTES:
            current_app.logger.warning(f"Max total notes limit reached ({MAX_TOTAL_NOTES}). Rejecting new note.")
            # Using 403 Forbidden, as the action is disallowed due to a server policy
            abort(403, description=f"The maximum number of notes ({MAX_TOTAL_NOTES}) has been reached. New submissions are currently disabled.")
    except sqlalchemy_exc.SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception("Database Error checking total notes count:")
        abort(500, description="Failed to check note capacity due to a database issue.")
    # --- END NEW: Check total notes count ---

    if not request.is_json:
        abort(400, description="Request must be JSON")
    data = request.get_json()
    if data is None:
        abort(400, description="Invalid JSON payload")

    # --- Centralized Input Validation ---
    validated_data, errors = validate_note_data(data, is_create=True)
    if errors:
        error_desc = "Invalid input: " + "; ".join([f"{k}: {v}" for k, v in errors.items()])
        abort(400, description=error_desc)

    # Extract validated AND SANITIZED data
    title = validated_data['title']
    content = validated_data['content']
    tags = validated_data['tags']
    visibility = validated_data['visibility']
    # Get username from original data *before* validation might remove it
    username_input = data.get('username')

    # --- Generate Username if not provided ---
    # Sanitize the input username if provided
    if username_input and isinstance(username_input, str):
         final_username = bleach.clean(username_input, tags=[], strip=True).strip()
         if not final_username:
             final_username = None
         elif len(final_username) > 100:
             abort(400, description="Username exceeds maximum length (100 characters)")
    else:
         final_username = None

    # If no valid username was provided, generate one using the sequence
    if not final_username:
        try:
            sequence_result = db.session.execute(text("SELECT nextval('anonymous_user_seq')")).scalar_one()
            final_username = f"anonymous{sequence_result}"
        except sqlalchemy_exc.SQLAlchemyError as e:
             db.session.rollback()
             current_app.logger.exception("Database Error fetching sequence:") # Use logger.exception
             abort(500, description="Failed to generate anonymous username due to a database issue.")
        except Exception as e:
             current_app.logger.exception("Unexpected Error fetching sequence:") # Use logger.exception
             abort(500, description="Failed to generate anonymous username due to an unexpected error.")
    # --- End Generate Username ---

    # --- Generate Modification Code ---
    modification_code = generate_modification_code()

    # --- Database Insertion ---
    insert_sql = text("""
        INSERT INTO drop_note (title, content, username, tags, visibility, modification_code)
        VALUES (:title, :content, :username, :tags, :visibility, :modification_code)
        RETURNING id, created_at, updated_at
    """)
    result = db.session.execute(insert_sql, {
        'title': title,
        'content': content,
        'username': final_username, # Use the final username here
        'tags': tags,
        'visibility': visibility,
        'modification_code': modification_code
    })
    new_note_data = result.fetchone()

    if not new_note_data:
         db.session.rollback()
         # Let the generic error handler catch this
         raise Exception("Failed to retrieve new note data after insert.")

    db.session.commit()
    new_note_id, created_at, updated_at = new_note_data

    # --- Prepare Response ---
    response_data = {
        "id": str(new_note_id),
        "title": title,
        "content": content,
        "username": final_username, # Use the final username here
        "tags": tags,
        "visibility": visibility,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "modification_code": modification_code
    }
    return jsonify(response_data), 201


# --- UPDATED: List Public Notes Route (with Tag Filtering, Search, and Sorting) ---
@api.route('/notes', methods=['GET'])
def get_public_notes():
    """
    Retrieves a list of public notes.
    Supports pagination via 'page' and 'limit'.
    Supports filtering by tag via 'tag'.
    Supports searching title/content via 'search'.
    Supports sorting via 'sort' (e.g., 'title_asc', 'created_at_desc').
    Defaults to page 1, limit 10, sort by updated_at_desc.
    """
    try:
        # --- Pagination ---
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        if page < 1: page = 1
        if limit < 1: limit = 1
        max_limit = 100
        if limit > max_limit: limit = max_limit
        offset = (page - 1) * limit

        # --- Filtering & Searching ---
        filter_tag = request.args.get('tag', None, type=str)
        search_term = request.args.get('search', None, type=str)

        # --- Sorting ---
        sort_param = request.args.get('sort', 'updated_at_desc', type=str).lower()
        # Define allowed sort fields and directions - ADD secondary sort key for stability
        allowed_sorts = {
            "updated_at_desc": "updated_at DESC, id DESC", # Added , id DESC
            "updated_at_asc": "updated_at ASC, id ASC",   # Added , id ASC
            "created_at_desc": "created_at DESC, id DESC", # Added , id DESC
            "created_at_asc": "created_at ASC, id ASC",   # Added , id ASC
            "title_asc": "LOWER(title) ASC, id ASC",      # Also good practice for titles
            "title_desc": "LOWER(title) DESC, id DESC",     # Also good practice for titles
        }
        # Default to updated_at DESC (with secondary key) if invalid sort param is given
        order_by_clause = allowed_sorts.get(sort_param, "updated_at DESC, id DESC") # Update default too
        # Store the actual sort applied for the response
        applied_sort = sort_param if sort_param in allowed_sorts else 'updated_at_desc'


        # --- Build Query ---
        params = {'limit': limit, 'offset': offset}
        where_clauses = ["visibility = 'public'"]

        if filter_tag:
            where_clauses.append(":tag = ANY(tags)")
            params['tag'] = filter_tag

        if search_term:
            # Use ILIKE for case-insensitive search
            where_clauses.append("(title ILIKE :search_pattern OR content ILIKE :search_pattern)")
            params['search_pattern'] = f"%{search_term}%"

        where_sql = " AND ".join(where_clauses)

        # Select columns needed for the list view
        # Use the dynamically determined order_by_clause (which now includes the secondary key)
        select_sql = text(f"""
            SELECT id, title, content, username, tags, visibility, created_at, updated_at
            FROM drop_note
            WHERE {where_sql}
            ORDER BY {order_by_clause}
            LIMIT :limit OFFSET :offset
        """)

        result = db.session.execute(select_sql, params)
        notes_data = result.mappings().fetchall()

        # --- Format Response ---
        # No changes needed here, as 'content' will now be in note_dict
        notes_list = []
        for note in notes_data:
            note_dict = dict(note)
            note_dict['id'] = str(note_dict['id'])
            note_dict['created_at'] = note_dict['created_at'].isoformat()
            note_dict['updated_at'] = note_dict['updated_at'].isoformat()
            note_dict['tags'] = note_dict.get('tags') or []
            notes_list.append(note_dict)


        # --- Get Total Count for Pagination ---
        count_sql = text(f"SELECT COUNT(*) FROM drop_note WHERE {where_sql}")
        count_params = {}
        if filter_tag:
            count_params['tag'] = filter_tag
        if search_term:
            count_params['search_pattern'] = f"%{search_term}%"
        total_notes = db.session.execute(count_sql, count_params).scalar_one()
        total_pages = (total_notes + limit - 1) // limit


        response = {
            "notes": notes_list,
            "pagination": {
                "current_page": page,
                "per_page": limit,
                "total_notes": total_notes,
                "total_pages": total_pages,
                "filter_tag": filter_tag,
                "search_term": search_term,
                "sort": applied_sort
            }
        }

        return jsonify(response), 200

    except Exception as e:
        current_app.logger.exception("Error fetching public notes:") # Use logger.exception
        # Let the centralized handler manage the response
        abort(500, description="Database error occurred while fetching notes")


# --- NEW: Get Random Public Note Route ---
@api.route('/notes/random', methods=['GET'])
def get_random_note():
    """
    Retrieves a single, randomly selected public note.
    """
    try:
        # Use TABLESAMPLE SYSTEM (1) for efficiency on larger tables,
        # or ORDER BY random() for simplicity on smaller tables.
        # ORDER BY random() is generally fine for moderate table sizes.
        select_sql = text("""
            SELECT id, title, content, username, tags, visibility, created_at, updated_at
            FROM drop_note
            WHERE visibility = 'public'
            ORDER BY random()
            LIMIT 1
        """)
        result = db.session.execute(select_sql)
        note_data = result.mappings().fetchone()

        if not note_data:
            # Handle case where there are no public notes
            return jsonify({"error": "No public notes found"}), 404

        # Format the response similar to get_note
        response_data = dict(note_data)
        response_data['id'] = str(response_data['id'])
        response_data['created_at'] = response_data['created_at'].isoformat()
        response_data['updated_at'] = response_data['updated_at'].isoformat()
        response_data['tags'] = response_data.get('tags') or []

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.exception("Error fetching random note:") # Use logger.exception
        abort(500, description="Database error occurred while fetching random note")


@api.route('/tags', methods=['GET'])
def get_public_tags():
    """
    Retrieves a list of unique tags used in public notes.
    """
    try:
        # Use unnest to expand the tags array into rows,
        # then select distinct tags only from public notes.
        select_sql = text("""
            SELECT DISTINCT unnest(tags) AS tag
            FROM drop_note
            WHERE visibility = 'public' AND tags IS NOT NULL AND array_length(tags, 1) > 0
            ORDER BY tag ASC;
        """)
        result = db.session.execute(select_sql)
        # Fetch all results and extract the tag string from each row tuple
        tags_list = [row[0] for row in result.fetchall()]

        return jsonify({"tags": tags_list}), 200

    except Exception as e:
        current_app.logger.exception("Error fetching public tags:") # Use logger.exception
        abort(500, description="Database error occurred while fetching tags")


@api.route('/notes/<uuid:note_id>', methods=['GET'])
def get_note(note_id):
    """
    Retrieves a specific note by its UUID.
    note_id is automatically converted to a Python UUID object by Flask.
    """
    try:
        select_sql = text("""
            SELECT id, title, content, username, tags, visibility, created_at, updated_at
            FROM drop_note
            WHERE id = :note_id -- Query using the UUID
        """)
        # Pass the UUID object directly as a parameter
        result = db.session.execute(select_sql, {'note_id': note_id})
        note_data = result.mappings().fetchone()

        if not note_data:
            return jsonify({"error": "Note not found"}), 404

        response_data = dict(note_data)
        # Convert UUID id back to string for JSON response
        response_data['id'] = str(response_data['id'])
        response_data['created_at'] = response_data['created_at'].isoformat()
        response_data['updated_at'] = response_data['updated_at']. isoformat()
        response_data['tags'] = response_data.get('tags') or []

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.exception(f"Error fetching note {note_id}:") # Use logger.exception
        abort(500, description="Database error occurred while fetching note")


@api.route('/notes/<uuid:note_id>', methods=['PUT'])
@limiter.limit(write_limit)
def update_note(note_id):
    """
    Updates an existing note using centralized validation.
    """
    if not request.is_json:
        abort(400, description="Request must be JSON")
    data = request.get_json()
    if data is None:
        abort(400, description="Invalid JSON payload")

    provided_mod_code = data.get('modification_code')
    if not provided_mod_code:
        abort(400, description="Missing modification_code")

    # --- Fetch and Validate Modification Code ---
    check_sql = text("SELECT modification_code FROM drop_note WHERE id = :note_id")
    result = db.session.execute(check_sql, {'note_id': note_id})
    db_note = result.fetchone()
    if not db_note:
        abort(404, description="Note not found")
    correct_mod_code = db_note[0]
    if provided_mod_code != correct_mod_code:
        abort(403, description="Invalid modification_code")

    # --- Centralized Input Validation ---
    # Pass only the fields relevant for update (exclude modification_code)
    update_data = {k: v for k, v in data.items() if k != 'modification_code'}
    validated_data, errors = validate_note_data(update_data, is_create=False) # is_create=False

    if errors:
        error_desc = "Invalid input: " + "; ".join([f"{k}: {v}" for k, v in errors.items()])
        abort(400, description=error_desc)

    # Check if any valid fields were actually provided for update
    if not validated_data:
        abort(400, description="No valid fields provided for update")

    # --- Perform Update ---
    # validated_data now contains the fields to update
    set_clause = ", ".join([f"{field} = :{field}" for field in validated_data.keys()])
    update_sql = text(f"""
        UPDATE drop_note
        SET {set_clause}
        WHERE id = :note_id
        RETURNING id, title, content, username, tags, visibility, created_at, updated_at
    """)
    params = {**validated_data, 'note_id': note_id}

    result = db.session.execute(update_sql, params)
    updated_note_data = result.mappings().fetchone()
    db.session.commit()

    if not updated_note_data:
         raise Exception("Failed to retrieve updated note data after update.")

    # --- Prepare Response ---
    response_data = dict(updated_note_data)
    response_data['id'] = str(response_data['id'])
    response_data['created_at'] = response_data['created_at'].isoformat()
    response_data['updated_at'] = response_data['updated_at'].isoformat()
    response_data['tags'] = response_data.get('tags') or []

    return jsonify(response_data), 200


# --- Refactored Delete Route ---
@api.route('/notes/<uuid:note_id>', methods=['DELETE'])
@limiter.limit(write_limit) # Apply rate limit to delete_note
def delete_note(note_id):
    """
    Deletes an existing note.
    Requires the correct modification_code in the JSON body.
    Uses centralized error handlers. Returns 204 No Content on success.
    """
    if not request.is_json:
        abort(400, description="Request must be JSON")

    data = request.get_json()
    if data is None:
        abort(400, description="Invalid JSON payload")

    provided_mod_code = data.get('modification_code')
    if not provided_mod_code:
        abort(400, description="Missing modification_code")

    # --- Validate modification code (Let error handlers catch DB/other errors) ---
    check_sql = text("SELECT modification_code FROM drop_note WHERE id = :note_id")
    result = db.session.execute(check_sql, {'note_id': note_id})
    db_note = result.fetchone()

    if not db_note:
        # Note already deleted or never existed, treat as success (idempotent)
        return '', 204 # 204 No Content is common for successful DELETE

    correct_mod_code = db_note[0]

    if provided_mod_code != correct_mod_code:
        abort(403, description="Invalid modification_code") # Use abort for 403

    # --- Perform Deletion (Let error handlers catch DB/other errors) ---
    delete_sql = text("DELETE FROM drop_note WHERE id = :note_id")
    # Execute returns a result proxy, we might want to check rowcount
    result_proxy = db.session.execute(delete_sql, {'note_id': note_id})

    # Optional check: Ensure a row was actually deleted
    if result_proxy.rowcount == 0:
        # This case might indicate a race condition if the note was deleted
        # between the check and the delete. Treating as success (idempotent) is often fine.
        current_app.logger.warning(f"DELETE affected 0 rows for note {note_id}. Might have been deleted concurrently.") # Use logger.warning
        # Still commit potential transaction state changes if any occurred before delete
        db.session.commit()
        return '', 204

    db.session.commit()

    # Return 204 No Content on successful deletion
    return '', 204


# --- NEW: Batch Fetch Notes by IDs Route ---
@api.route('/notes/batch', methods=['POST'])
# No rate limit applied to get_notes_batch
def get_notes_batch():
    """
    Retrieves details for multiple notes based on a list of provided UUIDs.
    Expects JSON data: { "ids": ["uuid1", "uuid2", ...] }
    Returns a list of note objects. Notes not found or not public might be omitted.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    note_ids_str = data.get('ids')

    if not isinstance(note_ids_str, list):
        return jsonify({"error": "Missing or invalid 'ids' field: must be a list of UUID strings"}), 400

    # --- Validate UUIDs ---
    note_ids_uuid = []
    invalid_ids = []
    for id_str in note_ids_str:
        try:
            note_ids_uuid.append(uuid.UUID(id_str))
        except ValueError:
            invalid_ids.append(id_str)

    if invalid_ids:
        return jsonify({"error": f"Invalid UUID format for IDs: {', '.join(invalid_ids)}"}), 400

    if not note_ids_uuid:
        return jsonify({"notes": []}), 200 # Return empty list if no valid IDs provided

    # --- Query ---
    try:
        # Use WHERE id = ANY(:ids_array) for efficient lookup with a list/tuple of UUIDs
        select_sql = text("""
            SELECT id, title, content, username, tags, visibility, created_at, updated_at
            FROM drop_note
            WHERE id = ANY(:ids_array)
            -- Optional: Add ORDER BY if a specific order is desired, e.g., ORDER BY updated_at DESC
        """)

        # Pass the list of UUID objects directly
        result = db.session.execute(select_sql, {'ids_array': note_ids_uuid})
        notes_data = result.mappings().fetchall()

        # --- Format Response ---
        notes_list = []
        for note in notes_data:
            note_dict = dict(note)
            note_dict['id'] = str(note_dict['id'])
            note_dict['created_at'] = note_dict['created_at'].isoformat()
            note_dict['updated_at'] = note_dict['updated_at'].isoformat()
            note_dict['tags'] = note_dict.get('tags') or []
            # Note: We return all requested notes found, regardless of visibility.
            # The frontend knows which IDs it saved, so privacy isn't compromised here.
            notes_list.append(note_dict)

        return jsonify({"notes": notes_list}), 200

    except Exception as e:
        current_app.logger.exception("Error fetching notes batch:") # Use logger.exception
        abort(500, description="Database error occurred while fetching notes batch")