from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, event

from app.db import db_path

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모델 메타데이터를 쓰지 않는다. 마이그레이션은 직접 쓴 SQL 로만 한다(autogenerate 없음).
target_metadata = None


def run_migrations_online() -> None:
    engine = create_engine(f"sqlite:///{db_path()}")

    # pysqlite 의 기본 트랜잭션 처리는 DDL 앞에서 커밋해 버린다.
    # 마이그레이션 전체가 하나의 트랜잭션이 되도록 직접 BEGIN 한다.
    @event.listens_for(engine, "connect")
    def _no_implicit_tx(dbapi_connection, _):  # noqa: ANN001
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(conn):  # noqa: ANN001
        conn.exec_driver_sql("BEGIN")

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("offline 모드는 지원하지 않습니다.")
run_migrations_online()
