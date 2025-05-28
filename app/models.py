from . import db
from sqlalchemy.dialects.postgresql import UUID, ARRAY, TEXT
from sqlalchemy import TIMESTAMP, text, CheckConstraint # Import CheckConstraint

class DropNote(db.Model):
    __tablename__ = 'drop_note'

    id = db.Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    title = db.Column(TEXT, nullable=False)
    content = db.Column(TEXT, nullable=False)
    username = db.Column(TEXT, nullable=False)
    tags = db.Column(ARRAY(TEXT), nullable=True) # Check constraint will be in __table_args__
    visibility = db.Column(TEXT, nullable=False, default='public') # Check constraint in __table_args__
    modification_code = db.Column(TEXT, unique=True, nullable=False)
    created_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.current_timestamp())
    updated_at = db.Column(TIMESTAMP(timezone=True), nullable=False, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp()) # onupdate is for ORM, trigger for DB

    def __repr__(self):
        return f'<DropNote {self.id} Title: "{self.title[:20]}...">'

    __table_args__ = (
        CheckConstraint('array_length(tags, 1) <= 10', name='ck_drop_note_tags_length'),
        CheckConstraint("visibility IN ('public', 'private')", name='ck_drop_note_visibility_values'),
        # You can add other table-level arguments or multi-column constraints here
        # For example, if you wanted a schema specified: {'schema': 'myschema'}
    )