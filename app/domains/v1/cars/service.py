from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    CarParkTimePriceSchema,
    CarUnparkSchema,
    ParkingPriceTimeCursorSchema,
    ParkingReadSchema,
)
from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
)
from app.models.car import CarStatus
from app.park_price.get_price import Pricing, pricing_strategies_map, set_pricing_strategies
from app.uow import UnitOfWork


class CarService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def get_cars(self) -> list[CarParkingAndPriceSchema]:
        cars = await self.uow.cars.get_cars()
        return [await self._get_car_parking_price_and_time(car) for car in cars]

    async def get_car_list_by_number(self, car_number: str) -> list[CarParkingAndPriceSchema]:
        cars = await self.uow.cars.get_car_list_by_number(car_number=car_number)
        return [await self._get_car_parking_price_and_time(car) for car in cars]

    async def get_parking_data(
        self,
        limit: int,
        cursor_id: UUID | None,
        created_at: datetime | None,
        car_number: str | None = None,
    ) -> ParkingPriceTimeCursorSchema:
        parking_data = await self.uow.cars.get_parking_data(
            car_number=car_number,
            limit=limit,
            cursor_id=cursor_id,
            created_at=created_at,
        )
        # return parking_data
        cars = [ParkingReadSchema.model_validate(car) for car in parking_data.model_dump()["cars"]]
        price_time = [await self._get_car_parking_price_and_time(car) for car in cars]

        # return price_time
        return ParkingPriceTimeCursorSchema(
            **{
                "parking_and_price_data": price_time,
                "has_more": parking_data.model_dump()["has_more"],
                "next_cursor": parking_data.model_dump()["next_cursor"],
            }
        )

    async def park_car(self, park_car: CarParkSchema) -> ParkingReadSchema:
        car = await self.uow.cars.check_car_status(car_number=park_car.number)
        if car and car.status == CarStatus.parked:
            raise CarIsAlreadyParkedException

        try:
            return await self.uow.cars.park_car(park_car)
        except IntegrityError as err:
            raise CarIsAlreadyParkedException from err

    async def unpark_car(self, unpark_car: CarUnparkSchema) -> CarParkingAndPriceSchema:
        car = await self.uow.cars.unpark_car(unpark_car)
        return await self._get_car_parking_price_and_time(car)

    async def _get_car_parking_price_and_time(
        self, car: ParkingReadSchema
    ) -> CarParkingAndPriceSchema:
        park_time = (car.updated_at - car.created_at).total_seconds() // 60
        price_strategy = set_pricing_strategies(park_time)
        set_price_strategy = pricing_strategies_map[price_strategy]

        price = Pricing(set_price_strategy).get_park_price(park_time)

        price_time = CarParkTimePriceSchema(
            park_time=park_time,
            price=price,
        )
        return CarParkingAndPriceSchema(parking_data=car, price_time_data=price_time)
