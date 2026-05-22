from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    row = result.fetchone()
    print(f"Current alembic version: {row[0] if row else 'None'}")
