"""Initial creation of drop_note table and sequence

Revision ID: af0da1206605
Revises: fda94c133ca4
Create Date: 2025-05-28 23:49:56.540285

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'af0da1206605'
down_revision = 'fda94c133ca4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('drop_note',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('title', sa.TEXT(), nullable=False),
    sa.Column('content', sa.TEXT(), nullable=False),
    sa.Column('username', sa.TEXT(), nullable=False),
    sa.Column('tags', postgresql.ARRAY(sa.TEXT()), nullable=True),
    sa.Column('visibility', sa.TEXT(), nullable=False),
    sa.Column('modification_code', sa.TEXT(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('modification_code')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('drop_note')
    # ### end Alembic commands ###
