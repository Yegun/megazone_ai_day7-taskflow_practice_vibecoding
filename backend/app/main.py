from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from . import auth, db
from .routes import auth as auth_routes
from .routes import division as division_routes
from .routes import suggest as suggest_routes
from .routes import tasks


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    auth.load_env_file()
    auth.secret_key()  # 비밀값이 없으면 기동 단계에서 실패한다.
    db.init_db()
    yield


app = FastAPI(title="task-flow", lifespan=lifespan)

api = APIRouter(prefix="/api")


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api.include_router(auth_routes.router)
api.include_router(suggest_routes.router)
api.include_router(division_routes.router)
api.include_router(tasks.router)
app.include_router(api)
