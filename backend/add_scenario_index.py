from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("CREATE INDEX idx_stat_template_scenario ON stat_template(scenario)"))
        print("Created idx_stat_template_scenario")
    except Exception as e:
        print(f"idx_stat_template_scenario: {e}")
    conn.commit()
    print("Done!")
