from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Biosecurity Backend"
    APP_ENV: str = "dev"
    APP_DEBUG: bool = True

    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "123456"
    MYSQL_DATABASE: str = "biosecurity_stat"

    JWT_SECRET_KEY: str = "biosecurity-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # FISCO BCOS 上链服务配置
    # 当前 FastAPI 后端不直接连接 FISCO BCOS Python SDK，
    # 统一调用 Alice 节点上的 fisco_anchor_service。
    FISCO_ANCHOR_SERVICE_URL: str = "http://123.60.109.244:18080"
    FISCO_ANCHOR_API_KEY: str = "bio-anchor-2026-test"
    FISCO_ANCHOR_TIMEOUT_SECONDS: int = 10
    FISCO_CHAIN_TYPE: str = "fisco_bcos"
    FISCO_CONTRACT_ADDRESS: str = "0x6849f21d1e455e9f0712b1e99fa4fcd23758e8f1"

    # SecretFlow 联合统计服务配置
    # 当前 FastAPI 后端不直接运行 SecretFlow，统一调用 Alice 节点上的统计服务。
    SECRETFLOW_STAT_SERVICE_URL: str = "http://123.60.109.244:18180"
    SECRETFLOW_STAT_API_KEY: str = "bio-secretflow-2026-test"
    SECRETFLOW_STAT_TIMEOUT_SECONDS: int = 300
    SECRETFLOW_ALICE_CSV: str = "/data/alice_hospital_flu_202604.csv"
    SECRETFLOW_BOB_CSV: str = "/data/bob_hospital_flu_202604.csv"
    SECRETFLOW_DEFAULT_START_DATE: str = "2026-04-01"
    SECRETFLOW_DEFAULT_END_DATE: str = "2026-04-30"
    SECRETFLOW_DEFAULT_SYNDROME_TYPE: str = "ILI"

    # SecretFlow 联邦学习训练服务配置
    # 当前 FastAPI 后端不直接运行训练脚本，统一调用 Alice 节点上的 18181 训练服务。
    SECRETFLOW_FL_SERVICE_URL: str = "http://123.60.109.244:18181"
    SECRETFLOW_FL_API_KEY: str = "bio-secretflow-fl-2026-test"
    SECRETFLOW_FL_TIMEOUT_SECONDS: int = 900
    SECRETFLOW_FL_ALICE_CSV: str = "/data/alice_flu_fl_train.csv"
    SECRETFLOW_FL_BOB_CSV: str = "/data/bob_flu_fl_train.csv"
    SECRETFLOW_FL_EPOCHS: int = 5
    SECRETFLOW_FL_BATCH_SIZE: int = 32
    SECRETFLOW_FL_LEARNING_RATE: float = 0.001

    # Bio Task Runtime 配置（T2 时空轨迹预测任务）
    BIO_TASK_RUNTIME_URL: str = "http://123.60.109.244:18190"
    BIO_TASK_RUNTIME_TIMEOUT: int = 600

    # Alice Node Agent 配置（19090，用于自动启动 bio-task-runtime）
    ALICE_NODE_AGENT_URL: str = "http://123.60.109.244:19090"
    ALICE_NODE_AGENT_TIMEOUT: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()