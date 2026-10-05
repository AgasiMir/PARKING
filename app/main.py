from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.domains import routers
from app.errors.handlers import register_exception_handlers
from app.middlewares.log import log_requests, logger, setup_logging
from app.middlewares.metrics_middleware import metrics_middleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    logger.info("Starting up...")
    yield
    logger.complete()  # сброс очереди enqueue=True при завершении


app = FastAPI(title="Parking App", version="1.0", lifespan=lifespan)

app.middleware("http")(log_requests)
app.middleware("http")(metrics_middleware)

for router in routers:
    app.include_router(router)

register_exception_handlers(app)
