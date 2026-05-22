from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 检查群组6的模板
    result = conn.execute(text("""
        SELECT gt.id, gt.template_id, gt.auth_status, st.template_name, st.template_code
        FROM group_task_template gt
        JOIN stat_template st ON st.id = gt.template_id
        WHERE gt.group_id = 6 AND gt.auth_status = 'active'
    """))
    print("群组6已授权模板：")
    for row in result:
        print(f"  id={row[0]}, template_id={row[1]}, status={row[2]}, name={row[3]}, code={row[4]}")
