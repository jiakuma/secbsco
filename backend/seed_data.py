from datetime import datetime

from app.core.database import SessionLocal
from app.core.security import get_password_hash

from app.models.agency import Agency
from app.models.sys_user import SysUser
from app.models.node import Node
from app.models.dataset import Dataset
from app.models.stat_template import StatTemplate


def get_or_create(db, model, defaults=None, **kwargs):
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance

    params = dict(kwargs)
    if defaults:
        params.update(defaults)

    instance = model(**params)
    db.add(instance)
    db.flush()
    return instance


def seed_agencies(db):
    cdc = get_or_create(
        db,
        Agency,
        agency_code="CDC001",
        defaults={
            "agency_name": "市疾控中心",
            "agency_type": "cdc",
            "contact_person": "疾控管理员",
            "contact_phone": "13800000001",
            "status": "enabled",
            "description": "联合统计任务发起机构"
        }
    )

    hospital_a = get_or_create(
        db,
        Agency,
        agency_code="HOSPITAL_A",
        defaults={
            "agency_name": "医院A",
            "agency_type": "hospital",
            "contact_person": "医院A管理员",
            "contact_phone": "13800000002",
            "status": "enabled",
            "description": "病例数据提供机构"
        }
    )

    hospital_b = get_or_create(
        db,
        Agency,
        agency_code="HOSPITAL_B",
        defaults={
            "agency_name": "医院B",
            "agency_type": "hospital",
            "contact_person": "医院B管理员",
            "contact_phone": "13800000003",
            "status": "enabled",
            "description": "病例数据提供机构"
        }
    )

    lab_c = get_or_create(
        db,
        Agency,
        agency_code="LAB_C",
        defaults={
            "agency_name": "实验室C",
            "agency_type": "laboratory",
            "contact_person": "实验室管理员",
            "contact_phone": "13800000004",
            "status": "enabled",
            "description": "检测结果数据提供机构"
        }
    )

    return cdc, hospital_a, hospital_b, lab_c


def seed_users(db, cdc, hospital_a, hospital_b, lab_c):
    get_or_create(
        db,
        SysUser,
        username="admin",
        defaults={
            "agency_id": cdc.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "平台管理员",
            "role_code": "platform_admin",
            "status": "enabled"
        }
    )

    get_or_create(
        db,
        SysUser,
        username="cdc_admin",
        defaults={
            "agency_id": cdc.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "疾控中心管理员",
            "role_code": "agency_admin",
            "status": "enabled"
        }
    )

    get_or_create(
        db,
        SysUser,
        username="hospital_a",
        defaults={
            "agency_id": hospital_a.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "医院A操作员",
            "role_code": "agency_operator",
            "status": "enabled"
        }
    )

    get_or_create(
        db,
        SysUser,
        username="hospital_b",
        defaults={
            "agency_id": hospital_b.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "医院B操作员",
            "role_code": "agency_operator",
            "status": "enabled"
        }
    )

    get_or_create(
        db,
        SysUser,
        username="lab_c",
        defaults={
            "agency_id": lab_c.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "实验室C操作员",
            "role_code": "agency_operator",
            "status": "enabled"
        }
    )

    get_or_create(
        db,
        SysUser,
        username="auditor",
        defaults={
            "agency_id": cdc.id,
            "password_hash": get_password_hash("123456"),
            "real_name": "审计员",
            "role_code": "auditor",
            "status": "enabled"
        }
    )


def seed_nodes(db, cdc, hospital_a, hospital_b, lab_c):
    get_or_create(
        db,
        Node,
        node_code="CDC_NODE",
        defaults={
            "agency_id": cdc.id,
            "node_name": "疾控中心协调节点",
            "node_type": "coordinator",
            "endpoint": "http://127.0.0.1:9001",
            "status": "online",
            "last_heartbeat_at": datetime.now(),
            "description": "任务协调与结果汇总节点"
        }
    )

    get_or_create(
        db,
        Node,
        node_code="HOSPITAL_A_NODE",
        defaults={
            "agency_id": hospital_a.id,
            "node_name": "医院A计算节点",
            "node_type": "participant",
            "endpoint": "http://127.0.0.1:9002",
            "status": "online",
            "last_heartbeat_at": datetime.now(),
            "description": "医院A本地隐私计算节点"
        }
    )

    get_or_create(
        db,
        Node,
        node_code="HOSPITAL_B_NODE",
        defaults={
            "agency_id": hospital_b.id,
            "node_name": "医院B计算节点",
            "node_type": "participant",
            "endpoint": "http://127.0.0.1:9003",
            "status": "online",
            "last_heartbeat_at": datetime.now(),
            "description": "医院B本地隐私计算节点"
        }
    )

    get_or_create(
        db,
        Node,
        node_code="LAB_C_NODE",
        defaults={
            "agency_id": lab_c.id,
            "node_name": "实验室C计算节点",
            "node_type": "participant",
            "endpoint": "http://127.0.0.1:9004",
            "status": "online",
            "last_heartbeat_at": datetime.now(),
            "description": "实验室C本地隐私计算节点"
        }
    )


def seed_datasets(db, hospital_a, hospital_b, lab_c):
    case_schema = {
        "fields": [
            {"name": "patient_id", "type": "string", "label": "患者ID"},
            {"name": "visit_time", "type": "datetime", "label": "就诊时间"},
            {"name": "symptom_type", "type": "string", "label": "症状类型"},
            {"name": "diagnosis_code", "type": "string", "label": "诊断编码"}
        ]
    }

    test_schema = {
        "fields": [
            {"name": "patient_id", "type": "string", "label": "患者ID"},
            {"name": "sample_time", "type": "datetime", "label": "采样时间"},
            {"name": "test_item", "type": "string", "label": "检测项目"},
            {"name": "test_result", "type": "string", "label": "检测结果"}
        ]
    }

    get_or_create(
        db,
        Dataset,
        dataset_code="HOSPITAL_A_CASE",
        defaults={
            "agency_id": hospital_a.id,
            "dataset_name": "医院A流感样病例数据集",
            "dataset_type": "case",
            "storage_uri": "data/hospital_a/case.csv",
            "schema_json": case_schema,
            "status": "enabled",
            "description": "医院A本地病例数据"
        }
    )

    get_or_create(
        db,
        Dataset,
        dataset_code="HOSPITAL_B_CASE",
        defaults={
            "agency_id": hospital_b.id,
            "dataset_name": "医院B流感样病例数据集",
            "dataset_type": "case",
            "storage_uri": "data/hospital_b/case.csv",
            "schema_json": case_schema,
            "status": "enabled",
            "description": "医院B本地病例数据"
        }
    )

    get_or_create(
        db,
        Dataset,
        dataset_code="LAB_C_TEST",
        defaults={
            "agency_id": lab_c.id,
            "dataset_name": "实验室C检测结果数据集",
            "dataset_type": "test_result",
            "storage_uri": "data/lab_c/test_result.csv",
            "schema_json": test_schema,
            "status": "enabled",
            "description": "实验室C本地检测结果数据"
        }
    )


def seed_templates(db):
    get_or_create(
        db,
        StatTemplate,
        template_code="ILI_JOINT_STAT",
        defaults={
            "template_name": "流感样病例联合统计模板",
            "stat_type": "federated_statistics",
            "metrics_json": {
                "metrics": [
                    {
                        "metric_code": "case_count",
                        "metric_name": "病例数",
                        "unit": "人次"
                    },
                    {
                        "metric_code": "distinct_patient_count",
                        "metric_name": "去重后人数",
                        "unit": "人"
                    },
                    {
                        "metric_code": "positive_count",
                        "metric_name": "阳性数",
                        "unit": "人"
                    },
                    {
                        "metric_code": "positive_rate",
                        "metric_name": "阳性率",
                        "unit": "%"
                    }
                ]
            },
            "params_schema_json": {
                "params": [
                    {
                        "name": "stat_start_time",
                        "label": "统计开始时间",
                        "type": "datetime",
                        "required": True
                    },
                    {
                        "name": "stat_end_time",
                        "label": "统计结束时间",
                        "type": "datetime",
                        "required": True
                    },
                    {
                        "name": "disease_type",
                        "label": "疾病类型",
                        "type": "string",
                        "required": False,
                        "default": "流感样病例"
                    }
                ]
            },
            "status": "enabled",
            "description": "用于多机构流感样病例病例数、去重人数、阳性数、阳性率联合统计"
        }
    )


def main():
    db = SessionLocal()
    try:
        cdc, hospital_a, hospital_b, lab_c = seed_agencies(db)
        seed_users(db, cdc, hospital_a, hospital_b, lab_c)
        seed_nodes(db, cdc, hospital_a, hospital_b, lab_c)
        seed_datasets(db, hospital_a, hospital_b, lab_c)
        seed_templates(db)

        db.commit()
        print("初始化测试数据完成")
        print("默认管理员账号：admin")
        print("默认密码：123456")

    except Exception as e:
        db.rollback()
        print(f"初始化测试数据失败：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()