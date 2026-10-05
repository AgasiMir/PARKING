from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.domains.v1.cars.repository import CarRepository
from app.domains.v1.cars.schemas import (
    CarParkSchema,
    CarUnparkSchema,
    ParkingReadSchema,
    ParkingReadSchemaWithCursor,
)
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException
from app.models.car import Car, CarStatus
from app.uow import UnitOfWork


@pytest.fixture()
async def park_cars(db: UnitOfWork):
    car_1 = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")
    await db.cars.park_car(car_1)

    result = await db.cars.get_parking_data(limit=1, car_number="db777xH")
    car_2_created_at = result.cars[0].created_at + timedelta(hours=1)

    db_car = Car(
        mark="Toyota",
        model="Camry",
        number="zz777ov",
        color="white",
        status=CarStatus.parked,
        created_at=car_2_created_at,
        updated_at=car_2_created_at,
    )

    repo = CarRepository(db._session)
    repo.session.add(db_car)
    await repo.session.flush()


async def test_cars_created_at(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(limit=2)
    assert result.cars[0].created_at - result.cars[1].created_at == timedelta(hours=1)


async def test_park_car(db: UnitOfWork):
    car = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")

    parked_car = await db.cars.park_car(car)
    assert parked_car.status == CarStatus.parked
    assert parked_car.number == car.number
    assert isinstance(parked_car, ParkingReadSchema)


async def test_get_empty_parking_data(db: UnitOfWork):
    result = await db.cars.get_parking_data(limit=10)
    assert isinstance(result, ParkingReadSchemaWithCursor)
    assert result.has_more is False
    assert len(result.cars) == 0
    assert result.next_cursor is None


async def test_get_parking_data(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(limit=2)
    assert isinstance(result, ParkingReadSchemaWithCursor)
    assert isinstance(result.cars[0], ParkingReadSchema)


async def test_get_parking_data_by_car_number(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(limit=5, car_number="zz777ov")
    assert result.cars[0].number == "zz777ov"


async def test_get_parking_data_by_car_number_list(db: UnitOfWork, park_cars):
    unpark_car = CarUnparkSchema(number="zz777ov")
    await db.cars.unpark_car(unpark_car=unpark_car)

    car_3 = CarParkSchema(mark="Toyota", model="Camry", number="zz777ov", color="white")
    await db.cars.park_car(car_3)

    result = await db.cars.get_parking_data(limit=5, car_number="zz777ov")
    assert len(result.cars) == 2


async def test_unpark_car(db: UnitOfWork, park_cars):
    unpark_car = CarUnparkSchema(number="zz777ov")

    unparked_car = await db.cars.unpark_car(unpark_car=unpark_car)
    assert unparked_car.status == CarStatus.unparked
    assert isinstance(unparked_car, ParkingReadSchema)


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


async def test_get_parking_data_with_has_more(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(limit=1)
    assert result.cars[0].number == "zz777ov"
    assert result.has_more is True


async def test_get_parking_data_without_has_more(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(limit=2)
    assert result.has_more is False


async def test_get_parkings_by_cursor_with_no_result(db: UnitOfWork, park_cars):
    result = await db.cars.get_parking_data(1)
    last_id = result.model_dump()["cars"][-1]["id"]
    last_created_at = result.model_dump()["cars"][-1]["created_at"]

    assert result.model_dump()["next_cursor"]["last_id"] == last_id

    res = await db.cars.get_parking_data(limit=5, cursor_id=last_id, created_at=last_created_at)
    assert res.model_dump()["next_cursor"] is None

    assert isinstance(res, ParkingReadSchemaWithCursor)


async def test_tie_break_by_cursor(db: UnitOfWork, park_cars):
    # у car_3 created_at равен created_at у car_1, за это отвечает postgesql,
    # а именно, server_default=func.now(). car_2_created_at же добавляет 1 час
    # к created_at у car_1 для целей тестирования

    car_3 = CarParkSchema(mark="Toyota", model="Land Cruiser", number="ak4774x", color="grey")
    await db.cars.park_car(car_3)

    page_1_res = await db.cars.get_parking_data(limit=2)
    page_1_last_id = page_1_res.model_dump()["cars"][-1]["id"]
    page_1_last_created_at = page_1_res.model_dump()["cars"][-1]["created_at"]

    page_2_res = await db.cars.get_parking_data(
        limit=2,
        cursor_id=page_1_last_id,
        created_at=page_1_last_created_at,
    )
    page_1_cars = page_1_res.model_dump()["cars"]
    page_2_cars = page_2_res.model_dump()["cars"]

    page_1_ids = {car["id"] for car in page_1_cars}
    page_2_ids = {car["id"] for car in page_2_cars}

    # первая страница всегда начинается с самой свежей машины (детерминированно)
    assert page_1_cars[0]["number"] == "zz777ov"
    assert len(page_1_cars) == 2
    assert page_1_res.has_more is True

    # вторая страница — ровно одна оставшаяся машина
    assert len(page_2_cars) == 1
    assert page_2_res.has_more is False

    # нет дубликатов на границе страниц и ничего не потеряно
    assert not page_1_ids & page_2_ids
    assert len(page_1_ids | page_2_ids) == 3
