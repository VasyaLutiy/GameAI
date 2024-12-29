"""Add character_mode to User

Revision ID: add_character_mode
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Добавляем колонку character_mode с значением по умолчанию 'default'
    op.add_column('users', 
        sa.Column('character_mode', sa.String(50), nullable=True, server_default='default')
    )

def downgrade():
    # Удаляем колонку при откате
    op.drop_column('users', 'character_mode')