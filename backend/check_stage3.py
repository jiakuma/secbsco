"""
第 3 阶段检测脚本：群组基础管理与生命周期起步

检测内容：
1. 登录各角色用户
2. 群组列表接口
3. 群组详情接口
4. 群组成员机构
5. 群组用户列表
6. 群组节点列表
7. 创建测试群组（事务验证）
8. 数据库记录验证
9. 权限控制验证
10. 生命周期日志
11. 编辑群组
12. 不破坏已有接口
"""

import urllib.request
import urllib.error
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

# ============================================================
# 辅助函数
# ============================================================

def http_post(path, data, token=None):
    """POST 请求"""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw)
        except Exception:
            result = {"detail": raw}
        result["status_code"] = exc.code
        return result, exc.code


def http_get(path, token=None, params=None):
    """GET 请求"""
    url = f"{BASE_URL}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        if qs:
            url = f"{url}?{qs}"
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw)
        except Exception:
            result = {"detail": raw}
        result["status_code"] = exc.code
        return result, exc.code


def http_put(path, data, token=None):
    """PUT 请求"""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="PUT")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(raw)
        except Exception:
            result = {"detail": raw}
        result["status_code"] = exc.code
        return result, exc.code


def login(username, password):
    """登录并返回 token"""
    res, code = http_post("/api/auth/login", {"username": username, "password": password})
    assert res.get("code") == 0, f"登录失败: {res}"
    token = res["data"]["access_token"]
    return token


def check(condition, desc):
    """检查并通过"""
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {desc}")
    else:
        failed += 1
        print(f"  [FAIL] {desc}")


# ============================================================
# 主流程
# ============================================================

passed = 0
failed = 0

print("=" * 70)
print("第 3 阶段检测：群组基础管理与生命周期起步")
print("=" * 70)

# ---------- 1. 登录 ----------
print("\n--- 1. 登录各角色用户 ---")
tokens = {}
for role, user, pwd in [
    ("platform_admin", "platform_admin", "123456"),
    ("group_admin", "group_admin", "123456"),
    ("business_user", "business_user", "123456"),
    ("chain_governor", "chain_governor", "123456"),
]:
    try:
        tokens[role] = login(user, pwd)
        check(True, f"登录 {user} 成功")
    except Exception as e:
        check(False, f"登录 {user} 失败: {e}")

# ---------- 2. 群组列表 ----------
print("\n--- 2. 群组列表接口 ---")
res, code = http_get("/api/groups", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "group_admin 查询群组列表成功")
items = res.get("data", {}).get("items", [])
check(len(items) >= 1, f"返回群组数量 >= 1 (实际: {len(items)})")
if items:
    default_group_id = items[0]["id"]
    check(items[0].get("group_code") == "GROUP_FLU_BEIJING_2026", f"默认群组编码正确: {items[0].get('group_code')}")

# ---------- 3. 群组详情 ----------
print("\n--- 3. 群组详情接口 ---")
res, code = http_get(f"/api/groups/{default_group_id}", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询默认群组详情成功")
detail = res.get("data", {})
check(detail.get("summary") is not None, "详情包含 summary 统计")
summary = detail.get("summary", {})
check(summary.get("member_count", 0) >= 1, f"成员机构数 >= 1 (实际: {summary.get('member_count')})")

# ---------- 4. 群组成员机构 ----------
print("\n--- 4. 群组成员机构 ---")
res, code = http_get(f"/api/groups/{default_group_id}/members", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询成员机构成功")
members = res.get("data", [])
check(len(members) >= 1, f"成员机构数 >= 1 (实际: {len(members)})")

# ---------- 5. 群组用户列表 ----------
print("\n--- 5. 群组用户列表 ---")
res, code = http_get(f"/api/groups/{default_group_id}/users", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询群组用户成功")
users = res.get("data", [])
check(len(users) >= 1, f"群组用户数 >= 1 (实际: {len(users)})")

# ---------- 6. 群组节点列表 ----------
print("\n--- 6. 群组节点列表 ---")
res, code = http_get(f"/api/groups/{default_group_id}/nodes", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询群组节点成功")
nodes = res.get("data", [])
check(len(nodes) >= 1, f"授权节点数 >= 1 (实际: {len(nodes)})")

# ---------- 7. 创建测试群组 ----------
print("\n--- 7. 创建测试群组 ---")
ts = int(time.time())
test_code = f"GROUP_TEST_STAGE3_{ts}"
create_data = {
    "group_code": test_code,
    "group_name": f"测试群组_{ts}",
    "group_level": "city",
    "region_code": "110000",
    "region_name": "北京市",
    "lead_agency_id": 10,  # 北京市疾控中心
    "description": "第3阶段自动化测试群组",
}
res, code = http_post("/api/groups", create_data, tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, f"创建测试群组成功: {test_code}")
create_result = res.get("data", {})
new_group_id = create_result.get("id")
check(new_group_id is not None, f"新建群组 ID: {new_group_id}")
check(create_result.get("created_admin_role_created") is True, "创建人自动成为群组管理员")
check(create_result.get("lead_agency_member_created") is True, "牵头机构自动写入成员")
check(create_result.get("lifecycle_log_created") is True, "生命周期日志自动创建")

# ---------- 8. 验证新群组数据 ----------
print("\n--- 8. 验证创建事务数据 ---")

# 8a. 群组详情
res, code = http_get(f"/api/groups/{new_group_id}", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询新建群组详情成功")
check(res["data"]["status"] == "draft", "新群组状态为 draft")

# 8b. 成员机构
res, code = http_get(f"/api/groups/{new_group_id}/members", tokens.get("group_admin"))
members = res.get("data", [])
has_lead = any(m.get("is_lead") is True for m in members)
check(has_lead, "牵头机构已自动写入 group_member")

# 8c. 用户
res, code = http_get(f"/api/groups/{new_group_id}/users", tokens.get("group_admin"))
users = res.get("data", [])
has_admin_user = any(
    u.get("username") == "group_admin" and
    any(r.get("role_code") == "admin" for r in u.get("roles", []))
    for u in users
)
check(has_admin_user, "创建人已进入 sys_user_group 且拥有 admin + group 权限")

# 8d. 生命周期日志
res, code = http_get(f"/api/groups/{new_group_id}/lifecycle-logs", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "查询生命周期日志成功")
logs = res.get("data", {}).get("items", [])
has_created_log = any(l.get("event_type") == "group_created" for l in logs)
check(has_created_log, "group_created 日志已写入")

# ---------- 9. 权限控制 ----------
print("\n--- 9. 权限控制 ---")

# business_user 不能创建群组
res, code = http_post("/api/groups", create_data, tokens.get("business_user"))
is_denied = code == 403 or "需要管理员权限" in str(res)
check(is_denied, f"business_user 创建群组被拒绝 (HTTP {code})")

# chain_governor 不能创建群组
res, code = http_post("/api/groups", create_data, tokens.get("chain_governor"))
is_denied = code == 403 or "需要管理员权限" in str(res)
check(is_denied, f"chain_governor 创建群组被拒绝 (HTTP {code})")

# ---------- 10. 编辑群组 ----------
print("\n--- 10. 编辑群组 ---")
update_data = {
    "group_name": f"测试群组_已编辑_{ts}",
    "description": "编辑后的描述",
}
res, code = http_put(f"/api/groups/{new_group_id}", update_data, tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "编辑群组基础信息成功")

# 验证编辑后
res, code = http_get(f"/api/groups/{new_group_id}", tokens.get("group_admin"))
check(res["data"]["group_name"] == f"测试群组_已编辑_{ts}", "群组名称已更新")
check(res["data"]["description"] == "编辑后的描述", "群组描述已更新")

# 验证 group_updated 日志
res, code = http_get(f"/api/groups/{new_group_id}/lifecycle-logs", tokens.get("group_admin"))
logs = res.get("data", {}).get("items", [])
has_updated_log = any(l.get("event_type") == "group_updated" for l in logs)
check(has_updated_log, "group_updated 日志已写入")

# ---------- 11. 不破坏已有接口 ----------
print("\n--- 11. 不破坏已有接口 ---")

# /api/auth/me
res, code = http_get("/api/auth/me", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "/api/auth/me 正常")

# /api/auth/menus
res, code = http_get("/api/auth/menus", tokens.get("group_admin"))
check(code == 200 and res.get("code") == 0, "/api/auth/menus 正常")

# /api/tasks
res, code = http_get("/api/tasks", tokens.get("group_admin"), {"page": 1, "page_size": 5})
check(code == 200 and res.get("code") == 0, "/api/tasks 正常")

# ---------- 12. 平台管理员查看全部群组 ----------
print("\n--- 12. 平台管理员查看全部 ---")
res, code = http_get("/api/groups", tokens.get("platform_admin"))
check(code == 200 and res.get("code") == 0, "platform_admin 查询群组列表成功")
platform_items = res.get("data", {}).get("items", [])
platform_total = res.get("data", {}).get("total", 0)
check(platform_total >= len(items), f"平台管理员可见群组数 >= 群组管理员 (平台: {platform_total}, 群组: {len(items)})")

# ============================================================
# 结果汇总
# ============================================================

print("\n" + "=" * 70)
print(f"检测结果: {passed} PASS, {failed} FAIL, 共 {passed + failed} 项")
if failed == 0:
    print("第 3 阶段群组基础管理与生命周期起步检测通过!")
else:
    print(f"第 3 阶段检测未通过，有 {failed} 项失败")
print("=" * 70)

sys.exit(0 if failed == 0 else 1)
