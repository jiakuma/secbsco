from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 修改 stat_template.version 字段类型为 BIGINT
    try:
        conn.execute(text("ALTER TABLE stat_template MODIFY COLUMN version BIGINT NOT NULL DEFAULT 1 COMMENT '版本号'"))
        print("Modified stat_template.version to BIGINT")
    except Exception as e:
        print(f"Modify version: {e}")
    conn.commit()
    print("Done!")
