from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.domains import routers
from app.errors.handlers import register_exception_handlers
from app.middlewares.log import log_requests, logger, setup_logging
from app.middlewares.metrics_middleware import metrics_middleware
from app.redis_connector import get_redis, ping_redis


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    logger.info("Starting up...")
    redis = get_redis()
    await ping_redis(redis)
    logger.info("Redis работает")
    yield
    logger.complete()  # сброс очереди enqueue=True при завершении
    await redis.aclose()
    get_redis.cache_clear()  # чтобы следующий цикл создал новый клиент
    logger.info("Redis отключен")


app = FastAPI(title="Parking App", version="1.0", lifespan=lifespan)

app.middleware("http")(log_requests)
app.middleware("http")(metrics_middleware)

for router in routers:
    app.include_router(router)

register_exception_handlers(app)
