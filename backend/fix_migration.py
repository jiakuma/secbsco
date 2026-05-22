from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 检查 dataset 表是否有新字段
    result = conn.execute(text("SHOW COLUMNS FROM dataset LIKE 'node_id'"))
    has_node_id = result.fetchone()
    
    if not has_node_id:
        print("Adding missing columns to dataset table...")
        conn.execute(text("ALTER TABLE dataset ADD COLUMN node_id BIGINT NULL COMMENT '所属节点ID'"))
        conn.execute(text("ALTER TABLE dataset ADD COLUMN data_type VARCHAR(32) NULL COMMENT '数据类型: file/database/api'"))
        conn.execute(text("ALTER TABLE data_location VARCHAR(512) NULL COMMENT '数据位置'")) if False else conn.execute(text("ALTER TABLE dataset ADD COLUMN data_location VARCHAR(512) NULL COMMENT '数据位置'"))
        conn.execute(text("ALTER TABLE dataset ADD COLUMN template_id BIGINT NULL COMMENT '数据模板ID'"))
        conn.execute(text("ALTER TABLE dataset ADD COLUMN version BIGINT NOT NULL DEFAULT 1 COMMENT '版本号'"))
        conn.execute(text("ALTER TABLE dataset ADD COLUMN created_by BIGINT NULL COMMENT '创建人ID'"))
        conn.commit()
        print("Dataset columns added successfully")
    else:
        print("Dataset already has new columns")
    
    # 更新 alembic_version 到 008
    conn.execute(text("UPDATE alembic_version SET version_num = '008_extend_dataset_and_template'"))
    conn.commit()
    print("Alembic version updated to 008_extend_dataset_and_template")
