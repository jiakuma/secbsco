"""
第 2 阶段检测脚本：用户系统与三类角色作用域控制。

检测内容：
1. 4 个默认用户登录
2. /api/auth/me 返回 roles/groups/permissions
3. /api/auth/menus 按角色返回不同菜单
4. 携带 token 访问 /api/tasks 正常
5. business_user 不显示系统管理菜单
6. chain_governor 能看到区块链治理菜单
7. chain_governor 不能执行任务
8. 普通 user 访问用户管理返回 403
9. admin 可以访问用户管理
"""

import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://127.0.0.1:8000"

results = {"pass": 0, "warn": 0, "fail": 0, "details": []}


def http_post(path: str, data: dict = None, token: str = None) -> dict:
    """发送 POST 请求。"""
    url = f"{BASE_URL}{path}"
    body = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(body)
            data["status_code"] = exc.code
            return data
        except Exception:
            return {"code": exc.code, "message": body, "status_code": exc.code}
    except Exception as exc:
        return {"code": -1, "message": str(exc), "status_code": -1}


def http_get(path: str, token: str = None) -> dict:
    """发送 GET 请求。"""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            data = json.loads(body)
            data["status_code"] = exc.code
            return data
        except Exception:
            return {"code": exc.code, "message": body, "status_code": exc.code}
    except Exception as exc:
        return {"code": -1, "message": str(exc), "status_code": -1}


def check(name: str, condition: bool, detail: str = ""):
    """记录检测结果。"""
    if condition:
        results["pass"] += 1
        results["details"].append({"name": name, "status": "PASS", "detail": detail})
        print(f"  ✓ {name}")
    else:
        results["fail"] += 1
        results["details"].append({"name": name, "status": "FAIL", "detail": detail})
        print(f"  ✗ {name} — {detail}")


def warn(name: str, detail: str = ""):
    """记录警告。"""
    results["warn"] += 1
    results["details"].append({"name": name, "status": "WARN", "detail": detail})
    print(f"  ⚠ {name} — {detail}")


def get_token(username: str, password: str = "123456") -> str | None:
    """登录获取 token。"""
    res = http_post("/api/auth/login", {"username": username, "password": password})
    if res.get("code") == 0 and res.get("data", {}).get("access_token"):
        return res["data"]["access_token"]
    return None


def main():
    print("=" * 60)
    print("第 2 阶段：用户系统与三类角色作用域控制检测")
    print("=" * 60)
    print()

    # ======================================================
    # 1. 登录测试
    # ======================================================
    print("【1. 登录测试】")

    token_admin = get_token("platform_admin")
    check("platform_admin 登录", token_admin is not None,
          "登录失败" if not token_admin else "")

    token_group_admin = get_token("group_admin")
    check("group_admin 登录", token_group_admin is not None,
          "登录失败" if not token_group_admin else "")

    token_biz = get_token("business_user")
    check("business_user 登录", token_biz is not None,
          "登录失败" if not token_biz else "")

    token_gov = get_token("chain_governor")
    check("chain_governor 登录", token_gov is not None,
          "登录失败" if not token_gov else "")

    print()

    # ======================================================
    # 2. /api/auth/me 测试
    # ======================================================
    print("【2. /api/auth/me 测试】")

    me_admin = http_get("/api/auth/me", token_admin)
    check("/me 返回 roles (platform_admin)",
          isinstance(me_admin.get("data", {}).get("roles"), list)
          and len(me_admin["data"]["roles"]) > 0,
          f"roles 为空或不存在: {me_admin}")

    me_admin_data = me_admin.get("data", {})
    check("/me 返回 groups (platform_admin)",
          isinstance(me_admin_data.get("groups"), list),
          f"groups 不存在或不是列表")

    check("/me 返回 permissions (platform_admin)",
          isinstance(me_admin_data.get("permissions"), list)
          and len(me_admin_data["permissions"]) > 0,
          f"permissions 为空")

    me_biz = http_get("/api/auth/me", token_biz)
    me_biz_data = me_biz.get("data", {})
    check("/me business_user 有 roles",
          isinstance(me_biz_data.get("roles"), list) and len(me_biz_data["roles"]) > 0,
          f"business_user roles 为空")

    check("/me business_user 有 groups",
          isinstance(me_biz_data.get("groups"), list) and len(me_biz_data["groups"]) > 0,
          f"business_user groups 为空")

    me_gov = http_get("/api/auth/me", token_gov)
    me_gov_data = me_gov.get("data", {})
    gov_roles = me_gov_data.get("roles", [])
    check("/me chain_governor 有 governor 角色",
          any(r.get("role_code") == "governor" for r in gov_roles),
          f"chain_governor roles: {gov_roles}")

    print()

    # ======================================================
    # 3. /api/auth/menus 测试
    # ======================================================
    print("【3. /api/auth/menus 测试】")

    menus_admin = http_get("/api/auth/menus", token_admin)
    admin_menu_items = menus_admin.get("data", [])
    check("/menus platform_admin 返回菜单",
          isinstance(admin_menu_items, list) and len(admin_menu_items) > 0,
          f"菜单为空")

    menus_biz = http_get("/api/auth/menus", token_biz)
    biz_menu_items = menus_biz.get("data", [])
    biz_menu_paths = [m.get("path") for m in biz_menu_items]
    check("business_user 不显示用户管理菜单",
          "/user-manage" not in biz_menu_paths,
          f"business_user 菜单: {biz_menu_paths}")

    check("business_user 不显示区块链治理菜单",
          "/blockchain" not in biz_menu_paths,
          f"business_user 菜单: {biz_menu_paths}")

    menus_gov = http_get("/api/auth/menus", token_gov)
    gov_menu_items = menus_gov.get("data", [])
    gov_menu_paths = [m.get("path") for m in gov_menu_items]
    check("chain_governor 显示区块链治理菜单",
          "/blockchain" in gov_menu_paths,
          f"governor 菜单: {gov_menu_paths}")

    menus_group_admin = http_get("/api/auth/menus", token_group_admin)
    group_admin_menu_items = menus_group_admin.get("data", [])
    group_admin_menu_paths = [m.get("path") for m in group_admin_menu_items]
    check("group_admin 显示用户管理菜单",
          "/user-manage" in group_admin_menu_paths,
          f"group_admin 菜单: {group_admin_menu_paths}")

    print()

    # ======================================================
    # 4. 任务接口测试
    # ======================================================
    print("【4. 任务接口权限测试】")

    # 携带 token 访问 /api/tasks
    tasks_res = http_get("/api/tasks", token_biz)
    check("携带 token 访问 /api/tasks 正常",
          tasks_res.get("code") == 0,
          f"返回: {tasks_res.get('message', '')}")

    # 未登录访问返回 401
    tasks_no_auth = http_get("/api/tasks")
    check("未登录访问 /api/tasks 返回 401",
          tasks_no_auth.get("status_code") == 401 or tasks_no_auth.get("code") == 401,
          f"返回: {tasks_no_auth}")

    # governor 不能执行任务
    # 先获取任务列表看有没有任务
    if tasks_res.get("data", {}).get("items"):
        task_id = tasks_res["data"]["items"][0]["id"]
        run_res = http_post(f"/api/tasks/{task_id}/run", token=token_gov)
        check("chain_governor 不能执行任务",
              run_res.get("status_code") == 403 or "治理员不允许" in str(run_res),
              f"返回: {run_res.get('message', run_res.get('detail', ''))}")
    else:
        warn("chain_governor 不能执行任务", "没有可用的任务来测试，跳过")

    print()

    # ======================================================
    # 5. 用户管理接口权限测试
    # ======================================================
    print("【5. 用户管理接口权限测试】")

    # business_user 访问用户管理应返回 403
    users_biz = http_get("/api/users", token_biz)
    check("business_user 访问用户管理返回 403",
          users_biz.get("status_code") == 403 or users_biz.get("code") == 403,
          f"返回: {users_biz.get('message', '')}")

    # chain_governor 访问用户管理应返回 403
    users_gov = http_get("/api/users", token_gov)
    check("chain_governor 访问用户管理返回 403",
          users_gov.get("status_code") == 403 or users_gov.get("code") == 403,
          f"返回: {users_gov.get('message', '')}")

    # admin 可以访问用户管理
    users_admin = http_get("/api/users", token_admin)
    check("platform_admin 访问用户管理正常",
          users_admin.get("code") == 0,
          f"返回: {users_admin.get('message', '')}")

    users_group_admin = http_get("/api/users", token_group_admin)
    check("group_admin 访问用户管理正常",
          users_group_admin.get("code") == 0,
          f"返回: {users_group_admin.get('message', '')}")

    print()

    # ======================================================
    # 6. 操作日志测试
    # ======================================================
    print("【6. 操作日志测试】")

    # 重新登录检查 last_login_time
    token_admin2 = get_token("platform_admin")
    if token_admin2:
        me_admin2 = http_get("/api/auth/me", token_admin2)
        me_data = me_admin2.get("data", {})
        check("登录后 /api/me 能获取用户信息",
              me_data.get("username") == "platform_admin",
              f"返回: {me_data}")
    else:
        warn("登录后检查", "重新登录失败")

    print()

    # ======================================================
    # 结果汇总
    # ======================================================
    print("=" * 60)
    print(f"检测完成：通过 {results['pass']}、警告 {results['warn']}、失败 {results['fail']}")
    print("=" * 60)

    if results["fail"] == 0:
        print()
        print("✅ 第 2 阶段：用户系统与三类角色作用域控制检测通过。")
        return 0
    else:
        print()
        print("❌ 存在失败项，请检查上述详情。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
