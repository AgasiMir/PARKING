import asyncio
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.database import async_session_null_pool
from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    CarUnparkSchema,
    ParkingReadSchema,
)
from app.domains.v1.cars.service import CarService
from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
    CarIsNotParkedException,
    CarNotFoundException,
)
from app.models.car import CarStatus
from app.uow import UnitOfWork


async def test_get_car_parking_price_and_time_short_term(db: UnitOfWork):
    car = ParkingReadSchema(
        id=uuid4(),
        mark="Toyota",
        model="Corolla",
        number="ak47TT",
        color="red",
        status=CarStatus.parked,
        created_at=datetime(2026, 10, 3, 12, 0, 0),
        updated_at=datetime(2026, 10, 3, 12, 30, 0),
    )

    price_data = await CarService(db)._get_car_parking_price_and_time(car)
    assert isinstance(price_data, CarParkingAndPriceSchema)
    assert price_data.model_dump()["price_time_data"]["price"] == 400.0
    assert price_data.model_dump()["price_time_data"]["park_time"] == 30.0


async def test_get_car_parking_price_and_time_mid_term(db: UnitOfWork):
    car = ParkingReadSchema(
        id=uuid4(),
        mark="Toyota",
        model="Corolla",
        number="ak47TT",
        color="red",
        status=CarStatus.parked,
        created_at=datetime(2026, 10, 3, 12, 0, 0),
        updated_at=datetime(2026, 10, 3, 13, 20, 0),
    )

    price_data = await CarService(db)._get_car_parking_price_and_time(car)
    assert isinstance(price_data, CarParkingAndPriceSchema)
    assert price_data.model_dump()["price_time_data"]["price"] == 760.0
    assert price_data.model_dump()["price_time_data"]["park_time"] == 80.0


async def test_get_car_parking_price_and_time_long_term(db: UnitOfWork):
    car = ParkingReadSchema(
        id=uuid4(),
        mark="Toyota",
        model="Corolla",
        number="ak47TT",
        color="red",
        status=CarStatus.parked,
        created_at=datetime(2026, 10, 3, 12, 0, 0),
        updated_at=datetime(2026, 10, 3, 15, 37, 0),
    )

    price_data = await CarService(db)._get_car_parking_price_and_time(car)
    assert isinstance(price_data, CarParkingAndPriceSchema)
    assert price_data.model_dump()["price_time_data"]["price"] == 1719.0
    assert price_data.model_dump()["price_time_data"]["park_time"] == 217.0


async def test_get_cars(db: UnitOfWork):
    cars = await CarService(db).get_cars()
    assert isinstance(cars, list)


async def test_get_car_list_by_number(db: UnitOfWork):
    cars = await CarService(db).get_car_list_by_number("ak47TT")
    assert isinstance(cars, list)
    assert len(cars) == 0


async def test_park_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    car = await CarService(db).park_car(park_car=park_car)
    assert isinstance(car, ParkingReadSchema)


async def test_park_parked_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    car = await CarService(db).park_car(park_car=park_car)
    assert isinstance(car, ParkingReadSchema)

    with pytest.raises(CarIsAlreadyParkedException):
        await CarService(db).park_car(park_car=park_car)


async def test_unpark_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    car = await CarService(db).park_car(park_car=park_car)
    assert isinstance(car, ParkingReadSchema)

    unpark_car = CarUnparkSchema(number=car.number)
    unparked_car = await CarService(db).unpark_car(unpark_car=unpark_car)
    assert isinstance(unparked_car, CarParkingAndPriceSchema)


async def test_unpark_not_existing_car(db: UnitOfWork):
    unpark_car = CarUnparkSchema(number="ak47TT")
    with pytest.raises(CarNotFoundException):
        await CarService(db).unpark_car(unpark_car=unpark_car)


async def test_unpark_unparked_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    car = await CarService(db).park_car(park_car=park_car)
    assert isinstance(car, ParkingReadSchema)

    unpark_car = CarUnparkSchema(number=car.number)
    unparked_car = await CarService(db).unpark_car(unpark_car=unpark_car)
    assert isinstance(unparked_car, CarParkingAndPriceSchema)

    with pytest.raises(CarIsNotParkedException):
        await CarService(db).unpark_car(unpark_car=unpark_car)


async def test_unpark_car_with_wrong_number(db: UnitOfWork):
    with pytest.raises(ValidationError):
        unpark_car = CarUnparkSchema(number="ak47TTxxx")
        await CarService(db).unpark_car(unpark_car=unpark_car)


async def test_concurrent_unparks_serialized():
    car = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")
    unpark = CarUnparkSchema(number=car.number)

    # 1) Паркуем и ЗАКОММИЧИВАЕМ: выход из async with = commit.
    #    Фикстуру db использовать нельзя — её транзакция открыта,
    #    и строка не видна другим соединениям.
    async with UnitOfWork(async_session_null_pool) as setup_uow:
        await setup_uow.cars.park_car(car)

    async def unpark_once():
        # 2) Каждый вызов — СВОЙ UoW, обязательно через async with
        async with UnitOfWork(async_session_null_pool) as uow:
            return await CarService(uow=uow).unpark_car(unpark)

    results = await asyncio.gather(unpark_once(), unpark_once(), return_exceptions=True)

    ok = [r for r in results if not isinstance(r, Exception)]
    errors = [type(r) for r in results if isinstance(r, Exception)]

    assert len(ok) == 1
    assert errors == [CarIsNotParkedException]
