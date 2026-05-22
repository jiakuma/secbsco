from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 添加 dataset 索引
    try:
        conn.execute(text("CREATE INDEX idx_dataset_node_id ON dataset(node_id)"))
        print("Created idx_dataset_node_id")
    except Exception as e:
        print(f"idx_dataset_node_id: {e}")
    
    try:
        conn.execute(text("CREATE INDEX idx_dataset_data_type ON dataset(data_type)"))
        print("Created idx_dataset_data_type")
    except Exception as e:
        print(f"idx_dataset_data_type: {e}")
    
    # 添加 stat_template 索引
    try:
        conn.execute(text("CREATE INDEX idx_stat_template_agency_id ON stat_template(agency_id)"))
        print("Created idx_stat_template_agency_id")
    except Exception as e:
        print(f"idx_stat_template_agency_id: {e}")
    
    try:
        conn.execute(text("CREATE INDEX idx_stat_template_scenario ON stat_template(scenario)"))
        print("Created idx_stat_template_scenario")
    except Exception as e:
        print(f"idx_stat_template_scenario: {e}")
    
    # 添加 scenario 列（如果不存在）
    try:
        conn.execute(text("ALTER TABLE stat_template ADD COLUMN scenario VARCHAR(64) NULL COMMENT '适用场景'"))
        print("Added scenario column to stat_template")
    except Exception as e:
        print(f"scenario column: {e}")
    
    conn.commit()
    print("Done!")
