import pytest
import os
import uuid # Import uuid for checking ID format
from flask import json # Import json for request data
from . import create_app
from . import db

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    # Store the original FLASK_CONFIG if it exists
    original_flask_config = os.environ.get('FLASK_CONFIG')
    os.environ['FLASK_CONFIG'] = 'test' # Ensure tests run with test configuration

    # Create the Flask app using the factory function from __init__.py
    # This should pick up FLASK_CONFIG='test'
    flask_app = create_app()

    # Establish an application context BEFORE accessing db or other app-bound extensions
    ctx = flask_app.app_context()
    ctx.push()

    # --- Create tables for the database ---
    # This assumes your TestConfig (or the config 'test' maps to)
    # points to the database you intend to use for these tests.
    try:
        db.create_all() # Create tables based on SQLAlchemy models
        yield flask_app # Provide the app instance to tests
    finally:
        # --- Clean up context after tests ---
        db.session.remove() # Ensure session is closed properly
        # db.drop_all() # <<--- REMOVE OR COMMENT OUT THIS LINE
        ctx.pop() # Pop the application context

    # Restore original FLASK_CONFIG
    if original_flask_config is None:
        del os.environ['FLASK_CONFIG']
    else:
        os.environ['FLASK_CONFIG'] = original_flask_config


# --- Pytest Fixture for the Test Client ---
@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()

# --- Test Functions ---

def test_get_public_notes_basic(client):
    """
    Test fetching public notes returns a 200 OK status and JSON data.
    """
    response = client.get('/api/notes')

    assert response.status_code == 200
    assert response.content_type == 'application/json'
    json_data = response.get_json()
    assert 'notes' in json_data
    assert 'pagination' in json_data
    assert isinstance(json_data['notes'], list)
    # Check that the list is initially empty in the test DB
    assert len(json_data['notes']) == 0

# --- ADD THIS TEST ---
def test_create_note_success(client):
    """
    Test successfully creating a new public note with minimal data.
    """
    note_data = {
        "title": "My Test Note",
        "content": "<p>This is the content.</p>",
        # Optional fields (username, tags, visibility) will use defaults
    }
    response = client.post('/api/notes', json=note_data)

    # Check status code and content type
    assert response.status_code == 201 # 201 Created
    assert response.content_type == 'application/json'

    # Check response body structure and content
    json_data = response.get_json()
    assert 'id' in json_data
    assert 'title' in json_data
    assert 'content' in json_data
    assert 'username' in json_data # Should be generated like 'anonymousX'
    assert 'tags' in json_data
    assert 'visibility' in json_data
    assert 'created_at' in json_data
    assert 'updated_at' in json_data
    assert 'modification_code' in json_data

    # Check specific values
    assert json_data['title'] == note_data['title']
    # Content might be slightly different due to sanitization, check it's still the core content
    assert "This is the content." in json_data['content']
    assert json_data['visibility'] == 'public' # Default visibility
    assert isinstance(json_data['tags'], list) and len(json_data['tags']) == 0 # Default tags
    assert json_data['username'].startswith('anonymous') # Check generated username format

    # Check formats
    try:
        uuid.UUID(json_data['id'], version=4) # Check if 'id' is a valid UUID string
    except ValueError:
        pytest.fail(f"ID '{json_data['id']}' is not a valid UUID")

    assert isinstance(json_data['modification_code'], str) and len(json_data['modification_code']) > 0

    # --- Optional: Verify note exists in DB via GET request ---
    # This makes the test more robust by checking persistence
    note_id = json_data['id']
    get_response = client.get(f'/api/notes/{note_id}')
    assert get_response.status_code == 200
    get_data = get_response.get_json()
    assert get_data['id'] == note_id
    assert get_data['title'] == note_data['title']

# --- NEW TEST: Update Note Success ---
def test_update_note_success(client):
    """
    Test successfully updating a note's title and content.
    """
    # 1. Create a note first to get its ID and modification code
    create_data = {
        "title": "Note to Update",
        "content": "<p>Original Content</p>",
        "tags": ["update", "test"],
        "visibility": "public"
    }
    create_response = client.post('/api/notes', json=create_data)
    assert create_response.status_code == 201
    create_json = create_response.get_json()
    note_id = create_json['id']
    mod_code = create_json['modification_code']
    original_username = create_json['username'] # Keep original username

    # 2. Prepare update data
    update_data = {
        "title": "Updated Title",
        "content": "<p>Updated Content</p>",
        "tags": ["updated"], # Test changing tags
        "visibility": "private", # Test changing visibility
        "modification_code": mod_code # Provide the correct code
    }

    # 3. Send PUT request to update the note
    update_response = client.put(f'/api/notes/{note_id}', json=update_data)

    # 4. Assert the response
    assert update_response.status_code == 200
    update_json = update_response.get_json()
    assert update_json['id'] == note_id
    assert update_json['title'] == "Updated Title" # Check updated title
    assert update_json['content'] == "<p>Updated Content</p>" # Check updated content
    assert update_json['tags'] == ["updated"] # Check updated tags
    assert update_json['visibility'] == "private" # Check updated visibility
    assert update_json['username'] == original_username # Username should not change on update
    assert 'modification_code' not in update_json # Mod code shouldn't be in response

    # 5. Optional: Verify with a subsequent GET request
    get_response = client.get(f'/api/notes/{note_id}')
    assert get_response.status_code == 200
    get_json = get_response.get_json()
    assert get_json['title'] == "Updated Title"
    assert get_json['content'] == "<p>Updated Content</p>"
    assert get_json['tags'] == ["updated"]
    assert get_json['visibility'] == "private"

# --- NEW TEST: Delete Note Success ---
def test_delete_note_success(client):
    """
    Test successfully deleting a note.
    """
    # 1. Create a note first to get its ID and modification code
    create_data = {
        "title": "Note to Delete",
        "content": "<p>This note will be deleted.</p>",
        "tags": ["delete", "test"],
        "visibility": "public"
    }
    create_response = client.post('/api/notes', json=create_data)
    assert create_response.status_code == 201
    create_json = create_response.get_json()
    note_id = create_json['id']
    mod_code = create_json['modification_code']

    # 2. Prepare delete request data
    delete_data = {
        "modification_code": mod_code # Provide the correct code
    }

    # 3. Send DELETE request
    delete_response = client.delete(f'/api/notes/{note_id}', json=delete_data)

    # 4. Assert the response status code
    assert delete_response.status_code == 204 # Expect 204 No Content for successful DELETE

    # 5. Optional: Verify with a subsequent GET request (should be 404)
    get_response = client.get(f'/api/notes/{note_id}')
    assert get_response.status_code == 404 # Expect 404 Not Found after deletion

# --- NEW TEST: Get Public Notes ---
def test_get_public_notes_excludes_private(client):
    """
    Test GET /api/notes returns public notes but excludes private ones.
    """
    # 1. Create a public note
    public_data = {
        "title": "Public Note",
        "content": "This is visible to everyone.",
        "tags": ["public", "test"],
        "visibility": "public"
    }
    create_public_res = client.post('/api/notes', json=public_data)
    assert create_public_res.status_code == 201
    public_note_id = create_public_res.get_json()['id']

    # 2. Create a private note
    private_data = {
        "title": "Private Note",
        "content": "This is only for the owner.",
        "tags": ["private", "test"],
        "visibility": "private" # Explicitly private
    }
    create_private_res = client.post('/api/notes', json=private_data)
    assert create_private_res.status_code == 201
    private_note_id = create_private_res.get_json()['id']

    # 3. Get public notes
    get_response = client.get('/api/notes')
    assert get_response.status_code == 200
    json_data = get_response.get_json()

    # 4. Assert response structure and content
    assert 'notes' in json_data
    assert isinstance(json_data['notes'], list)
    assert 'pagination' in json_data
    assert isinstance(json_data['pagination'], dict)
    assert 'total_notes' in json_data['pagination']
    assert 'current_page' in json_data['pagination']
    assert 'per_page' in json_data['pagination']

    # 5. Verify only the public note is returned
    assert len(json_data['notes']) == 1
    returned_note = json_data['notes'][0]
    assert returned_note['id'] == public_note_id
    assert returned_note['title'] == "Public Note"
    assert returned_note['visibility'] == "public"
    assert private_note_id not in [note['id'] for note in json_data['notes']]

    # 6. Verify total count reflects only public notes
    assert json_data['pagination']['total_notes'] == 1
    assert json_data['pagination']['current_page'] == 1

# --- Add more tests below (e.g., create with tags, private, invalid data) ---
def test_create_note_missing_title(client):
    """
    Test creating a note with missing title returns 400 Bad Request.
    """
    note_data = {
        # "title": "Missing Title", # Title is intentionally missing
        "content": "<p>This note has no title.</p>",
    }
    response = client.post('/api/notes', json=note_data)

    # Check status code and content type
    assert response.status_code == 400 # Expect Bad Request
    assert response.content_type == 'application/json'

    # Check error message in response body
    json_data = response.get_json()
    assert 'error' in json_data
    # Check if the specific error message from your validation is present
    assert "Missing required fields: title" in json_data['error'] or "Title is required" in json_data['error']

def test_create_note_missing_content(client):
    """
    Test creating a note with missing content returns 400 Bad Request.
    """
    note_data = {
        "title": "Note with No Content",
        # "content": "<p>Missing Content</p>", # Content is intentionally missing
    }
    response = client.post('/api/notes', json=note_data)

    # Check status code and content type
    assert response.status_code == 400 # Expect Bad Request
    assert response.content_type == 'application/json'

    # Check error message in response body
    json_data = response.get_json()
    assert 'error' in json_data
    # Check if the specific error message from your validation is present
    assert "Missing required fields: content" in json_data['error'] or "Content is required" in json_data['error']

# --- Add these tests for UPDATE errors ---
def test_update_note_missing_mod_code(client):
    """
    Test updating a note without providing a modification code returns 400.
    """
    # 1. Create a note
    create_res = client.post('/api/notes', json={"title": "ModCode Test", "content": "Content"})
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']

    # 2. Attempt update without modification_code
    update_data = {"title": "New Title"} # Missing modification_code
    update_res = client.put(f'/api/notes/{note_id}', json=update_data)

    # 3. Assert 400 Bad Request
    assert update_res.status_code == 400
    assert "Missing modification_code" in update_res.get_json()['error']

def test_update_note_invalid_mod_code(client):
    """
    Test updating a note with an incorrect modification code returns 403.
    """
    # 1. Create a note
    create_res = client.post('/api/notes', json={"title": "ModCode Test", "content": "Content"})
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']
    # correct_mod_code = create_res.get_json()['modification_code'] # We won't use this

    # 2. Attempt update with a wrong modification_code
    update_data = {
        "title": "New Title",
        "modification_code": "invalid_code_123" # Incorrect code
    }
    update_res = client.put(f'/api/notes/{note_id}', json=update_data)

    # 3. Assert 403 Forbidden
    assert update_res.status_code == 403
    assert "Invalid modification_code" in update_res.get_json()['error']

def test_update_note_not_found(client):
    """
    Test updating a non-existent note returns 404.
    """
    non_existent_uuid = str(uuid.uuid4())
    update_data = {
        "title": "New Title",
        "modification_code": "doesnt_matter"
    }
    update_res = client.put(f'/api/notes/{non_existent_uuid}', json=update_data)

    # Assert 404 Not Found
    assert update_res.status_code == 404
    assert "Note not found" in update_res.get_json()['error']

# --- Add similar tests for DELETE errors ---
def test_delete_note_missing_mod_code(client):
    """
    Test deleting a note without providing a modification code returns 400.
    """
    # 1. Create a note
    create_res = client.post('/api/notes', json={"title": "Delete ModCode Test", "content": "Content"})
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']

    # 2. Attempt delete without modification_code
    delete_data = {} # Missing modification_code
    delete_res = client.delete(f'/api/notes/{note_id}', json=delete_data)

    # 3. Assert 400 Bad Request
    assert delete_res.status_code == 400
    assert "Missing modification_code" in delete_res.get_json()['error']

def test_delete_note_invalid_mod_code(client):
    """
    Test deleting a note with an incorrect modification code returns 403.
    """
    # 1. Create a note
    create_res = client.post('/api/notes', json={"title": "Delete ModCode Test", "content": "Content"})
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']

    # 2. Attempt delete with a wrong modification_code
    delete_data = {
        "modification_code": "invalid_code_456" # Incorrect code
    }
    delete_res = client.delete(f'/api/notes/{note_id}', json=delete_data)

    # 3. Assert 403 Forbidden
    assert delete_res.status_code == 403
    assert "Invalid modification_code" in delete_res.get_json()['error']

def test_delete_note_not_found(client):
    """
    Test deleting a non-existent note returns 204 (idempotent).
    """
    non_existent_uuid = str(uuid.uuid4())
    delete_data = {
        "modification_code": "doesnt_matter"
    }
    delete_res = client.delete(f'/api/notes/{non_existent_uuid}', json=delete_data)

    # Assert 204 No Content (as per current route logic)
    assert delete_res.status_code == 204

# --- Tests for GET /api/notes/{id} ---

def test_get_single_note_public_success(client):
    """
    Test retrieving a single existing public note by ID returns 200 OK
    and includes the 'visibility' field set to 'public'.
    """
    # 1. Create a public note
    create_data = {
        "title": "Public Single Note",
        "content": "Content for public single note.",
        "visibility": "public" # Explicitly public
    }
    create_res = client.post('/api/notes', json=create_data)
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']

    # 2. Retrieve the note by ID
    get_res = client.get(f'/api/notes/{note_id}')

    # 3. Assert success and correct data
    assert get_res.status_code == 200
    assert get_res.content_type == 'application/json'
    note_data = get_res.get_json()
    assert note_data['id'] == note_id
    assert note_data['title'] == create_data['title']
    assert note_data['content'] == create_data['content']
    assert 'visibility' in note_data # Check the key exists
    assert note_data['visibility'] == 'public' # Check the value
    assert 'modification_code' not in note_data # Mod code should not be returned on GET

def test_get_single_note_private_success(client):
    """
    Test retrieving a single existing private note by ID returns 200 OK
    and includes the 'visibility' field set to 'private'.
    (Based on the design where direct URL access is allowed for private notes).
    """
    # 1. Create a private note
    create_data = {
        "title": "Private Single Note",
        "content": "This is private.",
        "visibility": "private" # Explicitly private
    }
    create_res = client.post('/api/notes', json=create_data)
    assert create_res.status_code == 201
    note_id = create_res.get_json()['id']

    # 2. Retrieve the private note by ID
    get_res = client.get(f'/api/notes/{note_id}')

    # 3. Assert success (200 OK) and correct data
    assert get_res.status_code == 200 # <<< Expect 200 OK, not 403
    assert get_res.content_type == 'application/json'
    note_data = get_res.get_json()
    assert note_data['id'] == note_id
    assert note_data['title'] == create_data['title']
    assert note_data['content'] == create_data['content']
    assert 'visibility' in note_data # Check the key exists
    assert note_data['visibility'] == 'private' # Check the value
    assert 'modification_code' not in note_data # Mod code should not be returned on GET

def test_get_single_note_not_found(client):
    """
    Test retrieving a non-existent note by ID returns 404 Not Found.
    (This test remains the same as it's correct).
    """
    non_existent_uuid = str(uuid.uuid4())

    # Attempt to retrieve the non-existent note
    get_res = client.get(f'/api/notes/{non_existent_uuid}')

    # Assert 404 Not Found
    assert get_res.status_code == 404
    assert get_res.content_type == 'application/json'
    assert "Note not found" in get_res.get_json()['error']

# --- Tests for GET /api/tags ---

def test_get_tags_empty(client):
    """
    Test GET /api/tags returns an empty list when no public notes exist.
    """
    response = client.get('/api/tags')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    json_data = response.get_json()
    assert 'tags' in json_data
    assert json_data['tags'] == []

def test_get_tags_success(client):
    """
    Test GET /api/tags returns unique tags from public notes only.
    """
    # 1. Create notes with various tags and visibilities
    client.post('/api/notes', json={"title": "Public 1", "content": "c", "tags": ["tag1", "tag2"], "visibility": "public"})
    client.post('/api/notes', json={"title": "Public 2", "content": "c", "tags": ["tag2", "tag3"], "visibility": "public"})
    client.post('/api/notes', json={"title": "Private 1", "content": "c", "tags": ["tag3", "tag4"], "visibility": "private"}) # Private note tags should be excluded
    client.post('/api/notes', json={"title": "Public 3", "content": "c", "tags": ["tag1"], "visibility": "public"}) # Duplicate public tag
    client.post('/api/notes', json={"title": "Public 4", "content": "c", "tags": [], "visibility": "public"}) # No tags
    client.post('/api/notes', json={"title": "Public 5", "content": "c", "visibility": "public"}) # Tags field missing

    # 2. Get the tags
    response = client.get('/api/tags')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    json_data = response.get_json()
    assert 'tags' in json_data

    # 3. Assert the returned tags are unique and only from public notes
    # The order might vary depending on the database, so check presence and count
    expected_tags = ["tag1", "tag2", "tag3"]
    returned_tags = json_data['tags']
    assert len(returned_tags) == len(expected_tags)
    assert sorted(returned_tags) == sorted(expected_tags) # Compare sorted lists
    assert "tag4" not in returned_tags # Ensure private tag is excluded

# --- Tests for GET /api/notes/random ---

def test_get_random_note_not_found(client):
    """
    Test GET /api/notes/random returns 404 when no public notes exist.
    """
    response = client.get('/api/notes/random')
    assert response.status_code == 404
    assert response.content_type == 'application/json'
    assert "No public notes found" in response.get_json()['error']

def test_get_random_note_success(client):
    """
    Test GET /api/notes/random returns a 200 OK and a valid public note
    when public notes exist.
    """
    # 1. Create multiple public notes and one private note
    public_data1 = {"title": "Random Public 1", "content": "c1", "visibility": "public"}
    public_data2 = {"title": "Random Public 2", "content": "c2", "visibility": "public"}
    private_data = {"title": "Random Private", "content": "cp", "visibility": "private"}

    res1 = client.post('/api/notes', json=public_data1)
    res2 = client.post('/api/notes', json=public_data2)
    client.post('/api/notes', json=private_data) # Create private note

    assert res1.status_code == 201
    assert res2.status_code == 201
    public_note_id1 = res1.get_json()['id']
    public_note_id2 = res2.get_json()['id']
    public_note_ids = {public_note_id1, public_note_id2} # Set of possible public IDs

    # 2. Get a random note
    response = client.get('/api/notes/random')

    # 3. Assert success and valid note structure
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    note_data = response.get_json()

    # Check basic structure and fields
    assert 'id' in note_data
    assert 'title' in note_data
    assert 'content' in note_data
    assert 'username' in note_data
    assert 'tags' in note_data
    assert 'visibility' in note_data
    assert 'created_at' in note_data
    assert 'updated_at' in note_data
    assert 'modification_code' not in note_data # Mod code should not be returned

    # 4. Assert the returned note is one of the public ones created
    assert note_data['id'] in public_note_ids
    assert note_data['visibility'] == 'public' # Ensure it's public

    # 5. Optional: Call it again to increase confidence it's random (not strictly necessary)
    response2 = client.get('/api/notes/random')
    assert response2.status_code == 200
    note_data2 = response2.get_json()
    assert note_data2['id'] in public_note_ids
    assert note_data2['visibility'] == 'public'

# --- Tests for POST /api/notes/batch ---

def test_get_notes_batch_empty_list(client):
    """
    Test POST /api/notes/batch with an empty list of IDs returns an empty list.
    """
    response = client.post('/api/notes/batch', json={"ids": []})
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    json_data = response.get_json()
    assert 'notes' in json_data
    assert json_data['notes'] == []

def test_get_notes_batch_invalid_input(client):
    """
    Test POST /api/notes/batch with various invalid inputs returns 400.
    """
    # Not JSON
    response = client.post('/api/notes/batch', data="not json")
    assert response.status_code == 400
    assert "Request must be JSON" in response.get_json()['error']

    # Missing 'ids' field
    response = client.post('/api/notes/batch', json={"other_field": []})
    assert response.status_code == 400
    assert "Missing or invalid 'ids' field" in response.get_json()['error']

    # 'ids' field is not a list
    response = client.post('/api/notes/batch', json={"ids": "not-a-list"})
    assert response.status_code == 400
    assert "Missing or invalid 'ids' field" in response.get_json()['error']

    # List contains invalid UUID format
    response = client.post('/api/notes/batch', json={"ids": ["invalid-uuid-format"]})
    assert response.status_code == 400
    assert "Invalid UUID format" in response.get_json()['error']

def test_get_notes_batch_success(client):
    """
    Test POST /api/notes/batch successfully retrieves multiple notes,
    including public and private ones, and handles non-existent IDs.
    """
    # 1. Create notes
    res_pub = client.post('/api/notes', json={"title": "Batch Public", "content": "c", "visibility": "public"})
    res_priv = client.post('/api/notes', json={"title": "Batch Private", "content": "c", "visibility": "private"})
    assert res_pub.status_code == 201
    assert res_priv.status_code == 201
    pub_id = res_pub.get_json()['id']
    priv_id = res_priv.get_json()['id']
    non_existent_id = str(uuid.uuid4())

    # 2. Request these notes plus a non-existent one
    request_ids = [pub_id, non_existent_id, priv_id] # Mix order and include non-existent
    response = client.post('/api/notes/batch', json={"ids": request_ids})

    # 3. Assert success
    assert response.status_code == 200
    assert response.content_type == 'application/json'
    json_data = response.get_json()
    assert 'notes' in json_data
    returned_notes = json_data['notes']

    # 4. Verify the correct notes were returned (order might not be guaranteed by default)
    assert len(returned_notes) == 2 # Only the two existing notes should be returned
    returned_ids = {note['id'] for note in returned_notes}
    assert returned_ids == {pub_id, priv_id} # Check if the correct IDs are present

    # 5. Verify structure and visibility of returned notes
    for note in returned_notes:
        assert 'id' in note
        assert 'title' in note
        assert 'content' in note
        assert 'visibility' in note
        assert 'modification_code' not in note # Mod code should not be returned
        if note['id'] == pub_id:
            assert note['visibility'] == 'public'
            assert note['title'] == "Batch Public"
        elif note['id'] == priv_id:
            assert note['visibility'] == 'private'
            assert note['title'] == "Batch Private"
