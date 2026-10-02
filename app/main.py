from fastapi import FastAPI

from app.domains import routers
from app.errors.handlers import register_exception_handlers

app = FastAPI(title="Parking App", version="1.0")


for router in routers:
    app.include_router(router)

register_exception_handlers(app)
