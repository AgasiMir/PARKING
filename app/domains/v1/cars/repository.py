from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.v1.cars.schemas import CarParkSchema, CarReadSchema, CarUnparkSchema
from app.errors.python_exceptions import CarNotFoundException
from app.models.car import Car


class CarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_car_status(self, car_number):
        car = await self.session.scalars(
            select(Car)
            .where(Car.number == car_number)
            .order_by(
                Car.created_at.desc(),
            )
            .with_for_update()
        )
        if not car:
            return None

        car = car.first()
        return car

    async def get_cars(self) -> Sequence[Car]:
        cars = await self.session.scalars(select(Car))
        return cars.all()

    async def get_car(self, car_number: str) -> Car:
        car = await self.session.scalar(select(Car).where(Car.number == car_number))

        if not car:
            raise CarNotFoundException

        return car

    async def park_car(self, park_car: CarParkSchema) -> CarReadSchema:
        db_park = Car(**park_car.model_dump(), status="parked")

        self.session.add(db_park)
        await self.session.flush()
        await self.session.refresh(db_park)

        return CarReadSchema.model_validate(db_park)

    async def unpark_car(self, unpark_car: CarUnparkSchema) -> CarReadSchema:
        car = await self.check_car_status(car_number=unpark_car.number)

        car.status = "unparked"

        await self.session.flush()
        await self.session.refresh(car)

        return CarReadSchema.model_validate(car)
