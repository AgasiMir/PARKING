from collections.abc import Sequence

from app.domains.v1.cars.schemas import CarParkSchema, CarUnparkSchema
from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
    CarIsNotParkedException,
    CarNotFoundException,
)
from app.models.car import Car, CarStatus
from app.uow import UnitOfWork


class CarService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_cars(self) -> Sequence[Car]:
        return await self.uow.cars.get_cars()

    async def get_car(self, car_number: str) -> Car:
        return await self.uow.cars.get_car(car_number=car_number)

    async def park_car(self, park_car: CarParkSchema):
        car = await self.uow.cars.check_car_status(car_number=park_car.number)
        if not car:
            return await self.uow.cars.park_car(park_car)
        if car and car.status == CarStatus.unparked:
            return await self.uow.cars.park_car(park_car)
        else:
            raise CarIsAlreadyParkedException

    async def unpark_car(self, unpark_car: CarUnparkSchema):
        car = await self.uow.cars.check_car_status(car_number=unpark_car.number)
        if not car:
            raise CarNotFoundException
        elif car.status == CarStatus.parked:
            return await self.uow.cars.unpark_car(unpark_car)
        else:
            raise CarIsNotParkedException
