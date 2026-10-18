from fastapi import APIRouter, Body, Depends, status

from app.domains.dependencies import (
    CarServiceDep,
    CarServiceReadOnlyDep,
    CursorPaginationDep,
    rate_limit_get_parking_data,
    rate_limit_park_car,
    rate_limit_unpark_car,
)
from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    CarUnparkSchema,
    ParkingPriceTimeCursorSchema,
    ParkingReadSchema,
)
from app.errors.schemas import ErrorResponse

router = APIRouter(prefix="/v1/cars", tags=["cars 🚗🚙🚓"])


@router.get(
    "/",
    response_model=ParkingPriceTimeCursorSchema,
    dependencies=[Depends(rate_limit_get_parking_data)],
)
async def get_cars(cars: CarServiceReadOnlyDep, cursor_pagination: CursorPaginationDep):
    return await cars.get_parking_data(
        limit=cursor_pagination.limit,
        created_at=cursor_pagination.created_at,
        cursor_id=cursor_pagination.cursor_id,
    )


@router.get(
    "/{car_number}",
    response_model=ParkingPriceTimeCursorSchema,
    summary="Получить историю машины (заезд и выезд из парковки) по номеру",
    dependencies=[Depends(rate_limit_get_parking_data)],
)
async def get_car_list_by_number(
    cars: CarServiceReadOnlyDep,
    cursor_pagination: CursorPaginationDep,
    car_number: str,
):
    return await cars.get_parking_data(
        car_number=car_number,
        limit=cursor_pagination.limit,
        created_at=cursor_pagination.created_at,
        cursor_id=cursor_pagination.cursor_id,
    )


# ruff: noqa: B008
@router.post(
    "/park/",
    response_model=ParkingReadSchema,
    summary="Паркование машины по номеру",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {
            "description": "Машина уже припаркована.",
            "model": ErrorResponse,
        },
    },
    dependencies=[Depends(rate_limit_park_car)],
)
async def park_car(
    cars: CarServiceDep,
    park_car: CarParkSchema = Body(
        openapi_examples={
            "1": {
                "summary": "Park The Car",
                "value": {
                    "mark": "Toyota",
                    "model": "Camry",
                    "number": "ax74Vz",
                    "color": "grey",
                },
            }
        }
    ),
):
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
    dependencies=[Depends(rate_limit_unpark_car)],
)
async def unpark_car(cars: CarServiceDep, unpark_car: CarUnparkSchema):
    return await cars.unpark_car(unpark_car=unpark_car)
