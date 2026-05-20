"""Add node agent control fields.

Revision ID: 006_add_node_agent_fields
Revises: 005_seed_default_demo_data
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = '006_add_node_agent_fields'
down_revision = '005_seed_default_demo_data'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('node', sa.Column('agent_url', sa.String(255), nullable=True, comment='节点Agent控制服务地址'))
    op.add_column('node', sa.Column('agent_token', sa.String(255), nullable=True, comment='节点Agent访问令牌'))
    op.add_column('node', sa.Column('last_check_at', sa.DateTime, nullable=True, comment='最近一次检测时间'))
    op.add_column('node', sa.Column('last_check_result', sa.JSON, nullable=True, comment='最近一次检测结果'))
    op.add_column('node', sa.Column('activation_status', sa.String(32), nullable=False, server_default='not_activated', comment='激活状态: not_activated/activating/activated/activation_failed'))
    op.add_column('node', sa.Column('activation_message', sa.Text, nullable=True, comment='激活说明'))


def downgrade():
    op.drop_column('node', 'activation_message')
    op.drop_column('node', 'activation_status')
    op.drop_column('node', 'last_check_result')
    op.drop_column('node', 'last_check_at')
    op.drop_column('node', 'agent_token')
    op.drop_column('node', 'agent_url')
