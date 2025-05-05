from . import db # Import the db instance from app/__init__.py
# Remove TIMESTAMPTZ from this import
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT
# Import the standard TIMESTAMP type from SQLAlchemy core
from sqlalchemy import TIMESTAMP
import uuid # For the default UUID generation in Python (alternative to DB default)

class DropNote(db.Model):
    """
    SQLAlchemy ORM model for the 'drop_note' table.
    This mirrors the structure defined in schema.sql but is not
    currently used for querying in the routes (which use raw SQL).
    """
    __tablename__ = 'drop_note'

    # Define columns matching the schema.sql structure
    # Note: The 'default' here in Python might differ slightly from DB default behavior,
    # especially for UUIDs. The DB default 'gen_random_uuid()' is generally preferred.
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(TEXT, nullable=False)
    content = db.Column(TEXT, nullable=False)
    username = db.Column(TEXT, nullable=False)
    # Use ARRAY(TEXT) for PostgreSQL text arrays
    tags = db.Column(ARRAY(TEXT), nullable=True) # Nullable=True allows empty/no tags
    visibility = db.Column(TEXT, nullable=False, default='public')
    modification_code = db.Column(TEXT, unique=True, nullable=False)
    # Use TIMESTAMP(timezone=True) instead of TIMESTAMPTZ
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Add constraints if needed (though CHECK constraints are often handled in DB schema)
    # Example: __table_args__ = (db.CheckConstraint("visibility IN ('public', 'private')"),)

    def __repr__(self):
        """Provides a developer-friendly representation of the object."""
        return f'<DropNote {self.id} Title: "{self.title[:20]}...">'

    # Potential methods for ORM usage (not currently used):
    # def to_dict(self):
    #     """Returns a dictionary representation of the note."""
    #     return {
    #         'id': str(self.id),
    #         'title': self.title,
    #         'content': self.content,
    #         'username': self.username,
    #         'tags': self.tags or [],
    #         'visibility': self.visibility,
    #         'created_at': self.created_at.isoformat() if self.created_at else None,
    #         'updated_at': self.updated_at.isoformat() if self.updated_at else None,
    #         # Exclude modification_code by default
    #     }