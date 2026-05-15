"""004 add contract info

Revision ID: 004_add_contract_info
Revises: 003_extend_task_result_chain
Create Date: 2026-05-15

新增表：
- contract_info
"""

from alembic import op
import sqlalchemy as sa

revision = '004_add_contract_info'
down_revision = '003_extend_task_result_chain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'contract_info',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('contract_name', sa.String(128), nullable=False, comment='合约名称'),
        sa.Column('contract_version', sa.String(64), nullable=True, comment='合约版本'),
        sa.Column('contract_address', sa.String(128), nullable=False, comment='合约地址'),
        sa.Column('chain_type', sa.String(64), nullable=False, server_default='fisco_bcos', comment='链类型'),
        sa.Column('status', sa.String(32), nullable=False, server_default='active', comment='状态'),
        sa.Column('deployed_at', sa.DateTime(), nullable=True, comment='部署时间'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.UniqueConstraint('chain_type', 'contract_address', name='uk_contract_chain_address'),
    )
    op.create_index('idx_contract_name', 'contract_info', ['contract_name'])
    op.create_index('idx_contract_address', 'contract_info', ['contract_address'])
    op.create_index('idx_contract_status', 'contract_info', ['status'])


def downgrade() -> None:
    op.drop_table('contract_info')
