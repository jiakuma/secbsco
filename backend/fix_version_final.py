from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 更新版本值为数字
    try:
        conn.execute(text("UPDATE stat_template SET version = '1'"))
        conn.commit()
        print("Updated all version values to '1'")
    except Exception as e:
        print(f"Update version: {e}")
    
    # 修改字段类型
    try:
        conn.execute(text("ALTER TABLE stat_template MODIFY COLUMN version BIGINT NOT NULL DEFAULT 1 COMMENT '版本号'"))
        print("Modified stat_template.version to BIGINT")
    except Exception as e:
        print(f"Modify version: {e}")
    conn.commit()
    print("Done!")
