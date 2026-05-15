"""001 add org group node tables

Revision ID: 001_add_org_group_node
Revises: 
Create Date: 2026-05-15

扩展表：agency（增量）、node（增量）
新增表：group_info, group_member, group_node, group_lifecycle_log
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect, text

revision = '001_add_org_group_node'
down_revision = None
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(f"SELECT COUNT(*) FROM information_schema.COLUMNS "
             f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"),
        {"t": table, "c": column}
    )
    return result.scalar() > 0


def _has_index(conn, table: str, index_name: str) -> bool:
    result = conn.execute(
        text(f"SELECT COUNT(*) FROM information_schema.STATISTICS "
             f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND INDEX_NAME = :i"),
        {"t": table, "i": index_name}
    )
    return result.scalar() > 0


def upgrade() -> None:
    conn = op.get_bind()

    # ============================
    # 1. 扩展 agency 表（仅新增缺少的字段）
    # ============================
    agency_new_cols = {
        'agency_level': sa.Column('agency_level', sa.String(32), nullable=True, comment='机构层级'),
        'parent_agency_id': sa.Column('parent_agency_id', sa.BigInteger(), nullable=True, comment='上级机构ID'),
        'region_code': sa.Column('region_code', sa.String(64), nullable=True, comment='行政区划代码'),
        'region_name': sa.Column('region_name', sa.String(128), nullable=True, comment='行政区划名称'),
        'description': sa.Column('description', sa.Text(), nullable=True, comment='描述'),
    }
    with op.batch_alter_table('agency', schema=None) as batch_op:
        for col_name, col_def in agency_new_cols.items():
            if not _has_column(conn, 'agency', col_name):
                batch_op.add_column(col_def)
        if not _has_index(conn, 'agency', 'idx_agency_status'):
            batch_op.create_index('idx_agency_status', ['status'])
        if not _has_index(conn, 'agency', 'idx_agency_region_code'):
            batch_op.create_index('idx_agency_region_code', ['region_code'])

    # ============================
    # 2. 扩展 node 表（仅新增缺少的字段）
    # ============================
    node_new_cols = [
        ('node_role', sa.Column('node_role', sa.String(64), nullable=True, comment='节点角色')),
        ('service_url', sa.Column('service_url', sa.String(255), nullable=True, comment='服务URL')),
        ('internal_ip', sa.Column('internal_ip', sa.String(64), nullable=True, comment='内网IP')),
        ('public_ip', sa.Column('public_ip', sa.String(64), nullable=True, comment='公网IP')),
        ('health_check_url', sa.Column('health_check_url', sa.String(255), nullable=True, comment='健康检查URL')),
        ('ray_address', sa.Column('ray_address', sa.String(128), nullable=True, comment='Ray集群地址')),
        ('chain_type', sa.Column('chain_type', sa.String(64), nullable=True, comment='链类型')),
        ('chain_node_id', sa.Column('chain_node_id', sa.String(128), nullable=True, comment='链节点ID')),
        ('rpc_endpoint', sa.Column('rpc_endpoint', sa.String(255), nullable=True, comment='RPC接入点')),
        ('p2p_endpoint', sa.Column('p2p_endpoint', sa.String(255), nullable=True, comment='P2P接入点')),
        ('anchor_service_url', sa.Column('anchor_service_url', sa.String(255), nullable=True, comment='存证服务URL')),
        ('contract_address', sa.Column('contract_address', sa.String(128), nullable=True, comment='合约地址')),
        ('cert_id', sa.Column('cert_id', sa.String(128), nullable=True, comment='证书ID')),
        ('last_heartbeat_time', sa.Column('last_heartbeat_time', sa.DateTime(), nullable=True, comment='最后心跳时间')),
        ('cpu_total', sa.Column('cpu_total', sa.Integer(), nullable=True, comment='CPU总量')),
        ('memory_total', sa.Column('memory_total', sa.Integer(), nullable=True, comment='内存总量')),
        ('gpu_total', sa.Column('gpu_total', sa.Integer(), nullable=True, comment='GPU总量')),
        ('max_concurrent_tasks', sa.Column('max_concurrent_tasks', sa.Integer(), nullable=False, server_default='1', comment='最大并发任务数')),
        ('current_running_tasks', sa.Column('current_running_tasks', sa.Integer(), nullable=False, server_default='0', comment='当前运行任务数')),
        ('node_load_status', sa.Column('node_load_status', sa.String(32), nullable=False, server_default='idle', comment='负载状态')),
        ('resource_desc_json', sa.Column('resource_desc_json', mysql.JSON(), nullable=True, comment='资源描述JSON')),
    ]
    with op.batch_alter_table('node', schema=None) as batch_op:
        for col_name, col_def in node_new_cols:
            if not _has_column(conn, 'node', col_name):
                batch_op.add_column(col_def)
        if not _has_index(conn, 'node', 'idx_node_agency_id'):
            batch_op.create_index('idx_node_agency_id', ['agency_id'])
        if not _has_index(conn, 'node', 'idx_node_type'):
            batch_op.create_index('idx_node_type', ['node_type'])
        if not _has_index(conn, 'node', 'idx_node_status'):
            batch_op.create_index('idx_node_status', ['status'])
        if not _has_index(conn, 'node', 'idx_node_load_status'):
            batch_op.create_index('idx_node_load_status', ['node_load_status'])

    # ============================
    # 3. 新增 group_info 表
    # ============================
    if not inspect(conn).has_table('group_info'):
        op.create_table(
            'group_info',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('group_code', sa.String(64), nullable=False, unique=True, comment='群组编码'),
            sa.Column('group_name', sa.String(128), nullable=False, comment='群组名称'),
            sa.Column('group_level', sa.String(32), nullable=True, comment='群组层级'),
            sa.Column('region_code', sa.String(64), nullable=True, comment='行政区划代码'),
            sa.Column('region_name', sa.String(128), nullable=True, comment='行政区划名称'),
            sa.Column('lead_agency_id', sa.BigInteger(), nullable=True, comment='牵头机构ID'),
            sa.Column('description', sa.Text(), nullable=True, comment='描述'),
            sa.Column('status', sa.String(32), nullable=False, server_default='draft', comment='状态'),
            sa.Column('created_by', sa.BigInteger(), nullable=True, comment='创建用户ID'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('activated_at', sa.DateTime(), nullable=True),
            sa.Column('suspended_at', sa.DateTime(), nullable=True),
            sa.Column('resumed_at', sa.DateTime(), nullable=True),
            sa.Column('dissolving_at', sa.DateTime(), nullable=True),
            sa.Column('dissolved_at', sa.DateTime(), nullable=True),
            sa.Column('archived_at', sa.DateTime(), nullable=True),
            sa.Column('dissolve_reason', sa.Text(), nullable=True),
            sa.Column('archive_policy', sa.String(64), nullable=True),
        )
        op.create_index('idx_group_code', 'group_info', ['group_code'])
        op.create_index('idx_group_status', 'group_info', ['status'])
        op.create_index('idx_group_lead_agency_id', 'group_info', ['lead_agency_id'])
        op.create_index('idx_group_region_code', 'group_info', ['region_code'])

    # ============================
    # 4. 新增 group_member 表
    # ============================
    if not inspect(conn).has_table('group_member'):
        op.create_table(
            'group_member',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('group_id', sa.BigInteger(), nullable=False, comment='群组ID'),
            sa.Column('agency_id', sa.BigInteger(), nullable=False, comment='机构ID'),
            sa.Column('member_role', sa.String(32), nullable=False, server_default='participant'),
            sa.Column('is_lead', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('join_status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('joined_at', sa.DateTime(), nullable=True),
            sa.Column('removed_at', sa.DateTime(), nullable=True),
            sa.Column('disabled_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('group_id', 'agency_id', name='uk_group_member_group_agency'),
        )
        op.create_index('idx_group_member_group_id', 'group_member', ['group_id'])
        op.create_index('idx_group_member_agency_id', 'group_member', ['agency_id'])
        op.create_index('idx_group_member_status', 'group_member', ['join_status'])

    # ============================
    # 5. 新增 group_node 表
    # ============================
    if not inspect(conn).has_table('group_node'):
        op.create_table(
            'group_node',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('group_id', sa.BigInteger(), nullable=False),
            sa.Column('agency_id', sa.BigInteger(), nullable=False),
            sa.Column('node_id', sa.BigInteger(), nullable=False),
            sa.Column('node_usage_role', sa.String(32), nullable=False),
            sa.Column('auth_status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('resource_quota_json', mysql.JSON(), nullable=True),
            sa.Column('priority_level', sa.BigInteger(), nullable=False, server_default='1'),
            sa.Column('max_concurrent_tasks', sa.BigInteger(), nullable=False, server_default='1'),
            sa.Column('usage_policy', sa.String(64), nullable=True),
            sa.Column('authorized_by', sa.BigInteger(), nullable=True),
            sa.Column('authorized_at', sa.DateTime(), nullable=True),
            sa.Column('revoked_at', sa.DateTime(), nullable=True),
            sa.Column('archived_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('group_id', 'node_id', name='uk_group_node_group_node'),
        )
        op.create_index('idx_group_node_group_id', 'group_node', ['group_id'])
        op.create_index('idx_group_node_node_id', 'group_node', ['node_id'])
        op.create_index('idx_group_node_agency_id', 'group_node', ['agency_id'])
        op.create_index('idx_group_node_auth_status', 'group_node', ['auth_status'])
        op.create_index('idx_group_node_usage_role', 'group_node', ['node_usage_role'])

    # ============================
    # 6. 新增 group_lifecycle_log 表
    # ============================
    if not inspect(conn).has_table('group_lifecycle_log'):
        op.create_table(
            'group_lifecycle_log',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('group_id', sa.BigInteger(), nullable=False),
            sa.Column('event_type', sa.String(64), nullable=False),
            sa.Column('before_status', sa.String(32), nullable=True),
            sa.Column('after_status', sa.String(32), nullable=True),
            sa.Column('operator_user_id', sa.BigInteger(), nullable=True),
            sa.Column('operator_name', sa.String(64), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('detail_json', mysql.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_group_lifecycle_group_id', 'group_lifecycle_log', ['group_id'])
        op.create_index('idx_group_lifecycle_event_type', 'group_lifecycle_log', ['event_type'])
        op.create_index('idx_group_lifecycle_created_at', 'group_lifecycle_log', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()

    for tbl in ['group_lifecycle_log', 'group_node', 'group_member', 'group_info']:
        if inspect(conn).has_table(tbl):
            op.drop_table(tbl)

    # 回滚 node 表新增字段
    new_node_cols = ['node_role', 'service_url', 'internal_ip', 'public_ip', 'health_check_url',
                     'ray_address', 'chain_type', 'chain_node_id', 'rpc_endpoint', 'p2p_endpoint',
                     'anchor_service_url', 'contract_address', 'cert_id', 'last_heartbeat_time',
                     'cpu_total', 'memory_total', 'gpu_total', 'max_concurrent_tasks',
                     'current_running_tasks', 'node_load_status', 'resource_desc_json']
    with op.batch_alter_table('node', schema=None) as batch_op:
        for col in new_node_cols:
            if _has_column(conn, 'node', col):
                batch_op.drop_column(col)
        for idx in ['idx_node_agency_id', 'idx_node_type', 'idx_node_status', 'idx_node_load_status']:
            if _has_index(conn, 'node', idx):
                batch_op.drop_index(idx)

    # 回滚 agency 表（只删本次迁移新增的，description是原有字段不删）
    agency_added = ['agency_level', 'parent_agency_id', 'region_code', 'region_name']
    with op.batch_alter_table('agency', schema=None) as batch_op:
        for col in agency_added:
            if _has_column(conn, 'agency', col):
                batch_op.drop_column(col)
        for idx in ['idx_agency_status', 'idx_agency_region_code']:
            if _has_index(conn, 'agency', idx):
                batch_op.drop_index(idx)
