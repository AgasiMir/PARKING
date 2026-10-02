from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from app.domains.v1.cars.schemas import CarParkSchema, CarUnparkSchema
from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
)
from app.models.car import Car, CarStatus
from app.uow import UnitOfWork


class CarService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_cars(self) -> Sequence[Car]:
        return await self.uow.cars.get_cars()

    async def get_car_list_by_number(self, car_number: str) -> Sequence[Car]:
        return await self.uow.cars.get_car_list_by_number(car_number=car_number)

    async def park_car(self, park_car: CarParkSchema):
        car = await self.uow.cars.check_car_status(car_number=park_car.number)
        if car and car.status == CarStatus.parked:
            raise CarIsAlreadyParkedException

        try:
            return await self.uow.cars.park_car(park_car)
        except IntegrityError as err:
            raise CarIsAlreadyParkedException from err

    async def unpark_car(self, unpark_car: CarUnparkSchema):
        return await self.uow.cars.unpark_car(unpark_car)
