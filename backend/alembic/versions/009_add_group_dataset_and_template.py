"""add group_dataset and group_task_template tables

Revision ID: 009_add_group_dataset_and_template
Revises: 008_extend_dataset_and_template
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa


revision = '009_add_group_dataset_and_template'
down_revision = '008_extend_dataset_and_template'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'group_dataset',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.BigInteger(), nullable=False, comment='群组ID'),
        sa.Column('agency_id', sa.BigInteger(), nullable=False, comment='机构ID'),
        sa.Column('dataset_id', sa.BigInteger(), nullable=False, comment='数据集ID'),
        sa.Column('auth_status', sa.String(32), nullable=False, server_default='active', comment='授权状态: active/revoked'),
        sa.Column('authorized_by', sa.BigInteger(), nullable=True, comment='授权人用户ID'),
        sa.Column('authorized_at', sa.DateTime(), nullable=True, comment='授权时间'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='撤销时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'dataset_id', name='uk_group_dataset_group_dataset'),
    )
    op.create_index('idx_group_dataset_group_id', 'group_dataset', ['group_id'])
    op.create_index('idx_group_dataset_dataset_id', 'group_dataset', ['dataset_id'])
    op.create_index('idx_group_dataset_agency_id', 'group_dataset', ['agency_id'])
    op.create_index('idx_group_dataset_auth_status', 'group_dataset', ['auth_status'])

    op.create_table(
        'group_task_template',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.BigInteger(), nullable=False, comment='群组ID'),
        sa.Column('agency_id', sa.BigInteger(), nullable=True, comment='机构ID'),
        sa.Column('template_id', sa.BigInteger(), nullable=False, comment='任务模板ID'),
        sa.Column('auth_status', sa.String(32), nullable=False, server_default='active', comment='授权状态: active/revoked'),
        sa.Column('authorized_by', sa.BigInteger(), nullable=True, comment='授权人用户ID'),
        sa.Column('authorized_at', sa.DateTime(), nullable=True, comment='授权时间'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='撤销时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'template_id', name='uk_group_task_template_group_template'),
    )
    op.create_index('idx_group_task_template_group_id', 'group_task_template', ['group_id'])
    op.create_index('idx_group_task_template_template_id', 'group_task_template', ['template_id'])
    op.create_index('idx_group_task_template_agency_id', 'group_task_template', ['agency_id'])
    op.create_index('idx_group_task_template_auth_status', 'group_task_template', ['auth_status'])


def downgrade():
    op.drop_index('idx_group_task_template_auth_status', 'group_task_template')
    op.drop_index('idx_group_task_template_agency_id', 'group_task_template')
    op.drop_index('idx_group_task_template_template_id', 'group_task_template')
    op.drop_index('idx_group_task_template_group_id', 'group_task_template')
    op.drop_table('group_task_template')

    op.drop_index('idx_group_dataset_auth_status', 'group_dataset')
    op.drop_index('idx_group_dataset_agency_id', 'group_dataset')
    op.drop_index('idx_group_dataset_dataset_id', 'group_dataset')
    op.drop_index('idx_group_dataset_group_id', 'group_dataset')
    op.drop_table('group_dataset')
