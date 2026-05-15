"""002 add user role scope tables

Revision ID: 002_add_user_role_scope
Revises: 001_add_org_group_node
Create Date: 2026-05-15

扩展表：sys_user（增量）
新增表：sys_role, sys_user_group, sys_user_role_binding, sys_user_operate_log
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import inspect, text

revision = '002_add_user_role_scope'
down_revision = '001_add_org_group_node'
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
    # 1. 扩展 sys_user 表（增量）
    # ============================
    # 已有字段：id, agency_id, username, password_hash, real_name, role_code, status, last_login_at, created_at, updated_at
    user_new_cols = [
        ('phone', sa.Column('phone', sa.String(64), nullable=True, comment='手机号')),
        ('email', sa.Column('email', sa.String(128), nullable=True, comment='邮箱')),
        ('last_login_time', sa.Column('last_login_time', sa.DateTime(), nullable=True, comment='最后登录时间')),
        ('last_login_ip', sa.Column('last_login_ip', sa.String(64), nullable=True, comment='最后登录IP')),
    ]
    with op.batch_alter_table('sys_user', schema=None) as batch_op:
        for col_name, col_def in user_new_cols:
            if not _has_column(conn, 'sys_user', col_name):
                batch_op.add_column(col_def)
        # role_code 改为可空（兼容旧数据）
        batch_op.alter_column('role_code',
                               existing_type=sa.String(64),
                               nullable=True)
        if not _has_index(conn, 'sys_user', 'idx_sys_user_username'):
            batch_op.create_index('idx_sys_user_username', ['username'])
        if not _has_index(conn, 'sys_user', 'idx_sys_user_agency_id'):
            batch_op.create_index('idx_sys_user_agency_id', ['agency_id'])
        if not _has_index(conn, 'sys_user', 'idx_sys_user_status'):
            batch_op.create_index('idx_sys_user_status', ['status'])

    # ============================
    # 2. 新增 sys_role 表
    # ============================
    if not inspect(conn).has_table('sys_role'):
        op.create_table(
            'sys_role',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('role_code', sa.String(32), nullable=False, unique=True, comment='角色编码'),
            sa.Column('role_name', sa.String(64), nullable=False, comment='角色名称'),
            sa.Column('description', sa.Text(), nullable=True, comment='描述'),
            sa.Column('status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_sys_role_code', 'sys_role', ['role_code'])
        op.create_index('idx_sys_role_status', 'sys_role', ['status'])

    # ============================
    # 3. 新增 sys_user_group 表
    # ============================
    if not inspect(conn).has_table('sys_user_group'):
        op.create_table(
            'sys_user_group',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('group_id', sa.BigInteger(), nullable=False),
            sa.Column('agency_id', sa.BigInteger(), nullable=True),
            sa.Column('join_status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('authorized_by', sa.BigInteger(), nullable=True),
            sa.Column('authorized_at', sa.DateTime(), nullable=True),
            sa.Column('disabled_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('user_id', 'group_id', name='uk_sys_user_group_user_group'),
        )
        op.create_index('idx_sys_user_group_user_id', 'sys_user_group', ['user_id'])
        op.create_index('idx_sys_user_group_group_id', 'sys_user_group', ['group_id'])
        op.create_index('idx_sys_user_group_agency_id', 'sys_user_group', ['agency_id'])
        op.create_index('idx_sys_user_group_status', 'sys_user_group', ['join_status'])

    # ============================
    # 4. 新增 sys_user_role_binding 表
    # ============================
    if not inspect(conn).has_table('sys_user_role_binding'):
        op.create_table(
            'sys_user_role_binding',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.BigInteger(), nullable=False),
            sa.Column('role_code', sa.String(32), nullable=False),
            sa.Column('scope_type', sa.String(32), nullable=False),
            sa.Column('scope_id', sa.BigInteger(), nullable=True),
            sa.Column('status', sa.String(32), nullable=False, server_default='active'),
            sa.Column('created_by', sa.BigInteger(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('disabled_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('user_id', 'role_code', 'scope_type', 'scope_id', name='uk_user_role_scope'),
        )
        op.create_index('idx_user_role_binding_user_id', 'sys_user_role_binding', ['user_id'])
        op.create_index('idx_user_role_binding_role_code', 'sys_user_role_binding', ['role_code'])
        op.create_index('idx_user_role_binding_scope', 'sys_user_role_binding', ['scope_type', 'scope_id'])
        op.create_index('idx_user_role_binding_status', 'sys_user_role_binding', ['status'])

    # ============================
    # 5. 新增 sys_user_operate_log 表
    # ============================
    if not inspect(conn).has_table('sys_user_operate_log'):
        op.create_table(
            'sys_user_operate_log',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.BigInteger(), nullable=True),
            sa.Column('username', sa.String(64), nullable=True),
            sa.Column('operation_type', sa.String(64), nullable=False),
            sa.Column('resource_type', sa.String(64), nullable=True),
            sa.Column('resource_id', sa.BigInteger(), nullable=True),
            sa.Column('group_id', sa.BigInteger(), nullable=True),
            sa.Column('agency_id', sa.BigInteger(), nullable=True),
            sa.Column('request_path', sa.String(255), nullable=True),
            sa.Column('request_method', sa.String(16), nullable=True),
            sa.Column('request_params', mysql.JSON(), nullable=True),
            sa.Column('result_status', sa.String(32), nullable=True),
            sa.Column('ip_address', sa.String(64), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('idx_operate_log_user_id', 'sys_user_operate_log', ['user_id'])
        op.create_index('idx_operate_log_group_id', 'sys_user_operate_log', ['group_id'])
        op.create_index('idx_operate_log_agency_id', 'sys_user_operate_log', ['agency_id'])
        op.create_index('idx_operate_log_operation_type', 'sys_user_operate_log', ['operation_type'])
        op.create_index('idx_operate_log_created_at', 'sys_user_operate_log', ['created_at'])


def downgrade() -> None:
    conn = op.get_bind()

    for tbl in ['sys_user_operate_log', 'sys_user_role_binding', 'sys_user_group', 'sys_role']:
        if inspect(conn).has_table(tbl):
            op.drop_table(tbl)

    user_added = ['phone', 'email', 'last_login_time', 'last_login_ip']
    with op.batch_alter_table('sys_user', schema=None) as batch_op:
        for col in user_added:
            if _has_column(conn, 'sys_user', col):
                batch_op.drop_column(col)
        for idx in ['idx_sys_user_username', 'idx_sys_user_agency_id', 'idx_sys_user_status']:
            if _has_index(conn, 'sys_user', idx):
                batch_op.drop_index(idx)
        batch_op.alter_column('role_code',
                               existing_type=sa.String(64),
                               nullable=False)
