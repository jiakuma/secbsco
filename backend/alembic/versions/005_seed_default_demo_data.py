"""005 seed default demo data

Revision ID: 005_seed_default_demo_data
Revises: 004_add_contract_info
Create Date: 2026-05-15

初始化默认演示数据：
- 3 个默认机构
- 1 个默认群组
- 3 个群组成员机构
- 5 个默认节点
- 5 个群组节点授权
- 3 个默认角色
- 4 个默认用户
- 3 个用户群组关系
- 4 个角色绑定
- 1 个默认合约信息
"""

from datetime import datetime
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '005_seed_default_demo_data'
down_revision = '004_add_contract_info'
branch_labels = None
depends_on = None

NOW = datetime(2026, 5, 15, 0, 0, 0)

# 密码哈希：passlib bcrypt("123456")
# 预计算值，避免运行时依赖，可在任何环境复现
DEFAULT_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsBLp8x4.s4Yb56r9pMcM7IcH4xW"


def _hash_password(password: str) -> str:
    """运行时动态生成哈希，如果 passlib 可用则使用，否则用预计算值"""
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)
    except ImportError:
        return DEFAULT_PASSWORD_HASH


def upgrade() -> None:
    conn = op.get_bind()

    # ==================================================
    # 1. 默认机构
    # ==================================================
    agencies_to_insert = [
        {
            "agency_code": "CDC_BEIJING",
            "agency_name": "北京市疾控中心",
            "agency_type": "cdc",
            "agency_level": "city",
            "region_code": "110000",
            "region_name": "北京市",
            "status": "active",
        },
        {
            "agency_code": "HOSPITAL_ALICE",
            "agency_name": "海淀区医院 Alice",
            "agency_type": "hospital",
            "agency_level": "county",
            "region_code": "110108",
            "region_name": "北京市海淀区",
            "status": "active",
        },
        {
            "agency_code": "HOSPITAL_BOB",
            "agency_name": "朝阳区医院 Bob",
            "agency_type": "hospital",
            "agency_level": "county",
            "region_code": "110105",
            "region_name": "北京市朝阳区",
            "status": "active",
        },
    ]

    agency_ids = {}
    for ag in agencies_to_insert:
        row = conn.execute(
            text("SELECT id FROM agency WHERE agency_code = :code"),
            {"code": ag["agency_code"]}
        ).fetchone()
        if row:
            agency_ids[ag["agency_code"]] = row[0]
        else:
            conn.execute(
                text("""
                    INSERT INTO agency (agency_code, agency_name, agency_type, agency_level,
                        region_code, region_name, status, created_at, updated_at)
                    VALUES (:agency_code, :agency_name, :agency_type, :agency_level,
                        :region_code, :region_name, :status, :created_at, :updated_at)
                """),
                {**ag, "created_at": NOW, "updated_at": NOW}
            )
            row = conn.execute(
                text("SELECT id FROM agency WHERE agency_code = :code"),
                {"code": ag["agency_code"]}
            ).fetchone()
            agency_ids[ag["agency_code"]] = row[0]

    cdc_id = agency_ids["CDC_BEIJING"]
    alice_id = agency_ids["HOSPITAL_ALICE"]
    bob_id = agency_ids["HOSPITAL_BOB"]

    # ==================================================
    # 2. 默认群组
    # ==================================================
    group_row = conn.execute(
        text("SELECT id FROM group_info WHERE group_code = :code"),
        {"code": "GROUP_FLU_BEIJING_2026"}
    ).fetchone()

    if group_row:
        group_id = group_row[0]
    else:
        conn.execute(
            text("""
                INSERT INTO group_info (group_code, group_name, group_level, region_code, region_name,
                    lead_agency_id, description, status, created_at, updated_at, activated_at)
                VALUES (:group_code, :group_name, :group_level, :region_code, :region_name,
                    :lead_agency_id, :description, :status, :created_at, :updated_at, :activated_at)
            """),
            {
                "group_code": "GROUP_FLU_BEIJING_2026",
                "group_name": "北京市跨区县流感样病例联合统计群组",
                "group_level": "city",
                "region_code": "110000",
                "region_name": "北京市",
                "lead_agency_id": cdc_id,
                "description": "用于演示多机构生物安全数据联合统计与联邦学习训练的默认群组",
                "status": "active",
                "created_at": NOW,
                "updated_at": NOW,
                "activated_at": NOW,
            }
        )
        group_row = conn.execute(
            text("SELECT id FROM group_info WHERE group_code = :code"),
            {"code": "GROUP_FLU_BEIJING_2026"}
        ).fetchone()
        group_id = group_row[0]

    # ==================================================
    # 3. 默认群组成员机构
    # ==================================================
    members = [
        {"agency_id": cdc_id, "member_role": "lead_agency", "is_lead": True},
        {"agency_id": alice_id, "member_role": "data_provider", "is_lead": False},
        {"agency_id": bob_id, "member_role": "data_provider", "is_lead": False},
    ]
    for m in members:
        exists = conn.execute(
            text("SELECT id FROM group_member WHERE group_id = :gid AND agency_id = :aid"),
            {"gid": group_id, "aid": m["agency_id"]}
        ).fetchone()
        if not exists:
            conn.execute(
                text("""
                    INSERT INTO group_member (group_id, agency_id, member_role, is_lead, join_status,
                        joined_at, created_at, updated_at)
                    VALUES (:group_id, :agency_id, :member_role, :is_lead, 'active',
                        :joined_at, :created_at, :updated_at)
                """),
                {
                    "group_id": group_id,
                    "agency_id": m["agency_id"],
                    "member_role": m["member_role"],
                    "is_lead": 1 if m["is_lead"] else 0,
                    "joined_at": NOW,
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )

    # ==================================================
    # 4. 默认节点
    # ==================================================
    nodes_to_insert = [
        {
            "node_code": "NODE_ALICE_DATA",
            "node_name": "Alice 数据节点",
            "agency_id": alice_id,
            "node_type": "data_node",
            "status": "active",
            "node_load_status": "idle",
            "health_check_url": "http://123.60.109.244:18180/health",
            "ray_address": None,
            "chain_type": None,
            "anchor_service_url": None,
            "contract_address": None,
        },
        {
            "node_code": "NODE_ALICE_COMPUTE",
            "node_name": "Alice 计算节点",
            "agency_id": alice_id,
            "node_type": "compute_node",
            "status": "active",
            "node_load_status": "idle",
            "health_check_url": "http://123.60.109.244:18181/health",
            "ray_address": "192.168.0.40:10001",
            "chain_type": None,
            "anchor_service_url": None,
            "contract_address": None,
        },
        {
            "node_code": "NODE_ALICE_BLOCKCHAIN",
            "node_name": "Alice 区块链存证节点",
            "agency_id": cdc_id,
            "node_type": "blockchain_node",
            "status": "active",
            "node_load_status": "idle",
            "health_check_url": "http://123.60.109.244:18080/health",
            "ray_address": None,
            "chain_type": "fisco_bcos",
            "anchor_service_url": "http://123.60.109.244:18080",
            "contract_address": "0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1",
        },
        {
            "node_code": "NODE_BOB_DATA",
            "node_name": "Bob 数据节点",
            "agency_id": bob_id,
            "node_type": "data_node",
            "status": "active",
            "node_load_status": "idle",
            "health_check_url": None,
            "ray_address": None,
            "chain_type": None,
            "anchor_service_url": None,
            "contract_address": None,
        },
        {
            "node_code": "NODE_BOB_COMPUTE",
            "node_name": "Bob 计算节点",
            "agency_id": bob_id,
            "node_type": "compute_node",
            "status": "active",
            "node_load_status": "idle",
            "health_check_url": None,
            "ray_address": "192.168.0.63",
            "chain_type": None,
            "anchor_service_url": None,
            "contract_address": None,
        },
    ]

    node_ids = {}
    for nd in nodes_to_insert:
        row = conn.execute(
            text("SELECT id FROM node WHERE node_code = :code"),
            {"code": nd["node_code"]}
        ).fetchone()
        if row:
            node_ids[nd["node_code"]] = row[0]
        else:
            conn.execute(
                text("""
                    INSERT INTO node (node_code, node_name, agency_id, node_type, status,
                        node_load_status, health_check_url, ray_address, chain_type,
                        anchor_service_url, contract_address,
                        max_concurrent_tasks, current_running_tasks,
                        created_at, updated_at)
                    VALUES (:node_code, :node_name, :agency_id, :node_type, :status,
                        :node_load_status, :health_check_url, :ray_address, :chain_type,
                        :anchor_service_url, :contract_address,
                        1, 0, :created_at, :updated_at)
                """),
                {**nd, "created_at": NOW, "updated_at": NOW}
            )
            row = conn.execute(
                text("SELECT id FROM node WHERE node_code = :code"),
                {"code": nd["node_code"]}
            ).fetchone()
            node_ids[nd["node_code"]] = row[0]

    # ==================================================
    # 5. 默认群组节点授权
    # ==================================================
    node_auth_map = {
        "NODE_ALICE_DATA": ("group_data", alice_id),
        "NODE_ALICE_COMPUTE": ("group_compute", alice_id),
        "NODE_ALICE_BLOCKCHAIN": ("group_blockchain", cdc_id),
        "NODE_BOB_DATA": ("group_data", bob_id),
        "NODE_BOB_COMPUTE": ("group_compute", bob_id),
    }
    for node_code, (usage_role, agency_id) in node_auth_map.items():
        nid = node_ids[node_code]
        exists = conn.execute(
            text("SELECT id FROM group_node WHERE group_id = :gid AND node_id = :nid"),
            {"gid": group_id, "nid": nid}
        ).fetchone()
        if not exists:
            conn.execute(
                text("""
                    INSERT INTO group_node (group_id, agency_id, node_id, node_usage_role,
                        auth_status, priority_level, max_concurrent_tasks,
                        authorized_at, created_at, updated_at)
                    VALUES (:group_id, :agency_id, :node_id, :node_usage_role,
                        'active', 1, 1, :authorized_at, :created_at, :updated_at)
                """),
                {
                    "group_id": group_id,
                    "agency_id": agency_id,
                    "node_id": nid,
                    "node_usage_role": usage_role,
                    "authorized_at": NOW,
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )

    # ==================================================
    # 6. 默认角色
    # ==================================================
    roles = [
        {"role_code": "admin", "role_name": "管理员", "description": "负责机构、群组、节点、用户等管理配置"},
        {"role_code": "user", "role_name": "业务用户", "description": "负责创建任务、执行任务、查看结果"},
        {"role_code": "governor", "role_name": "治理员", "description": "负责查看存证记录、执行链上校验"},
    ]
    for r in roles:
        exists = conn.execute(
            text("SELECT id FROM sys_role WHERE role_code = :code"),
            {"code": r["role_code"]}
        ).fetchone()
        if not exists:
            conn.execute(
                text("""
                    INSERT INTO sys_role (role_code, role_name, description, status, created_at, updated_at)
                    VALUES (:role_code, :role_name, :description, 'active', :created_at, :updated_at)
                """),
                {**r, "created_at": NOW, "updated_at": NOW}
            )

    # ==================================================
    # 7. 默认用户
    # ==================================================
    password_hash = _hash_password("123456")
    users_to_insert = [
        {"username": "platform_admin", "real_name": "平台管理员", "agency_id": cdc_id},
        {"username": "group_admin", "real_name": "群组管理员", "agency_id": cdc_id},
        {"username": "business_user", "real_name": "业务用户", "agency_id": alice_id},
        {"username": "chain_governor", "real_name": "区块链治理员", "agency_id": cdc_id},
    ]
    user_ids = {}
    for u in users_to_insert:
        row = conn.execute(
            text("SELECT id FROM sys_user WHERE username = :uname"),
            {"uname": u["username"]}
        ).fetchone()
        if row:
            user_ids[u["username"]] = row[0]
        else:
            conn.execute(
                text("""
                    INSERT INTO sys_user (username, password_hash, real_name, agency_id,
                        status, created_at, updated_at)
                    VALUES (:username, :password_hash, :real_name, :agency_id,
                        'active', :created_at, :updated_at)
                """),
                {**u, "password_hash": password_hash, "created_at": NOW, "updated_at": NOW}
            )
            row = conn.execute(
                text("SELECT id FROM sys_user WHERE username = :uname"),
                {"uname": u["username"]}
            ).fetchone()
            user_ids[u["username"]] = row[0]

    # ==================================================
    # 8. 默认用户群组关系
    # ==================================================
    group_users = ["group_admin", "business_user", "chain_governor"]
    for uname in group_users:
        uid = user_ids[uname]
        exists = conn.execute(
            text("SELECT id FROM sys_user_group WHERE user_id = :uid AND group_id = :gid"),
            {"uid": uid, "gid": group_id}
        ).fetchone()
        if not exists:
            # 获取 agency_id
            u_row = next(u for u in users_to_insert if u["username"] == uname)
            conn.execute(
                text("""
                    INSERT INTO sys_user_group (user_id, group_id, agency_id, join_status,
                        authorized_at, created_at, updated_at)
                    VALUES (:user_id, :group_id, :agency_id, 'active',
                        :authorized_at, :created_at, :updated_at)
                """),
                {
                    "user_id": uid,
                    "group_id": group_id,
                    "agency_id": u_row["agency_id"],
                    "authorized_at": NOW,
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )

    # ==================================================
    # 9. 默认角色绑定
    # ==================================================
    role_bindings = [
        {
            "username": "platform_admin",
            "role_code": "admin",
            "scope_type": "platform",
            "scope_id": None,
        },
        {
            "username": "group_admin",
            "role_code": "admin",
            "scope_type": "group",
            "scope_id": group_id,
        },
        {
            "username": "business_user",
            "role_code": "user",
            "scope_type": "group",
            "scope_id": group_id,
        },
        {
            "username": "chain_governor",
            "role_code": "governor",
            "scope_type": "group",
            "scope_id": group_id,
        },
    ]
    for rb in role_bindings:
        uid = user_ids[rb["username"]]
        # uk_user_role_scope: user_id + role_code + scope_type + scope_id
        # scope_id 可能为 NULL，需特殊处理
        if rb["scope_id"] is None:
            exists = conn.execute(
                text("""
                    SELECT id FROM sys_user_role_binding
                    WHERE user_id = :uid AND role_code = :rc AND scope_type = :st AND scope_id IS NULL
                """),
                {"uid": uid, "rc": rb["role_code"], "st": rb["scope_type"]}
            ).fetchone()
        else:
            exists = conn.execute(
                text("""
                    SELECT id FROM sys_user_role_binding
                    WHERE user_id = :uid AND role_code = :rc AND scope_type = :st AND scope_id = :sid
                """),
                {"uid": uid, "rc": rb["role_code"], "st": rb["scope_type"], "sid": rb["scope_id"]}
            ).fetchone()
        if not exists:
            conn.execute(
                text("""
                    INSERT INTO sys_user_role_binding (user_id, role_code, scope_type, scope_id,
                        status, created_at, updated_at)
                    VALUES (:user_id, :role_code, :scope_type, :scope_id,
                        'active', :created_at, :updated_at)
                """),
                {
                    "user_id": uid,
                    "role_code": rb["role_code"],
                    "scope_type": rb["scope_type"],
                    "scope_id": rb["scope_id"],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )

    # ==================================================
    # 10. 默认合约信息
    # ==================================================
    exists = conn.execute(
        text("""
            SELECT id FROM contract_info
            WHERE chain_type = 'fisco_bcos'
            AND contract_address = '0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1'
        """)
    ).fetchone()
    if not exists:
        conn.execute(
            text("""
                INSERT INTO contract_info (contract_name, contract_version, contract_address,
                    chain_type, status, deployed_at, description, created_at, updated_at)
                VALUES (:contract_name, :contract_version, :contract_address,
                    :chain_type, :status, :deployed_at, :description, :created_at, :updated_at)
            """),
            {
                "contract_name": "BioSafetyAnchorContract",
                "contract_version": "v1.0",
                "contract_address": "0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1",
                "chain_type": "fisco_bcos",
                "status": "active",
                "deployed_at": NOW,
                "description": "生物安全数据联合统计系统默认结果存证合约",
                "created_at": NOW,
                "updated_at": NOW,
            }
        )


def downgrade() -> None:
    conn = op.get_bind()

    # 按依赖顺序清理 seed 数据
    conn.execute(text("DELETE FROM contract_info WHERE contract_address = '0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1'"))
    conn.execute(text("DELETE FROM sys_user_role_binding WHERE user_id IN (SELECT id FROM sys_user WHERE username IN ('platform_admin','group_admin','business_user','chain_governor'))"))
    conn.execute(text("DELETE FROM sys_user_group WHERE user_id IN (SELECT id FROM sys_user WHERE username IN ('group_admin','business_user','chain_governor'))"))
    conn.execute(text("DELETE FROM sys_user WHERE username IN ('platform_admin','group_admin','business_user','chain_governor')"))
    conn.execute(text("DELETE FROM sys_role WHERE role_code IN ('admin','user','governor')"))
    conn.execute(text("DELETE FROM group_node WHERE group_id IN (SELECT id FROM group_info WHERE group_code = 'GROUP_FLU_BEIJING_2026')"))
    conn.execute(text("DELETE FROM node WHERE node_code IN ('NODE_ALICE_DATA','NODE_ALICE_COMPUTE','NODE_ALICE_BLOCKCHAIN','NODE_BOB_DATA','NODE_BOB_COMPUTE')"))
    conn.execute(text("DELETE FROM group_member WHERE group_id IN (SELECT id FROM group_info WHERE group_code = 'GROUP_FLU_BEIJING_2026')"))
    conn.execute(text("DELETE FROM group_info WHERE group_code = 'GROUP_FLU_BEIJING_2026'"))
    conn.execute(text("DELETE FROM agency WHERE agency_code IN ('CDC_BEIJING','HOSPITAL_ALICE','HOSPITAL_BOB')"))
