from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.domains.v1.cars.repository import CarRepository
from app.domains.v1.cars.schemas import CarParkSchema, CarUnparkSchema, ParkingReadSchema
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException
from app.models.car import CarStatus
from app.uow import UnitOfWork


async def test_park_car(db: UnitOfWork):
    car = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")

    parked_car = await db.cars.park_car(car)
    assert parked_car.status == CarStatus.parked
    assert parked_car.number == car.number
    assert isinstance(parked_car, ParkingReadSchema)


async def test_get_cars_empty_list(db: UnitOfWork):
    cars = await db.cars.get_cars()
    assert isinstance(cars, list)
    assert len(cars) == 0


async def test_get_cars(db: UnitOfWork):
    car_1 = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")
    car_2 = CarParkSchema(mark="Toyota", model="Camry", number="zz777ov", color="white")

    await db.cars.park_car(car_1)
    await db.cars.park_car(car_2)

    cars = await db.cars.get_cars()
    assert isinstance(cars[-1], ParkingReadSchema)
    assert len(cars) == 2


async def test_get_car_list_by_number(db: UnitOfWork):
    car_1 = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")
    car_2 = CarParkSchema(mark="Toyota", model="Camry", number="zz777ov", color="white")

    await db.cars.park_car(car_1)
    await db.cars.park_car(car_2)

    cars = await db.cars.get_car_list_by_number(car_number=car_2.number)
    assert isinstance(cars[-1], ParkingReadSchema)
    assert len(cars) == 1


async def test_unpark_car(db: UnitOfWork):
    car_1 = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")
    car_2 = CarParkSchema(mark="Toyota", model="Camry", number="zz777ov", color="white")

    unpark_car = CarUnparkSchema(number=car_2.number)

    await db.cars.park_car(car_1)
    await db.cars.park_car(car_2)

    unparked_car = await db.cars.unpark_car(unpark_car=unpark_car)
    assert unparked_car.status == CarStatus.unparked
    assert isinstance(unparked_car, ParkingReadSchema)


async def test_unpark_car_with_wrong_number(db: UnitOfWork):
    with pytest.raises(ValidationError):
        await db.cars.unpark_car(unpark_car=CarUnparkSchema(number="wrong_number"))


async def test_unpark_car_with_not_existing_number(db: UnitOfWork):
    with pytest.raises(CarNotFoundException):
        await db.cars.unpark_car(unpark_car=CarUnparkSchema(number="tt891y"))


async def test_unpark_unparked_car(db: UnitOfWork):
    car = CarParkSchema(mark="Toyota", model="Camry", number="zz777ov", color="white")

    unpark_car = CarUnparkSchema(number=car.number)

    await db.cars.park_car(car)

    unparked_car = await db.cars.unpark_car(unpark_car=unpark_car)
    assert unparked_car.status == CarStatus.unparked

    with pytest.raises(CarIsNotParkedException):
        await db.cars.unpark_car(unpark_car=unpark_car)


async def test_check_car_status_uses_for_update():
    session = AsyncMock()
    session.scalars.return_value = MagicMock(first=MagicMock(return_value=None))

    await CarRepository(session).check_car_status("db777xH")

    select_stmt = session.scalars.call_args.args[0]
    sql = str(select_stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
