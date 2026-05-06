"""enhance_interview_session_for_skill_matrix

Revision ID: e5e168a2216e
Revises: 5bf8ec63040f
Create Date: 2026-05-06 21:46:19.963117

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e168a2216e'
down_revision: Union[str, None] = '5bf8ec63040f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enhanced skill matrix and AI transparency columns
    op.add_column('interview_session', sa.Column('skill_matrix', sa.JSON(), nullable=True))
    op.add_column('interview_session', sa.Column('confidence_scores', sa.JSON(), nullable=True))
    op.add_column('interview_session', sa.Column('evidence_log', sa.JSON(), nullable=True))
    op.add_column('interview_session', sa.Column('agent_states', sa.JSON(), nullable=True))
    op.add_column('interview_session', sa.Column('bias_metrics', sa.JSON(), nullable=True))
    op.add_column('interview_session', sa.Column('question_difficulty', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove enhanced columns
    op.drop_column('interview_session', 'question_difficulty')
    op.drop_column('interview_session', 'bias_metrics')
    op.drop_column('interview_session', 'agent_states')
    op.drop_column('interview_session', 'evidence_log')
    op.drop_column('interview_session', 'confidence_scores')
    op.drop_column('interview_session', 'skill_matrix')
