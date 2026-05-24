"""add_agentic_platform_tables

Revision ID: a1b2c3d4e5f6
Revises: f403f7f55f02
Create Date: 2026-05-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f403f7f55f02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Create `longitudinal_profile` table
    # -------------------------------------------------------------------------
    op.create_table(
        'longitudinal_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        # EncryptedJSON stored as Text at the DB level
        sa.Column('skill_history', sa.Text(), nullable=True),
        sa.Column('skill_averages', sa.Text(), nullable=True),
        sa.Column('skill_trends', sa.JSON(), nullable=True),
        sa.Column('github_last_indexed', sa.DateTime(), nullable=True),
        sa.Column('linkedin_last_indexed', sa.DateTime(), nullable=True),
        sa.Column('enrichment_sources', sa.JSON(), nullable=True),
        sa.Column('coaching_effectiveness', sa.JSON(), nullable=True),
        sa.Column('deletion_requested_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['user.id'], name='fk_longitudinal_profile_candidate_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id', name='uq_longitudinal_profile_candidate_id'),
    )
    op.create_index('ix_longitudinal_profile_candidate_id', 'longitudinal_profile', ['candidate_id'], unique=True)

    # -------------------------------------------------------------------------
    # 2. Create `interview_plan` table
    # -------------------------------------------------------------------------
    op.create_table(
        'interview_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('job_drive_id', sa.Integer(), nullable=True),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('phases', sa.JSON(), nullable=True),
        sa.Column('revision_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('revisions', sa.JSON(), nullable=True),
        sa.Column('generated_by', sa.String(length=50), nullable=False, server_default='planner_agent'),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_session.id'], name='fk_interview_plan_session_id'),
        sa.ForeignKeyConstraint(['job_drive_id'], ['job_drive.id'], name='fk_interview_plan_job_drive_id'),
        sa.ForeignKeyConstraint(['candidate_id'], ['user.id'], name='fk_interview_plan_candidate_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_interview_plan_session_id'),
    )
    op.create_index('ix_interview_plan_session_id', 'interview_plan', ['session_id'], unique=True)

    # -------------------------------------------------------------------------
    # 3. Create `violation_record` table
    # -------------------------------------------------------------------------
    op.create_table(
        'violation_record',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('violation_type', sa.String(length=100), nullable=False),
        sa.Column('detected_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        # EncryptedJSON stored as Text at the DB level
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('consent_granted', sa.Boolean(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_session.id'], name='fk_violation_record_session_id'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_violation_record_session_id', 'violation_record', ['session_id'])
    op.create_index('ix_violation_record_violation_type', 'violation_record', ['violation_type'])
    op.create_index('ix_violation_record_detected_at', 'violation_record', ['detected_at'])

    # -------------------------------------------------------------------------
    # 4. Create `coaching_plan` table
    # -------------------------------------------------------------------------
    op.create_table(
        'coaching_plan',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        # EncryptedJSON stored as Text at the DB level
        sa.Column('skill_gaps', sa.Text(), nullable=True),
        sa.Column('top_3_gaps', sa.JSON(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('notification_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_session.id'], name='fk_coaching_plan_session_id'),
        sa.ForeignKeyConstraint(['candidate_id'], ['user.id'], name='fk_coaching_plan_candidate_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', name='uq_coaching_plan_session_id'),
    )
    op.create_index('ix_coaching_plan_session_id', 'coaching_plan', ['session_id'], unique=True)
    op.create_index('ix_coaching_plan_candidate_id', 'coaching_plan', ['candidate_id'])

    # -------------------------------------------------------------------------
    # 5. Create `match_result` table
    # -------------------------------------------------------------------------
    op.create_table(
        'match_result',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_drive_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('is_top_match', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('explanation', sa.JSON(), nullable=True),
        sa.Column('score_breakdown', sa.JSON(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['user.id'], name='fk_match_result_candidate_id'),
        sa.ForeignKeyConstraint(['job_drive_id'], ['job_drive.id'], name='fk_match_result_job_drive_id'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_session.id'], name='fk_match_result_session_id'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_match_result_candidate_id', 'match_result', ['candidate_id'])
    op.create_index('ix_match_result_job_drive_id', 'match_result', ['job_drive_id'])
    op.create_index('ix_match_drive_score', 'match_result', ['job_drive_id', 'match_score'])

    # -------------------------------------------------------------------------
    # 6. Create `candidate_workflow` table
    # -------------------------------------------------------------------------
    op.create_table(
        'candidate_workflow',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_drive_id', sa.Integer(), nullable=False),
        sa.Column('current_state', sa.String(length=50), nullable=False, server_default='invited'),
        sa.Column('transition_history', sa.JSON(), nullable=True),
        sa.Column('last_reminder_sent_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('decision', sa.String(length=50), nullable=True),
        sa.Column('decided_by', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['candidate_id'], ['user.id'], name='fk_candidate_workflow_candidate_id'),
        sa.ForeignKeyConstraint(['job_drive_id'], ['job_drive.id'], name='fk_candidate_workflow_job_drive_id'),
        sa.ForeignKeyConstraint(['decided_by'], ['user.id'], name='fk_candidate_workflow_decided_by'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_candidate_workflow_candidate_id', 'candidate_workflow', ['candidate_id'])
    op.create_index('ix_candidate_workflow_job_drive_id', 'candidate_workflow', ['job_drive_id'])
    op.create_index('ix_candidate_workflow_current_state', 'candidate_workflow', ['current_state'])
    op.create_index(
        'ix_workflow_candidate_drive',
        'candidate_workflow',
        ['candidate_id', 'job_drive_id'],
        unique=True,
    )

    # -------------------------------------------------------------------------
    # 7. Create `trace_entries` table
    # -------------------------------------------------------------------------
    op.create_table(
        'trace_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('workflow_id', sa.Integer(), nullable=True),
        sa.Column('candidate_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('input_summary', sa.Text(), nullable=True),
        sa.Column('reasoning_summary', sa.Text(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('raw_input', sa.JSON(), nullable=True),
        sa.Column('raw_output', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trace_entries_agent_name', 'trace_entries', ['agent_name'])
    op.create_index('ix_trace_entries_action_type', 'trace_entries', ['action_type'])
    op.create_index('ix_trace_entries_session_id', 'trace_entries', ['session_id'])
    op.create_index('ix_trace_entries_workflow_id', 'trace_entries', ['workflow_id'])
    op.create_index('ix_trace_entries_candidate_id', 'trace_entries', ['candidate_id'])
    op.create_index('ix_trace_entries_timestamp', 'trace_entries', ['timestamp'])
    op.create_index('ix_trace_agent_session', 'trace_entries', ['agent_name', 'session_id'])
    op.create_index('ix_trace_timestamp', 'trace_entries', ['timestamp'])

    # -------------------------------------------------------------------------
    # 8. Add new columns to `interview_session`
    #    Use batch_alter_table for SQLite compatibility
    # -------------------------------------------------------------------------
    with op.batch_alter_table('interview_session') as batch_op:
        batch_op.add_column(sa.Column('interview_plan_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('workflow_state', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('empathy_timeline', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('qa_quality_score', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('proctor_consent_granted', sa.Boolean(), nullable=True))
        batch_op.create_foreign_key(
            'fk_interview_session_interview_plan_id',
            'interview_plan',
            ['interview_plan_id'],
            ['id'],
        )

    # -------------------------------------------------------------------------
    # 9. Add new columns to `student_profile`
    #    Use batch_alter_table for SQLite compatibility
    # -------------------------------------------------------------------------
    with op.batch_alter_table('student_profile') as batch_op:
        batch_op.add_column(sa.Column('longitudinal_profile_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('research_enriched_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key(
            'fk_student_profile_longitudinal_profile_id',
            'longitudinal_profile',
            ['longitudinal_profile_id'],
            ['id'],
        )


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # Reverse order: columns first, then tables (reverse of upgrade)
    # -------------------------------------------------------------------------

    # 9. Remove new columns from `student_profile`
    with op.batch_alter_table('student_profile') as batch_op:
        batch_op.drop_constraint('fk_student_profile_longitudinal_profile_id', type_='foreignkey')
        batch_op.drop_column('research_enriched_at')
        batch_op.drop_column('longitudinal_profile_id')

    # 8. Remove new columns from `interview_session`
    with op.batch_alter_table('interview_session') as batch_op:
        batch_op.drop_constraint('fk_interview_session_interview_plan_id', type_='foreignkey')
        batch_op.drop_column('proctor_consent_granted')
        batch_op.drop_column('qa_quality_score')
        batch_op.drop_column('empathy_timeline')
        batch_op.drop_column('workflow_state')
        batch_op.drop_column('interview_plan_id')

    # 7. Drop `trace_entries`
    op.drop_index('ix_trace_timestamp', table_name='trace_entries')
    op.drop_index('ix_trace_agent_session', table_name='trace_entries')
    op.drop_index('ix_trace_entries_timestamp', table_name='trace_entries')
    op.drop_index('ix_trace_entries_candidate_id', table_name='trace_entries')
    op.drop_index('ix_trace_entries_workflow_id', table_name='trace_entries')
    op.drop_index('ix_trace_entries_session_id', table_name='trace_entries')
    op.drop_index('ix_trace_entries_action_type', table_name='trace_entries')
    op.drop_index('ix_trace_entries_agent_name', table_name='trace_entries')
    op.drop_table('trace_entries')

    # 6. Drop `candidate_workflow`
    op.drop_index('ix_workflow_candidate_drive', table_name='candidate_workflow')
    op.drop_index('ix_candidate_workflow_current_state', table_name='candidate_workflow')
    op.drop_index('ix_candidate_workflow_job_drive_id', table_name='candidate_workflow')
    op.drop_index('ix_candidate_workflow_candidate_id', table_name='candidate_workflow')
    op.drop_table('candidate_workflow')

    # 5. Drop `match_result`
    op.drop_index('ix_match_drive_score', table_name='match_result')
    op.drop_index('ix_match_result_job_drive_id', table_name='match_result')
    op.drop_index('ix_match_result_candidate_id', table_name='match_result')
    op.drop_table('match_result')

    # 4. Drop `coaching_plan`
    op.drop_index('ix_coaching_plan_candidate_id', table_name='coaching_plan')
    op.drop_index('ix_coaching_plan_session_id', table_name='coaching_plan')
    op.drop_table('coaching_plan')

    # 3. Drop `violation_record`
    op.drop_index('ix_violation_record_detected_at', table_name='violation_record')
    op.drop_index('ix_violation_record_violation_type', table_name='violation_record')
    op.drop_index('ix_violation_record_session_id', table_name='violation_record')
    op.drop_table('violation_record')

    # 2. Drop `interview_plan`
    op.drop_index('ix_interview_plan_session_id', table_name='interview_plan')
    op.drop_table('interview_plan')

    # 1. Drop `longitudinal_profile`
    op.drop_index('ix_longitudinal_profile_candidate_id', table_name='longitudinal_profile')
    op.drop_table('longitudinal_profile')
