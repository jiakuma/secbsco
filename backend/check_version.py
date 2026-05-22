from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, version FROM stat_template"))
    rows = result.fetchall()
    print("stat_template version values:")
    for row in rows:
        print(f"  id={row[0]}, version='{row[1]}'")
