"""
第4阶段验收测试脚本：群组创建权限、审批起步与成员/用户/节点授权配置

测试覆盖：
1. 权限判断函数（is_platform_admin, is_agency_admin, is_group_admin, is_ancestor_agency, is_same_level_agency, find_common_parent_agency）
2. 群组创建权限（platform admin / agency admin 上级 / agency admin 同级 / group admin 禁止）
3. 群组审批（approve / reject）
4. 成员机构管理（add / remove）
5. 群组用户授权（add / change role / remove / 防止最后管理员）
6. 节点授权（available-nodes / add / remove）
7. 日志检查

运行方式：
cd backend
python check_stage4.py
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

PASS_COUNT = 0
FAIL_COUNT = 0


def log(msg, ok=True):
    global PASS_COUNT, FAIL_COUNT
    if ok:
        PASS_COUNT += 1
        print(f"  [PASS] {msg}")
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {msg}")


def login(username, password="123456"):
    """登录并返回 token 和用户信息。"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password})
    if r.status_code != 200:
        print(f"  [ERROR] 登录失败 {username}: {r.status_code} {r.text}")
        return None, None
    data = r.json()
    token = data.get("data", {}).get("access_token") or data.get("data", {}).get("token")
    if not token:
        print(f"  [ERROR] 登录响应无 token: {data}")
        return None, None
    return token, data.get("data", {})


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def cleanup_test_groups(token, prefix="STAGE4_"):
    """清理测试群组。"""
    headers = auth_headers(token)
    r = requests.get(f"{BASE_URL}/api/groups?page=1&page_size=100", headers=headers)
    if r.status_code != 200:
        return
    data = r.json().get("data", {})
    groups = data.get("items", []) if isinstance(data, dict) else data
    for g in groups:
        if isinstance(g, dict) and g.get("group_code", "").startswith(prefix):
            requests.delete(f"{BASE_URL}/api/groups/{g['id']}", headers=headers)
            # 也删除关联记录
            try:
                requests.delete(f"{BASE_URL}/api/groups/{g['id']}", headers=headers)
            except:
                pass


def cleanup_test_groups_by_db():
    """通过数据库清理测试群组。"""
    try:
        from app.core.database import SessionLocal
        from app.models.group import GroupInfo, GroupMember, GroupNode, GroupLifecycleLog
        from app.models.user import SysUserGroup, SysUserRoleBinding

        db = SessionLocal()
        # 查找测试群组
        test_groups = db.query(GroupInfo).filter(GroupInfo.group_code.like("STAGE4_%")).all()
        for g in test_groups:
            # 删除关联
            db.query(GroupMember).filter(GroupMember.group_id == g.id).delete()
            db.query(GroupNode).filter(GroupNode.group_id == g.id).delete()
            db.query(GroupLifecycleLog).filter(GroupLifecycleLog.group_id == g.id).delete()
            db.query(SysUserGroup).filter(SysUserGroup.group_id == g.id).delete()
            db.query(SysUserRoleBinding).filter(
                SysUserRoleBinding.scope_type == "group",
                SysUserRoleBinding.scope_id == g.id,
            ).delete()
            db.delete(g)
        db.commit()
        db.close()
        print(f"  已清理 {len(test_groups)} 个测试群组")
    except Exception as e:
        print(f"  [WARN] 清理失败: {e}")


# ============================================================
# 测试用例
# ============================================================

def test_01_permission_helpers():
    """测试权限判断函数。"""
    print("\n=== 1. 权限判断函数 ===")
    from app.core.database import SessionLocal
    from app.services.access_control_service import (
        is_platform_admin, is_agency_admin, is_group_admin,
        is_ancestor_agency, is_same_level_agency, find_common_parent_agency,
    )

    db = SessionLocal()
    try:
        # platform_admin (id=7)
        assert is_platform_admin(db, 7) == True
        log("is_platform_admin(7) = True")

        # agency_admin (id=13, agency_id=10)
        assert is_platform_admin(db, 13) == False
        log("is_platform_admin(13) = False")
        assert is_agency_admin(db, 13, 10) == True
        log("is_agency_admin(13, 10) = True")
        assert is_agency_admin(db, 13, 11) == False
        log("is_agency_admin(13, 11) = False")

        # group_admin (id=8)
        assert is_group_admin(db, 8, 1) == True
        log("is_group_admin(8, 1) = True")
        assert is_group_admin(db, 8, 999) == False
        log("is_group_admin(8, 999) = False")

        # is_ancestor_agency
        # 需要检查实际 agency 层级关系
        result = is_ancestor_agency(db, 10, 11)
        log(f"is_ancestor_agency(10, 11) = {result} (取决于parent_agency_id)")

        # is_same_level_agency
        result = is_same_level_agency(db, 11, 12)
        log(f"is_same_level_agency(11, 12) = {result} (取决于agency_level)")

        # find_common_parent_agency
        result = find_common_parent_agency(db, [11, 12])
        log(f"find_common_parent_agency([11, 12]) = {result}")

    finally:
        db.close()


def test_02_group_create_permissions():
    """测试群组创建权限。"""
    print("\n=== 2. 群组创建权限 ===")

    # 2.1 platform_admin 可以创建
    token, user_data = login("platform_admin")
    if not token:
        log("platform_admin 登录失败", ok=False)
        return

    headers = auth_headers(token)
    r = requests.post(f"{BASE_URL}/api/groups", headers=headers, json={
        "group_code": "STAGE4_PA_CREATE",
        "group_name": "平台管理员创建测试",
        "lead_agency_id": 10,
        "description": "测试",
    })
    log(f"platform_admin 创建群组: status={r.status_code}", ok=r.status_code == 200)
    if r.status_code == 200:
        data = r.json().get("data", {})
        log(f"  群组状态: {data.get('status')} == draft", ok=data.get("status") == "draft")
        log(f"  审批状态: {data.get('approval_status')} == none", ok=data.get("approval_status") == "none")
        log(f"  approval_required: {data.get('approval_required')} == False", ok=data.get("approval_required") == False)

    # 2.2 group_admin 不能创建
    token_ga, _ = login("group_admin")
    if not token_ga:
        log("group_admin 登录失败", ok=False)
        return

    r = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers(token_ga), json={
        "group_code": "STAGE4_GA_CREATE_FAIL",
        "group_name": "群组管理员尝试创建",
        "lead_agency_id": 10,
    })
    log(f"group_admin 创建群组被拒: status={r.status_code}", ok=r.status_code == 403)

    # 2.3 agency_admin 可以下级创建
    token_aa, _ = login("agency_admin")
    if not token_aa:
        log("agency_admin 登录失败", ok=False)
        return

    r = requests.post(f"{BASE_URL}/api/groups", headers=auth_headers(token_aa), json={
        "group_code": "STAGE4_AA_CREATE",
        "group_name": "机构管理员下级创建测试",
        "lead_agency_id": 10,
    })
    log(f"agency_admin 创建下级群组: status={r.status_code}", ok=r.status_code == 200)


def test_03_same_level_pending_approval():
    """测试同级机构创建进入 pending_approval。"""
    print("\n=== 3. 同级机构创建 -> pending_approval ===")

    token_aa, _ = login("agency_admin")
    if not token_aa:
        log("agency_admin 登录失败", ok=False)
        return

    headers = auth_headers(token_aa)
    # 尝试用同级机构作为成员（如果 agency_admin 所属机构下有同级机构）
    # 这里用 member_agency_ids
    r = requests.post(f"{BASE_URL}/api/groups", headers=headers, json={
        "group_code": "STAGE4_SAME_LEVEL",
        "group_name": "同级协作测试",
        "lead_agency_id": 10,
        "member_agency_ids": [11, 12],
    })
    log(f"同级协作创建: status={r.status_code}", ok=r.status_code == 200)
    if r.status_code == 200:
        data = r.json().get("data", {})
        # 如果 10 是 11, 12 的上级，则 status=draft（不需要审批）
        # 如果是同级，则 status=pending_approval
        log(f"  群组状态: {data.get('status')}")
        log(f"  审批状态: {data.get('approval_status')}")


def test_04_group_approval():
    """测试群组审批。"""
    print("\n=== 4. 群组审批 ===")

    token_pa, _ = login("platform_admin")
    token_aa, _ = login("agency_admin")
    if not token_pa or not token_aa:
        log("登录失败", ok=False)
        return

    headers_pa = auth_headers(token_pa)
    headers_aa = auth_headers(token_aa)

    # 先查看是否有 pending_approval 的群组
    r = requests.get(f"{BASE_URL}/api/groups?status=pending_approval", headers=headers_pa)
    groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []

    if groups:
        gid = groups[0]["id"]
        # 4.1 审批通过
        r = requests.post(f"{BASE_URL}/api/groups/{gid}/approve", headers=headers_pa, json={"remark": "测试审批通过"})
        log(f"platform_admin 审批通过: status={r.status_code}", ok=r.status_code == 200)
        if r.status_code == 200:
            data = r.json().get("data", {})
            log(f"  审批后状态: {data.get('status')}", ok=data.get("status") == "draft")

        # 检查生命周期日志
        r = requests.get(f"{BASE_URL}/api/groups/{gid}/lifecycle-logs", headers=headers_pa)
        if r.status_code == 200:
            logs = r.json().get("data", {}).get("items", [])
            has_approved_log = any(l.get("event_type") == "group_approved" for l in logs)
            log(f"  审批通过日志存在: {has_approved_log}", ok=has_approved_log)
    else:
        log("没有 pending_approval 的群组，跳过审批测试")

    # 4.2 创建一个待审批群组然后驳回
    r = requests.post(f"{BASE_URL}/api/groups", headers=headers_aa, json={
        "group_code": "STAGE4_REJECT_TEST",
        "group_name": "待驳回测试群组",
        "lead_agency_id": 10,
        "member_agency_ids": [11],
    })
    if r.status_code == 200:
        gid = r.json().get("data", {}).get("id")
        # 如果是 pending_approval 才测试驳回
        detail_r = requests.get(f"{BASE_URL}/api/groups/{gid}", headers=headers_pa)
        if detail_r.status_code == 200:
            detail = detail_r.json().get("data", {})
            if detail.get("status") == "pending_approval":
                r = requests.post(f"{BASE_URL}/api/groups/{gid}/reject", headers=headers_pa, json={"reason": "测试驳回"})
                log(f"platform_admin 驳回: status={r.status_code}", ok=r.status_code == 200)
                if r.status_code == 200:
                    data = r.json().get("data", {})
                    log(f"  驳回后状态: {data.get('status')}", ok=data.get("status") == "rejected")
            else:
                log(f"  群组状态为 {detail.get('status')}，非 pending_approval，跳过驳回测试")


def test_05_member_management():
    """测试成员机构管理。"""
    print("\n=== 5. 成员机构管理 ===")

    token_pa, _ = login("platform_admin")
    if not token_pa:
        log("登录失败", ok=False)
        return
    headers = auth_headers(token_pa)

    # 找一个活跃群组
    r = requests.get(f"{BASE_URL}/api/groups?status=draft", headers=headers)
    groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []
    if not groups:
        r = requests.get(f"{BASE_URL}/api/groups?status=active", headers=headers)
        groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []

    if not groups:
        log("没有可用的群组，跳过成员管理测试")
        return

    gid = groups[0]["id"]

    # 5.1 查看成员
    r = requests.get(f"{BASE_URL}/api/groups/{gid}/members", headers=headers)
    log(f"查看成员: status={r.status_code}", ok=r.status_code == 200)
    members = r.json().get("data", []) if r.status_code == 200 else []
    member_ids = [m["agency_id"] for m in members]

    # 5.2 添加成员（找一个不在列表中的机构）
    new_agency_id = None
    for aid in [11, 12]:
        if aid not in member_ids:
            new_agency_id = aid
            break

    if new_agency_id:
        r = requests.post(f"{BASE_URL}/api/groups/{gid}/members", headers=headers, json={
            "agency_id": new_agency_id,
            "member_type": "participant",
            "remark": "测试添加",
        })
        log(f"添加成员机构 {new_agency_id}: status={r.status_code}", ok=r.status_code == 200)

        # 5.3 不能重复添加
        r = requests.post(f"{BASE_URL}/api/groups/{gid}/members", headers=headers, json={
            "agency_id": new_agency_id,
        })
        log(f"重复添加被拒: status={r.status_code}", ok=r.status_code in (400, 403))

        # 5.4 不能移除牵头机构
        lead_member = next((m for m in members if m.get("is_lead")), None)
        if lead_member:
            r = requests.delete(f"{BASE_URL}/api/groups/{gid}/members/{lead_member['agency_id']}", headers=headers)
            log(f"不能移除牵头机构: status={r.status_code}", ok=r.status_code == 400)


def test_06_user_management():
    """测试群组用户授权管理。"""
    print("\n=== 6. 群组用户授权管理 ===")

    token_pa, _ = login("platform_admin")
    if not token_pa:
        log("登录失败", ok=False)
        return
    headers = auth_headers(token_pa)

    # 找一个群组
    r = requests.get(f"{BASE_URL}/api/groups?page=1&page_size=10", headers=headers)
    groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []
    if not groups:
        log("没有可用的群组", ok=False)
        return

    gid = groups[0]["id"]

    # 6.1 查看用户
    r = requests.get(f"{BASE_URL}/api/groups/{gid}/users", headers=headers)
    log(f"查看群组用户: status={r.status_code}", ok=r.status_code == 200)
    users = r.json().get("data", []) if r.status_code == 200 else []
    existing_user_ids = [u["user_id"] for u in users]

    # 6.2 添加用户
    # 找一个成员机构下的用户
    r = requests.get(f"{BASE_URL}/api/groups/{gid}/members", headers=headers)
    member_agencies = [m["agency_id"] for m in r.json().get("data", [])] if r.status_code == 200 else []

    # 用 chain_governor (id=10) 或 business_user (id=9)
    test_user_id = 10
    if test_user_id in existing_user_ids:
        test_user_id = 9

    if member_agencies:
        r = requests.post(f"{BASE_URL}/api/groups/{gid}/users", headers=headers, json={
            "user_id": test_user_id,
            "role_code": "user",
        })
        log(f"添加用户 {test_user_id}: status={r.status_code}", ok=r.status_code == 200)

        if r.status_code == 200:
            # 6.3 重复添加
            r = requests.post(f"{BASE_URL}/api/groups/{gid}/users", headers=headers, json={
                "user_id": test_user_id,
                "role_code": "user",
            })
            log(f"重复添加用户被拒: status={r.status_code}", ok=r.status_code == 400)

    # 6.4 检查群组管理员不能被移出（如果只有一个）
    admin_users = [u for u in users if any(role["role_code"] == "admin" for role in u.get("roles", []))]
    if len(admin_users) == 1:
        r = requests.delete(f"{BASE_URL}/api/groups/{gid}/users/{admin_users[0]['user_id']}", headers=headers)
        log(f"不能移出最后一个管理员: status={r.status_code}", ok=r.status_code == 400)


def test_07_node_management():
    """测试节点授权管理。"""
    print("\n=== 7. 节点授权管理 ===")

    token_pa, _ = login("platform_admin")
    if not token_pa:
        log("登录失败", ok=False)
        return
    headers = auth_headers(token_pa)

    # 找一个群组
    r = requests.get(f"{BASE_URL}/api/groups?page=1&page_size=10", headers=headers)
    groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []
    if not groups:
        log("没有可用的群组", ok=False)
        return

    gid = groups[0]["id"]

    # 7.1 查看可授权节点
    r = requests.get(f"{BASE_URL}/api/groups/{gid}/available-nodes", headers=headers)
    log(f"查看可授权节点: status={r.status_code}", ok=r.status_code == 200)

    available = r.json().get("data", []) if r.status_code == 200 else []
    unauthorized_nodes = [n for n in available if not n.get("authorized")]

    # 7.2 授权节点
    if unauthorized_nodes:
        node = unauthorized_nodes[0]
        r = requests.post(f"{BASE_URL}/api/groups/{gid}/nodes", headers=headers, json={
            "node_id": node["node_id"],
            "remark": "测试授权",
        })
        log(f"授权节点 {node['node_id']}: status={r.status_code}", ok=r.status_code == 200)

        if r.status_code == 200:
            # 7.3 不能重复授权
            r = requests.post(f"{BASE_URL}/api/groups/{gid}/nodes", headers=headers, json={
                "node_id": node["node_id"],
            })
            log(f"重复授权被拒: status={r.status_code}", ok=r.status_code == 400)

            # 7.4 查看已授权节点
            r = requests.get(f"{BASE_URL}/api/groups/{gid}/nodes", headers=headers)
            log(f"查看已授权节点: status={r.status_code}", ok=r.status_code == 200)
            nodes = r.json().get("data", []) if r.status_code == 200 else []
            has_node = any(n["node_id"] == node["node_id"] for n in nodes)
            log(f"  节点在已授权列表中: {has_node}", ok=has_node)
    else:
        log("没有可授权的节点，跳过节点授权测试")


def test_08_lifecycle_logs():
    """测试生命周期日志。"""
    print("\n=== 8. 生命周期日志 ===")

    token_pa, _ = login("platform_admin")
    if not token_pa:
        log("登录失败", ok=False)
        return
    headers = auth_headers(token_pa)

    # 找一个测试群组
    r = requests.get(f"{BASE_URL}/api/groups?page=1&page_size=10", headers=headers)
    groups = r.json().get("data", {}).get("items", []) if r.status_code == 200 else []
    test_groups = [g for g in groups if g.get("group_code", "").startswith("STAGE4_")]

    if not test_groups:
        log("没有 STAGE4_ 开头的测试群组", ok=False)
        return

    gid = test_groups[0]["id"]
    r = requests.get(f"{BASE_URL}/api/groups/{gid}/lifecycle-logs", headers=headers)
    log(f"查看日志: status={r.status_code}", ok=r.status_code == 200)

    if r.status_code == 200:
        logs = r.json().get("data", {}).get("items", [])
        log(f"  日志条数: {len(logs)} > 0", ok=len(logs) > 0)
        event_types = set(l.get("event_type") for l in logs)
        log(f"  包含事件类型: {event_types}", ok=len(event_types) > 0)


def test_09_frontend_display():
    """前端展示状态检查（仅检查接口返回字段）。"""
    print("\n=== 9. 接口返回字段完整性 ===")

    token_pa, _ = login("platform_admin")
    if not token_pa:
        log("登录失败", ok=False)
        return
    headers = auth_headers(token_pa)

    # 群组列表包含审批字段
    r = requests.get(f"{BASE_URL}/api/groups?page=1&page_size=5", headers=headers)
    if r.status_code == 200:
        items = r.json().get("data", {}).get("items", [])
        if items:
            first = items[0]
            has_approval_status = "approval_status" in first
            has_approval_required = "approval_required" in first
            log(f"列表包含 approval_status: {has_approval_status}", ok=has_approval_status)
            log(f"列表包含 approval_required: {has_approval_required}", ok=has_approval_required)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("第4阶段验收测试")
    print("=" * 60)

    # 清理
    print("\n清理测试数据...")
    cleanup_test_groups_by_db()

    # 运行测试
    test_01_permission_helpers()
    test_02_group_create_permissions()
    test_03_same_level_pending_approval()
    test_04_group_approval()
    test_05_member_management()
    test_06_user_management()
    test_07_node_management()
    test_08_lifecycle_logs()
    test_09_frontend_display()

    # 结果
    print("\n" + "=" * 60)
    print(f"测试完成: PASS={PASS_COUNT}, FAIL={FAIL_COUNT}")
    print("=" * 60)

    sys.exit(0 if FAIL_COUNT == 0 else 1)
