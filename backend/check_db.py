from sqlalchemy import create_engine, inspect
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

print("=== dataset columns ===")
cols = inspector.get_columns('dataset')
for c in cols:
    print(f"  {c['name']}: {c['type']}")

print("\n=== stat_template columns ===")
cols2 = inspector.get_columns('stat_template')
for c in cols2:
    print(f"  {c['name']}: {c['type']}")
