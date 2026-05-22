"""extend dataset and stat_template fields

Revision ID: 008_extend_dataset_and_template
Revises: 007_add_delete_approval_fields
Create Date: 2026-05-20

"""
from alembic import op
import sqlalchemy as sa


revision = '008_extend_dataset_and_template'
down_revision = '007_add_delete_approval_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('dataset', sa.Column('node_id', sa.BigInteger(), nullable=True, comment='所属节点ID'))
    op.add_column('dataset', sa.Column('data_type', sa.String(32), nullable=True, comment='数据类型: file/database/api'))
    op.add_column('dataset', sa.Column('data_location', sa.String(512), nullable=True, comment='数据位置'))
    op.add_column('dataset', sa.Column('template_id', sa.BigInteger(), nullable=True, comment='数据模板ID'))
    op.add_column('dataset', sa.Column('version', sa.BigInteger(), nullable=False, server_default='1', comment='版本号'))
    op.add_column('dataset', sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'))

    op.create_index('idx_dataset_node_id', 'dataset', ['node_id'])
    op.create_index('idx_dataset_data_type', 'dataset', ['data_type'])

    op.add_column('stat_template', sa.Column('agency_id', sa.BigInteger(), nullable=True, comment='所属机构ID'))
    op.add_column('stat_template', sa.Column('scenario', sa.String(64), nullable=True, comment='适用场景'))
    op.add_column('stat_template', sa.Column('exec_mode', sa.String(32), nullable=True, comment='执行方式: auto/manual'))
    op.add_column('stat_template', sa.Column('output_type', sa.String(64), nullable=True, comment='输出结果类型'))
    op.add_column('stat_template', sa.Column('executor_config_json', sa.JSON(), nullable=True, comment='执行器配置'))
    op.add_column('stat_template', sa.Column('input_requirements_json', sa.JSON(), nullable=True, comment='输入要求'))
    op.add_column('stat_template', sa.Column('output_view_type', sa.String(64), nullable=True, comment='输出视图类型'))
    op.add_column('stat_template', sa.Column('template_hash', sa.String(128), nullable=True, comment='模板哈希'))
    op.add_column('stat_template', sa.Column('version', sa.BigInteger(), nullable=False, server_default='1', comment='版本号'))
    op.add_column('stat_template', sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建人ID'))

    op.create_index('idx_stat_template_agency_id', 'stat_template', ['agency_id'])
    op.create_index('idx_stat_template_scenario', 'stat_template', ['scenario'])


def downgrade():
    op.drop_index('idx_dataset_data_type', 'dataset')
    op.drop_index('idx_dataset_node_id', 'dataset')
    op.drop_column('dataset', 'created_by')
    op.drop_column('dataset', 'version')
    op.drop_column('dataset', 'template_id')
    op.drop_column('dataset', 'data_location')
    op.drop_column('dataset', 'data_type')
    op.drop_column('dataset', 'node_id')

    op.drop_index('idx_stat_template_scenario', 'stat_template')
    op.drop_index('idx_stat_template_agency_id', 'stat_template')
    op.drop_column('stat_template', 'created_by')
    op.drop_column('stat_template', 'version')
    op.drop_column('stat_template', 'template_hash')
    op.drop_column('stat_template', 'output_view_type')
    op.drop_column('stat_template', 'input_requirements_json')
    op.drop_column('stat_template', 'executor_config_json')
    op.drop_column('stat_template', 'output_type')
    op.drop_column('stat_template', 'exec_mode')
    op.drop_column('stat_template', 'scenario')
    op.drop_column('stat_template', 'agency_id')
