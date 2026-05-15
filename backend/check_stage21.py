import subprocess
import sys
import urllib.request
from datetime import datetime

from sqlalchemy import inspect, text


# =========================
# 一、基础配置
# =========================

REQUIRED_TABLES = [
    "agency",
    "group_info",
    "group_member",
    "node",
    "group_node",
    "group_lifecycle_log",
    "sys_user",
    "sys_role",
    "sys_user_group",
    "sys_user_role_binding",
    "sys_user_operate_log",
    "contract_info",
]

REQUIRED_COLUMNS = {
    "task": [
        "group_id",
        "creator_user_id",
        "creator_agency_id",
        "lead_agency_id",
        "execution_mode",
        "selected_node_json",
    ],
    "task_result": [
        "group_id",
        "agency_id",
        "task_type",
        "result_version",
        "anchor_status",
        "anchor_time",
        "chain_record_id",
    ],
    "chain_record": [
        "anchor_id",
        "group_id",
        "agency_id",
        "task_id",
        "result_id",
        "dataset_id",
        "contract_name",
        "contract_version",
        "verify_status",
        "last_verify_time",
        "verify_detail_json",
        "updated_at",
    ],
}

DEFAULT_DATA_CHECKS = [
    ("agency", "agency_code", ["CDC_BEIJING", "HOSPITAL_ALICE", "HOSPITAL_BOB"]),
    ("group_info", "group_code", ["GROUP_FLU_BEIJING_2026"]),
    ("node", "node_code", [
        "NODE_ALICE_DATA",
        "NODE_ALICE_COMPUTE",
        "NODE_ALICE_BLOCKCHAIN",
        "NODE_BOB_DATA",
        "NODE_BOB_COMPUTE",
    ]),
    ("sys_role", "role_code", ["admin", "user", "governor"]),
    ("sys_user", "username", [
        "platform_admin",
        "group_admin",
        "business_user",
        "chain_governor",
    ]),
    ("contract_info", "contract_name", ["BioSafetyAnchorContract"]),
]

HTTP_CHECKS = [
    ("FastAPI Docs", "http://127.0.0.1:8000/docs"),
    ("任务列表接口", "http://127.0.0.1:8000/api/tasks"),
    ("FISCO 上链服务 18080", "http://123.60.109.244:18080/health"),
    ("SecretFlow 联合统计服务 18180", "http://123.60.109.244:18180/health"),
    ("SecretFlow 联邦学习服务 18181", "http://123.60.109.244:18181/health"),
]


# =========================
# 二、工具方法
# =========================

passed = 0
failed = 0
warned = 0


def ok(msg):
    global passed
    passed += 1
    print(f"[OK] {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"[FAIL] {msg}")


def warn(msg):
    global warned
    warned += 1
    print(f"[WARN] {msg}")


def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="ignore",
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def load_engine():
    try:
        from app.core.database import engine
        return engine
    except Exception as e:
        fail(f"无法从 app.core.database 导入 engine：{e}")
        print("请确认当前终端目录是 backend，并且已激活 bio_backend 环境。")
        sys.exit(1)


def check_http(name, url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                ok(f"{name} 可访问：{url}")
            else:
                warn(f"{name} 返回状态码 {resp.status}：{url}")
    except Exception as e:
        warn(f"{name} 暂不可访问：{url}，原因：{e}")


def table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def get_columns(inspector, table_name):
    return [col["name"] for col in inspector.get_columns(table_name)]


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


# =========================
# 三、开始检测
# =========================

print("=" * 80)
print("生物安全数据联合统计系统 - 第 21 阶段数据库底座一键检测")
print(f"检测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)


# 1. Alembic 状态
print("\n[1] 检查 Alembic 当前版本")
code, out, err = run_cmd("alembic current")
if code == 0:
    ok(f"Alembic current 正常：{out}")
else:
    fail(f"Alembic current 执行失败：{err}")


# 2. 数据库连接
print("\n[2] 检查数据库连接")
engine = load_engine()

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    ok("数据库连接正常")
except Exception as e:
    fail(f"数据库连接失败：{e}")
    sys.exit(1)


# 3. 新增表检查
print("\n[3] 检查新增表是否存在")
inspector = inspect(engine)

for table in REQUIRED_TABLES:
    if table_exists(inspector, table):
        ok(f"表存在：{table}")
    else:
        fail(f"表不存在：{table}")


# 4. 旧表扩展字段检查
print("\n[4] 检查 task / task_result / chain_record 扩展字段")

for table, required_cols in REQUIRED_COLUMNS.items():
    if not table_exists(inspector, table):
        fail(f"旧表不存在，无法检查字段：{table}")
        continue

    existing_cols = get_columns(inspector, table)

    for col in required_cols:
        if col in existing_cols:
            ok(f"{table}.{col} 存在")
        else:
            fail(f"{table}.{col} 缺失")


# 5. 默认演示数据检查
print("\n[5] 检查默认演示数据")

with engine.connect() as conn:
    for table, field, values in DEFAULT_DATA_CHECKS:
        if not table_exists(inspector, table):
            fail(f"表不存在，无法检查默认数据：{table}")
            continue

        for value in values:
            try:
                count = scalar(
                    conn,
                    f"SELECT COUNT(*) FROM {table} WHERE {field} = :value",
                    {"value": value},
                )
                if count and count > 0:
                    ok(f"{table}.{field} 默认数据存在：{value}")
                else:
                    fail(f"{table}.{field} 默认数据缺失：{value}")
            except Exception as e:
                fail(f"检查默认数据失败：{table}.{field}={value}，原因：{e}")


# 6. 历史数据数量检查
print("\n[6] 检查历史数据是否仍存在")

HISTORY_TABLES = ["task", "task_result", "chain_record"]

with engine.connect() as conn:
    for table in HISTORY_TABLES:
        if not table_exists(inspector, table):
            fail(f"历史表不存在：{table}")
            continue

        try:
            count = scalar(conn, f"SELECT COUNT(*) FROM {table}")
            ok(f"{table} 当前记录数：{count}")
        except Exception as e:
            fail(f"读取 {table} 记录数失败：{e}")


# 7. HTTP 服务检查
print("\n[7] 检查后端与远端服务健康状态")

for name, url in HTTP_CHECKS:
    check_http(name, url)


# 8. 汇总结果
print("\n" + "=" * 80)
print("检测结果汇总")
print("=" * 80)
print(f"通过：{passed}")
print(f"警告：{warned}")
print(f"失败：{failed}")

if failed == 0:
    print("\n结论：第 21 阶段数据库底座检测通过。")
    sys.exit(0)
else:
    print("\n结论：检测未通过，请优先处理 [FAIL] 项。")
    sys.exit(1)