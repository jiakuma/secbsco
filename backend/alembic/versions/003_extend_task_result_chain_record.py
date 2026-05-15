"""003 extend task result chain record

Revision ID: 003_extend_task_result_chain
Revises: 002_add_user_role_scope
Create Date: 2026-05-15

扩展表（增量）：task, task_result, chain_record
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text

revision = '003_extend_task_result_chain'
down_revision = '002_add_user_role_scope'
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text("SELECT COUNT(*) FROM information_schema.COLUMNS "
             "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"),
        {"t": table, "c": column}
    )
    return result.scalar() > 0


def _has_index(conn, table: str, index_name: str) -> bool:
    result = conn.execute(
        text("SELECT COUNT(*) FROM information_schema.STATISTICS "
             "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i"),
        {"t": table, "i": index_name}
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # ============================
    # 1. 扩展 task 表（增量）
    # ============================
    task_new_cols = [
        ('group_id', sa.Column('group_id', sa.BigInteger(), nullable=True, comment='所属群组ID')),
        ('lead_agency_id', sa.Column('lead_agency_id', sa.BigInteger(), nullable=True, comment='牵头机构ID')),
        ('execution_mode', sa.Column('execution_mode', sa.String(32), nullable=True, comment='执行模式')),
        ('selected_node_json', sa.Column('selected_node_json', mysql.JSON(), nullable=True, comment='选定节点JSON')),
    ]
    with op.batch_alter_table('task', schema=None) as batch_op:
        for col_name, col_def in task_new_cols:
            if not _has_column(conn, 'task', col_name):
                batch_op.add_column(col_def)
        if not _has_index(conn, 'task', 'idx_task_group_id'):
            batch_op.create_index('idx_task_group_id', ['group_id'])
        if not _has_index(conn, 'task', 'idx_task_status'):
            batch_op.create_index('idx_task_status', ['status'])

    # ============================
    # 2. 扩展 task_result 表（增量）
    # ============================
    tr_new_cols = [
        ('group_id', sa.Column('group_id', sa.BigInteger(), nullable=True, comment='所属群组ID')),
        ('agency_id', sa.Column('agency_id', sa.BigInteger(), nullable=True, comment='所属机构ID')),
        ('task_type', sa.Column('task_type', sa.String(64), nullable=True, comment='任务类型')),
        ('result_version', sa.Column('result_version', sa.Integer(), nullable=False, server_default='1', comment='结果版本号')),
        ('anchor_status', sa.Column('anchor_status', sa.String(32), nullable=True, comment='上链状态')),
        ('anchor_time', sa.Column('anchor_time', sa.DateTime(), nullable=True, comment='上链时间')),
        ('chain_record_id', sa.Column('chain_record_id', sa.BigInteger(), nullable=True, comment='存证记录ID')),
    ]
    with op.batch_alter_table('task_result', schema=None) as batch_op:
        for col_name, col_def in tr_new_cols:
            if not _has_column(conn, 'task_result', col_name):
                batch_op.add_column(col_def)
        if not _has_index(conn, 'task_result', 'idx_task_result_group_id'):
            batch_op.create_index('idx_task_result_group_id', ['group_id'])
        if not _has_index(conn, 'task_result', 'idx_task_result_anchor_status'):
            batch_op.create_index('idx_task_result_anchor_status', ['anchor_status'])

    # ============================
    # 3. 扩展 chain_record 表（增量）
    # ============================
    cr_new_cols = [
        ('anchor_id', sa.Column('anchor_id', sa.String(128), nullable=True, comment='存证业务ID')),
        ('group_id', sa.Column('group_id', sa.BigInteger(), nullable=True, comment='所属群组ID')),
        ('agency_id', sa.Column('agency_id', sa.BigInteger(), nullable=True, comment='所属机构ID')),
        ('task_id', sa.Column('task_id', sa.BigInteger(), nullable=True, comment='关联任务ID')),
        ('result_id', sa.Column('result_id', sa.BigInteger(), nullable=True, comment='关联结果ID')),
        ('dataset_id', sa.Column('dataset_id', sa.BigInteger(), nullable=True, comment='关联数据集ID')),
        ('contract_name', sa.Column('contract_name', sa.String(128), nullable=True, comment='合约名称')),
        ('contract_version', sa.Column('contract_version', sa.String(64), nullable=True, comment='合约版本')),
        ('verify_status', sa.Column('verify_status', sa.String(32), nullable=True, comment='验证状态')),
        ('last_verify_time', sa.Column('last_verify_time', sa.DateTime(), nullable=True, comment='最后验证时间')),
        ('verify_detail_json', sa.Column('verify_detail_json', mysql.JSON(), nullable=True, comment='验证详情JSON')),
        ('updated_at', sa.Column('updated_at', sa.DateTime(), nullable=True, comment='更新时间')),
    ]
    with op.batch_alter_table('chain_record', schema=None) as batch_op:
        for col_name, col_def in cr_new_cols:
            if not _has_column(conn, 'chain_record', col_name):
                batch_op.add_column(col_def)
        if not _has_index(conn, 'chain_record', 'idx_chain_record_group_id'):
            batch_op.create_index('idx_chain_record_group_id', ['group_id'])
        if not _has_index(conn, 'chain_record', 'idx_chain_record_task_id'):
            batch_op.create_index('idx_chain_record_task_id', ['task_id'])
        if not _has_index(conn, 'chain_record', 'idx_chain_record_verify_status'):
            batch_op.create_index('idx_chain_record_verify_status', ['verify_status'])


def downgrade() -> None:
    conn = op.get_bind()

    cr_added = ['anchor_id', 'group_id', 'agency_id', 'task_id', 'result_id', 'dataset_id',
                'contract_name', 'contract_version', 'verify_status', 'last_verify_time',
                'verify_detail_json', 'updated_at']
    with op.batch_alter_table('chain_record', schema=None) as batch_op:
        for col in cr_added:
            if _has_column(conn, 'chain_record', col):
                batch_op.drop_column(col)
        for idx in ['idx_chain_record_group_id', 'idx_chain_record_task_id', 'idx_chain_record_verify_status']:
            if _has_index(conn, 'chain_record', idx):
                batch_op.drop_index(idx)

    tr_added = ['group_id', 'agency_id', 'task_type', 'result_version', 'anchor_status', 'anchor_time', 'chain_record_id']
    with op.batch_alter_table('task_result', schema=None) as batch_op:
        for col in tr_added:
            if _has_column(conn, 'task_result', col):
                batch_op.drop_column(col)
        for idx in ['idx_task_result_group_id', 'idx_task_result_anchor_status']:
            if _has_index(conn, 'task_result', idx):
                batch_op.drop_index(idx)

    task_added = ['group_id', 'lead_agency_id', 'execution_mode', 'selected_node_json']
    with op.batch_alter_table('task', schema=None) as batch_op:
        for col in task_added:
            if _has_column(conn, 'task', col):
                batch_op.drop_column(col)
        for idx in ['idx_task_group_id', 'idx_task_status']:
            if _has_index(conn, 'task', idx):
                batch_op.drop_index(idx)
