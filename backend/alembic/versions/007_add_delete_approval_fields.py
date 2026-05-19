"""add delete approval fields to group_info

Revision ID: 007_add_delete_approval_fields
Revises: 006_add_node_agent_fields
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa


revision = '007_add_delete_approval_fields'
down_revision = '006_add_node_agent_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('group_info', sa.Column('delete_approval_status', sa.String(32), nullable=False, server_default='none', comment='删除审批状态'))
    op.add_column('group_info', sa.Column('delete_approval_agency_id', sa.BigInteger(), nullable=True, comment='删除审批机构ID'))
    op.add_column('group_info', sa.Column('delete_requested_by', sa.BigInteger(), nullable=True, comment='删除申请人ID'))
    op.add_column('group_info', sa.Column('delete_requested_at', sa.DateTime(), nullable=True, comment='删除申请时间'))
    op.add_column('group_info', sa.Column('delete_approved_by', sa.BigInteger(), nullable=True, comment='删除审批通过人ID'))
    op.add_column('group_info', sa.Column('delete_approved_at', sa.DateTime(), nullable=True, comment='删除审批通过时间'))
    op.add_column('group_info', sa.Column('delete_rejected_by', sa.BigInteger(), nullable=True, comment='删除驳回人ID'))
    op.add_column('group_info', sa.Column('delete_rejected_at', sa.DateTime(), nullable=True, comment='删除驳回时间'))
    op.add_column('group_info', sa.Column('delete_reject_reason', sa.Text(), nullable=True, comment='删除驳回原因'))


def downgrade():
    op.drop_column('group_info', 'delete_reject_reason')
    op.drop_column('group_info', 'delete_rejected_at')
    op.drop_column('group_info', 'delete_rejected_by')
    op.drop_column('group_info', 'delete_approved_at')
    op.drop_column('group_info', 'delete_approved_by')
    op.drop_column('group_info', 'delete_requested_at')
    op.drop_column('group_info', 'delete_requested_by')
    op.drop_column('group_info', 'delete_approval_agency_id')
    op.drop_column('group_info', 'delete_approval_status')
