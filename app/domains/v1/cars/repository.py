from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.v1.cars.schemas import CarParkSchema, CarReadSchema, CarUnparkSchema
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException
from app.models.car import Car, CarStatus


class CarRepository:
    _schema = CarReadSchema

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_car_status(self, car_number: str) -> Car | None:
        result = await self.session.scalars(
            select(Car)
            .where(Car.number == car_number)
            .order_by(
                Car.created_at.desc(),
            )
            .with_for_update()
        )
        car = result.first()
        return car

    async def get_cars(self) -> list[CarReadSchema]:
        cars = await self.session.scalars(select(Car))
        return [self._schema.model_validate(car) for car in cars.all()]

    async def get_car_list_by_number(self, car_number: str) -> list[CarReadSchema]:
        car = await self.session.scalars(
            select(Car)
            .where(Car.number == car_number)
            .order_by(
                Car.created_at.desc(),
            )
        )

        return [self._schema.model_validate(car) for car in car.all()]

    async def park_car(self, park_car: CarParkSchema) -> CarReadSchema:
        db_park = Car(**park_car.model_dump(), status=CarStatus.parked)

        self.session.add(db_park)
        await self.session.flush()
        await self.session.refresh(db_park)

        return self._schema.model_validate(db_park)

    async def unpark_car(self, unpark_car: CarUnparkSchema) -> CarReadSchema:
        car = await self.check_car_status(car_number=unpark_car.number)

        if car is None:
            raise CarNotFoundException

        if car.status == CarStatus.unparked:
            raise CarIsNotParkedException

        car.status = CarStatus.unparked

        await self.session.flush()
        await self.session.refresh(car)

        return self._schema.model_validate(car)
