from fastapi import APIRouter, status

from app.domains.dependencies import CarServiceDep
from app.domains.v1.cars.schemas import CarParkSchema, CarReadSchema, CarUnparkSchema
from app.errors.schemas import ErrorResponse

router = APIRouter(prefix="/cars", tags=["cars 🚗🚙🚓"])


@router.get("/", response_model=list[CarReadSchema])
async def get_cars(cars: CarServiceDep):
    return await cars.get_cars()


@router.get(
    "/{car_number}",
    response_model=CarReadSchema,
    summary="Получить машину по ее номеру",
    description="Возвращает машину и ее описание",
    responses={
        404: {
            "description": "Машина не найдена",
            "model": ErrorResponse,
        },
    },
)
async def get_car(cars: CarServiceDep, car_nubmer: str):
    return await cars.get_car(car_number=car_nubmer)


@router.post(
    "/park",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {
            "description": "Машина не найдена",
            "model": ErrorResponse,
        },
        409: {
            "description": "Машина уже припаркована.",
            "model": ErrorResponse,
        },
    },
)
async def park_car(cars: CarServiceDep, park_car: CarParkSchema):
    res = await cars.park_car(park_car=park_car)
    return {"message": res}


@router.patch(
    "/unpark",
    responses={
        404: {
            "description": "Машина не найдена",
            "model": ErrorResponse,
        },
        400: {
            "description": "Машина еще не припаркована.",
            "model": ErrorResponse,
        },
    },
)
async def unpark_car(cars: CarServiceDep, unpark_car: CarUnparkSchema):
    res = await cars.unpark_car(unpark_car=unpark_car)
    return {"message": res}
