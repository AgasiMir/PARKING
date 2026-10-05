from .health import router as health_router
from .v1.cars.cars import router as v1_car_router

routers = [v1_car_router, health_router]
