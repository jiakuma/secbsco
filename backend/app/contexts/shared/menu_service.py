"""
菜单服务：根据用户角色+作用域返回菜单列表。

菜单生成规则：
- user + group: 首页总览、联合统计任务、统计模板、结果展示、审计查询
- admin + group: 首页总览、联合统计任务、统计模板、结果展示、机构与节点、群组管理、用户管理
- admin + agency: 首页总览、联合统计任务、结果展示、机构管理、节点管理、用户管理
- admin + platform: 首页总览、联合统计任务、结果展示、机构管理、群组管理、节点管理、用户管理、角色授权
- governor + group: 首页总览、结果展示、区块链治理、存证记录、链上校验、合约管理
"""

from typing import Any


# ============================================================
# 菜单定义
# ============================================================

ALL_MENUS: dict[str, dict[str, Any]] = {
    "dashboard": {
        "title": "首页总览",
        "path": "/dashboard",
        "icon": "dashboard",
        "sort": 1,
    },
    "tasks": {
        "title": "联合统计任务",
        "path": "/tasks",
        "icon": "task",
        "sort": 2,
    },
    "stat_template": {
        "title": "统计模板",
        "path": "/stat-template",
        "icon": "document",
        "sort": 3,
    },
    "results": {
        "title": "结果展示",
        "path": "/results",
        "icon": "chart",
        "sort": 4,
    },
    "audit_query": {
        "title": "审计查询",
        "path": "/audit-query",
        "icon": "search",
        "sort": 5,
    },
    "agency_node": {
        "title": "机构与节点",
        "path": "/nodes",
        "icon": "office-building",
        "sort": 6,
    },
    "group_manage": {
        "title": "群组管理",
        "path": "/groups",
        "icon": "connection",
        "sort": 7,
    },
    "user_manage": {
        "title": "用户管理",
        "path": "/user-manage",
        "icon": "user",
        "sort": 8,
    },
    "role_auth": {
        "title": "角色授权",
        "path": "/role-auth",
        "icon": "key",
        "sort": 9,
    },
    "blockchain": {
        "title": "区块链治理",
        "path": "/blockchain",
        "icon": "link",
        "sort": 10,
    },
    "chain_records": {
        "title": "存证记录",
        "path": "/blockchain",
        "icon": "ticket",
        "sort": 11,
    },
    "chain_verify": {
        "title": "链上校验",
        "path": "/chain-verify",
        "icon": "circle-check",
        "sort": 12,
    },
    "contract_manage": {
        "title": "合约管理",
        "path": "/contract-manage",
        "icon": "document-copy",
        "sort": 13,
    },
}

# 角色+作用域 → 菜单 key 列表
ROLE_MENUS: dict[tuple[str, str], list[str]] = {
    ("user", "group"): [
        "dashboard", "tasks", "stat_template", "results", "audit_query",
    ],
    ("admin", "group"): [
        "dashboard", "tasks", "stat_template", "results",
        "agency_node", "group_manage", "user_manage",
    ],
    ("admin", "agency"): [
        "dashboard", "tasks", "results",
        "agency_node", "user_manage",
    ],
    ("admin", "platform"): [
        "dashboard", "tasks", "results",
        "agency_node", "group_manage", "user_manage", "role_auth",
    ],
    ("governor", "group"): [
        "dashboard", "results",
        "blockchain", "chain_records", "chain_verify", "contract_manage",
    ],
}

# 菜单排序（去重后按 sort 排序）
ROLE_MENUS_PRIORITY: dict[tuple[str, str], int] = {
    ("admin", "platform"): 0,
    ("admin", "agency"): 1,
    ("admin", "group"): 2,
    ("user", "group"): 3,
    ("governor", "group"): 4,
}


def get_menus_for_roles(role_bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    根据角色绑定列表返回菜单。

    如果用户有多个角色，取权限范围最大的角色的菜单。
    admin > user > governor（优先展示管理菜单）
    """
    if not role_bindings:
        return []

    # 确定最高优先级的角色
    best_key = None
    best_priority = 999

    for rb in role_bindings:
        key = (rb["role_code"], rb["scope_type"])
        priority = ROLE_MENUS_PRIORITY.get(key, 99)
        if priority < best_priority:
            best_priority = priority
            best_key = key

    if not best_key:
        return []

    menu_keys = ROLE_MENUS.get(best_key, [])

    # 合并所有角色的菜单（取并集，admin 的菜单通常已包含 user 的）
    all_keys = set()
    for rb in role_bindings:
        key = (rb["role_code"], rb["scope_type"])
        keys = ROLE_MENUS.get(key, [])
        all_keys.update(keys)

    # 按照最佳角色的排序，再合并其他角色独有的菜单
    result = []
    added = set()

    # 先按最佳角色的顺序添加
    for mk in menu_keys:
        if mk in all_keys and mk not in added:
            menu_data = ALL_MENUS.get(mk)
            if menu_data:
                result.append({
                    "title": menu_data["title"],
                    "path": menu_data["path"],
                    "icon": menu_data["icon"],
                })
                added.add(mk)

    # 添加其他角色独有的菜单（按 sort 排序）
    remaining = all_keys - added
    for mk in sorted(remaining, key=lambda k: ALL_MENUS.get(k, {}).get("sort", 99)):
        menu_data = ALL_MENUS.get(mk)
        if menu_data:
            result.append({
                "title": menu_data["title"],
                "path": menu_data["path"],
                "icon": menu_data["icon"],
            })
            added.add(mk)

    return result
