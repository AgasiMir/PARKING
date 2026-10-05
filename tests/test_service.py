import asyncio
from datetime import datetime

import pytest

from app.core.database import async_session_null_pool
from app.domains.v1.cars.schemas import (
    CarParkingAndPriceSchema,
    CarParkSchema,
    CarUnparkSchema,
    ParkingPriceTimeCursorSchema,
    ParkingReadSchema,
)
from app.domains.v1.cars.service import CarService
from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
    CarIsNotParkedException,
    CarNotFoundException,
)
from app.models.car import Car, CarStatus
from app.uow import UnitOfWork


@pytest.fixture()
async def park_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    res = await db.cars.park_car(park_car=park_car)
    return res


async def test_get_parking_data(db: UnitOfWork):
    parking_data = await CarService(db).get_parking_data(limit=10)
    assert isinstance(parking_data, ParkingPriceTimeCursorSchema)
    assert len(parking_data.parking_and_price_data) == 0


async def test_get_car_list_by_number(db: UnitOfWork, park_car):
    parking_data = await CarService(db).get_parking_data(limit=10, car_number=park_car.number)
    assert isinstance(parking_data, ParkingPriceTimeCursorSchema)
    assert len(parking_data.parking_and_price_data) == 1
    assert parking_data.next_cursor is None


async def test_park_car(db: UnitOfWork):
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="ak47TT", color="red")
    car = await CarService(db).park_car(park_car=park_car)
    assert isinstance(car, ParkingReadSchema)


async def test_park_parked_car(db: UnitOfWork, park_car):
    with pytest.raises(CarIsAlreadyParkedException):
        await CarService(db).park_car(park_car=park_car)


async def test_unpark_car(db: UnitOfWork, park_car):
    unpark_car = CarUnparkSchema(number=park_car.number)
    unparked_car = await CarService(db).unpark_car(unpark_car=unpark_car)
    assert isinstance(unparked_car, CarParkingAndPriceSchema)


async def test_unpark_not_existing_car(db: UnitOfWork):
    unpark_car = CarUnparkSchema(number="ak47TT")
    with pytest.raises(CarNotFoundException):
        await CarService(db).unpark_car(unpark_car=unpark_car)


async def test_unpark_unparked_car(db: UnitOfWork, park_car):
    unpark_car = CarUnparkSchema(number=park_car.number)
    unparked_car = await CarService(db).unpark_car(unpark_car=unpark_car)
    assert isinstance(unparked_car, CarParkingAndPriceSchema)

    with pytest.raises(CarIsNotParkedException):
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
    assert len(errors) == 1 and errors[0] == CarIsNotParkedException


async def test_concurrent_parks_serialized():
    """Гонка при парковке одного номера из двух транзакций.

    SELECT ... FOR UPDATE не блокирует несуществующую строку, поэтому обе
    транзакции видят None и обе идут на INSERT. Второй INSERT натыкается на
    частичный уникальный индекс uq_cars_number_parked -> IntegrityError,
    который сервис превращает в CarIsAlreadyParkedException.
    """
    car = CarParkSchema(mark="Toyota", model="Corolla", number="db777xH", color="red")

    async def park_once():
        # Каждый вызов — СВОЙ UoW: commit происходит при выходе из async with.
        async with UnitOfWork(async_session_null_pool) as uow:
            return await CarService(uow=uow).park_car(car)

    results = await asyncio.gather(park_once(), park_once(), return_exceptions=True)

    ok = [r for r in results if not isinstance(r, Exception)]
    errors = [type(r) for r in results if isinstance(r, Exception)]

    assert len(ok) == 1
    assert isinstance(ok[0], ParkingReadSchema)
    assert ok[0].status == CarStatus.parked
    assert len(errors) == 1 and errors[0] == CarIsAlreadyParkedException

    # в базе осталась ровно одна parked-запись
    async with UnitOfWork(async_session_null_pool) as verify_uow:
        data = await verify_uow.cars.get_parking_data(limit=10, car_number="db777xH")
    assert len(data.cars) == 1
    assert data.cars[0].status == CarStatus.parked


async def test_get_parking_data_with_prices_and_cursor(db: UnitOfWork):
    """Интеграция сервиса с репозиторием: цены, порядок, курсор и has_more."""
    # Даты проставляются сервером (func.now()), поэтому вставляем Car с
    # контролируемым временем напрямую, как в фикстуре park_cars из test_repo.
    cars = [
        Car(
            mark="Toyota",
            model="Corolla",
            number="aa1111A",
            color="red",
            status=CarStatus.parked,
            created_at=datetime(2026, 10, 1, 10, 0, 0),
            updated_at=datetime(2026, 10, 1, 10, 30, 0),  # 30 мин -> 400.0
        ),
        Car(
            mark="Toyota",
            model="Camry",
            number="bb2222B",
            color="white",
            status=CarStatus.parked,
            created_at=datetime(2026, 10, 2, 10, 0, 0),
            updated_at=datetime(2026, 10, 2, 11, 20, 0),  # 80 мин -> 760.0
        ),
        Car(
            mark="Toyota",
            model="RAV4",
            number="cc3333C",
            color="blue",
            status=CarStatus.parked,
            created_at=datetime(2026, 10, 3, 10, 0, 0),
            updated_at=datetime(2026, 10, 3, 13, 37, 0),  # 217 мин -> 1719.0
        ),
    ]
    db._session.add_all(cars)
    await db._session.flush()

    service = CarService(db)

    # первая страница: самые свежие (created_at DESC) -> cc3333C, bb2222B
    page_1 = await service.get_parking_data(limit=2)

    assert len(page_1.parking_and_price_data) == 2
    assert page_1.parking_and_price_data[0].parking_data.number == "cc3333C"
    assert page_1.parking_and_price_data[0].price_time_data.park_time == 217.0
    assert page_1.parking_and_price_data[0].price_time_data.price == 1719.0

    assert page_1.parking_and_price_data[1].parking_data.number == "bb2222B"
    assert page_1.parking_and_price_data[1].price_time_data.park_time == 80.0
    assert page_1.parking_and_price_data[1].price_time_data.price == 760.0

    assert page_1.has_more is True
    assert page_1.next_cursor is not None
    assert page_1.next_cursor.last_id == page_1.parking_and_price_data[1].parking_data.id
    assert (
        page_1.next_cursor.last_created_at
        == page_1.parking_and_price_data[1].parking_data.created_at
    )

    # вторая страница по курсору: оставшаяся aa1111A, без дубликатов
    page_2 = await service.get_parking_data(
        limit=2,
        cursor_id=page_1.next_cursor.last_id,
        created_at=page_1.next_cursor.last_created_at,
    )

    assert len(page_2.parking_and_price_data) == 1
    assert page_2.parking_and_price_data[0].parking_data.number == "aa1111A"
    assert page_2.parking_and_price_data[0].price_time_data.park_time == 30.0
    assert page_2.parking_and_price_data[0].price_time_data.price == 400.0
    assert page_2.has_more is False
    assert page_2.next_cursor is None


async def test_get_car_list_by_number_filters_data(db: UnitOfWork):
    """Фильтрация по номеру на уровне сервиса: чужие номера отсекаются."""
    service = CarService(db)

    await service.park_car(
        CarParkSchema(mark="Toyota", model="Corolla", number="aa1111A", color="red")
    )
    await service.park_car(
        CarParkSchema(mark="Honda", model="Civic", number="bb2222B", color="blue")
    )

    parking_data = await service.get_parking_data(car_number="aa1111A", limit=10)

    assert len(parking_data.parking_and_price_data) == 1
    only = parking_data.parking_and_price_data[0].parking_data
    assert only.number == "aa1111A"
    assert only.mark == "Toyota"
    assert only.status == CarStatus.parked
    assert parking_data.has_more is False
    assert parking_data.next_cursor is None


async def test_repark_after_unpark(db: UnitOfWork):
    """Бизнес-правило: unparked машина может снова парковаться (частичный индекс)."""
    service = CarService(db)
    park_car = CarParkSchema(mark="Toyota", model="Corolla", number="aa1111A", color="red")

    first = await service.park_car(park_car=park_car)
    assert first.status == CarStatus.parked

    unparked = await service.unpark_car(unpark_car=CarUnparkSchema(number=first.number))
    assert unparked.parking_data.status == CarStatus.unparked
    # парковка длилась меньше минуты -> park_time == 0, тариф short
    assert unparked.price_time_data.park_time in (0.0, 1.0)
    assert unparked.price_time_data.price >= 100.0

    second = await service.park_car(park_car=park_car)
    assert second.status == CarStatus.parked

    history = await service.get_parking_data(car_number="aa1111A", limit=10)
    assert len(history.parking_and_price_data) == 2
    statuses = {item.parking_data.status for item in history.parking_and_price_data}
    assert statuses == {CarStatus.parked, CarStatus.unparked}
