from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.database import engine
from app.exceptions.handlers import register_exception_handlers
from app.models.customer import Base
from app.routers.customer_router import router as customer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Customer Management API", lifespan=lifespan)

register_exception_handlers(app)
app.include_router(customer_router)


@app.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=settings.DEBUG)
