from app.core.database import Base, engine

# 必须导入所有模型，否则 SQLAlchemy 不会创建对应表
import app.models  # noqa


def init_db():
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


if __name__ == "__main__":
    init_db()