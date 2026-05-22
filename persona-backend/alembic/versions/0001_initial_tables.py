"""initial tables

Revision ID: 0001
Revises:
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_table(
        'personas',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('profile_json', sa.JSON(), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_personas_user_id', 'personas', ['user_id'])
    op.create_table(
        'simulations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('persona_id', sa.String(), nullable=False),
        sa.Column('scenario_type', sa.String(), nullable=False),
        sa.Column('scenario_config', sa.JSON(), nullable=True),
        sa.Column('turns', sa.JSON(), nullable=True),
        sa.Column('savepoints', sa.JSON(), nullable=True),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['persona_id'], ['personas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_simulations_user_id', 'simulations', ['user_id'])


def downgrade() -> None:
    op.drop_table('simulations')
    op.drop_table('personas')
    op.drop_table('users')
