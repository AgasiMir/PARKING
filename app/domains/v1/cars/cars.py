from fastapi import APIRouter, status

from app.domains.dependencies import CarServiceDep
from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    CarReadSchema,
    CarUnparkSchema,
)
from app.errors.schemas import ErrorResponse

router = APIRouter(prefix="/v1/cars", tags=["cars 🚗🚙🚓"])


@router.get("/", response_model=list[CarParkingAndPriceSchema])
async def get_cars(cars: CarServiceDep):
    return await cars.get_cars()


@router.get(
    "/{car_number}",
    response_model=list[CarParkingAndPriceSchema],
    summary="Получить историю машины (заезд и выезд из парковки) по номеру",
)
async def get_car_list_by_number(cars: CarServiceDep, car_number: str):
    return await cars.get_car_list_by_number(car_number=car_number)


@router.post(
    "/park/",
    response_model=CarReadSchema,
    summary="Паркование машины по номеру",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Машина уже припаркована.",
            "model": ErrorResponse,
        },
    },
)
async def park_car(cars: CarServiceDep, park_car: CarParkSchema):
    return await cars.park_car(park_car=park_car)


@router.patch(
    "/unpark/",
    summary="Убрать машину из парковки по номеру",
    response_model=CarParkingAndPriceSchema,
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
    return await cars.unpark_car(unpark_car=unpark_car)
