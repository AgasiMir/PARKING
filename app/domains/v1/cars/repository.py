from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.v1.cars.schemas import (
    CarParkSchema,
    CarUnparkSchema,
    CursorReadSchema,
    ParkingReadSchema,
    ParkingReadSchemaWithCursor,
)
from app.errors.python_exceptions import CarIsNotParkedException, CarNotFoundException
from app.models.car import Car, CarStatus


class CarRepository:
    _schema = ParkingReadSchema

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

    async def get_parking_data(
        self,
        limit: int,
        car_number: str | None,
        cursor_id: UUID | None,
        created_at: datetime | None,
    ) -> ParkingReadSchemaWithCursor:
        # запрашиваем на одну запись больше, чтобы понять, есть ли следующая страница
        filters = []

        if car_number:
            filters.append(Car.number == car_number)

        stmt = (
            select(Car)
            .where(*filters)
            .order_by(Car.created_at.desc(), Car.id.desc())
            .limit(limit + 1)
        )

        # следующая страница = записи "старше" курсора (порядок DESC);
        # при отсутствии курсора — первая страница без WHERE
        if cursor_id is not None and created_at is not None:
            stmt = stmt.where(
                *filters,
                or_(
                    Car.created_at < created_at,
                    and_(
                        Car.created_at == created_at,
                        Car.id < cursor_id,
                    ),
                ),
            )

        rows = list((await self.session.scalars(stmt)).all())

        has_more = len(rows) > limit  # есть ли запись за пределами страницы
        page_rows = rows[:limit]  # отрезаем лишнюю "смотрящую" запись

        result = [self._schema.model_validate(car) for car in page_rows]

        if not result:
            return ParkingReadSchemaWithCursor(
                cars=[],
                has_more=False,
                next_cursor=None,
            )

        return ParkingReadSchemaWithCursor(
            cars=result,
            has_more=has_more,
            next_cursor=CursorReadSchema(
                last_id=result[-1].id,
                last_created_at=result[-1].created_at,
            ),
        )

    async def get_cars(self) -> list[ParkingReadSchema]:
        cars = await self.session.scalars(select(Car))
        return [self._schema.model_validate(car) for car in cars.all()]

    async def get_car_list_by_number(self, car_number: str) -> list[ParkingReadSchema]:
        car = await self.session.scalars(
            select(Car)
            .where(Car.number == car_number)
            .order_by(
                Car.created_at.desc(),
            )
        )

        return [self._schema.model_validate(car) for car in car.all()]

    async def park_car(self, park_car: CarParkSchema) -> ParkingReadSchema:
        db_park = Car(**park_car.model_dump(), status=CarStatus.parked)

        self.session.add(db_park)
        await self.session.flush()
        await self.session.refresh(db_park)

        return self._schema.model_validate(db_park)

    async def unpark_car(self, unpark_car: CarUnparkSchema) -> ParkingReadSchema:
        car = await self.check_car_status(car_number=unpark_car.number)

        if car is None:
            raise CarNotFoundException

        if car.status == CarStatus.unparked:
            raise CarIsNotParkedException

        car.status = CarStatus.unparked

        await self.session.flush()
        await self.session.refresh(car)

        return self._schema.model_validate(car)
