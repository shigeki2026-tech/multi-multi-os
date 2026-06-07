"""answer_rate_threshold_stats

Revision ID: aac1b4173d98
Revises: 64de86ec20a4
Create Date: 2026-06-07 17:48:28.742000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aac1b4173d98'
down_revision: Union[str, None] = '64de86ec20a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 閲覧用の中間集計テーブル。集計済みデータのみ保存（生CSV・個別明細は保存しない）。
    # 粒度: (stat_date, time_slot, skill_group, threshold_seconds)。threshold は 0/3/10/20/30。
    op.create_table(
        'answer_rate_threshold_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('stat_date', sa.Date(), nullable=False),
        sa.Column('time_slot', sa.Integer(), nullable=False),
        sa.Column('skill_group', sa.String(length=255), nullable=False),
        sa.Column('threshold_seconds', sa.Integer(), nullable=False),
        sa.Column('completed_count', sa.Integer(), nullable=False),
        sa.Column('valid_abandon_count', sa.Integer(), nullable=False),
        sa.Column('denominator', sa.Integer(), nullable=False),
        sa.Column('answer_rate', sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column('source_filename', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'stat_date', 'time_slot', 'skill_group', 'threshold_seconds',
            name='uq_arts_date_slot_group_threshold',
        ),
    )


def downgrade() -> None:
    op.drop_table('answer_rate_threshold_stats')
