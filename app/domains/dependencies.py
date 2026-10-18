from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.database import async_replica_session, async_session
from app.domains.v1.cars.schemas import CursorPaginationSchema
from app.domains.v1.cars.service import CarService
from app.rate_limiter import RateLimiter
from app.redis_connector import get_redis
from app.uow import ReadOnlyUnitOfWork, UnitOfWork


async def get_db():
    async with UnitOfWork(session_factory=async_session) as session:
        yield session


DBDep = Annotated[UnitOfWork, Depends(get_db)]


async def get_car_service(uow: DBDep):
    return CarService(uow=uow)


CarServiceDep = Annotated[CarService, Depends(get_car_service)]


async def get_read_db():
    async with ReadOnlyUnitOfWork(session_factory=async_replica_session) as session:
        yield session


ReadDBDep = Annotated[ReadOnlyUnitOfWork, Depends(get_read_db)]


async def get_car_read_service(uow: ReadDBDep):
    return CarService(uow=uow)


CarServiceReadOnlyDep = Annotated[CarService, Depends(get_car_read_service)]


async def get_cursor_pagination(
    limit: int = Query(default=5, ge=1, le=50, description="Количество парковок на странице"),
    cursor_id: UUID | None = Query(default=None),  # noqa: B008
    created_at: datetime | None = Query(default=None),  # noqa: B008
) -> CursorPaginationSchema:
    try:
        return CursorPaginationSchema(limit=limit, cursor_id=cursor_id, created_at=created_at)
    except ValidationError as e:
        raise RequestValidationError(errors=e.errors()) from e


CursorPaginationDep = Annotated[CursorPaginationSchema, Depends(get_cursor_pagination)]


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis())


RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]


def rate_limiter_factory(
    endpoint: str,
    max_requests: int,
    window_seconds: int,
):
    async def dependency(
        request: Request,
        rate_limiter: RateLimiterDep,
    ):
        if request.client is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось определить IP клиента",
            )

        ip_address = request.client.host

        limited = await rate_limiter.is_limited(
            ip_address,
            endpoint,
            max_requests,
            window_seconds,
        )

        if limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Превышено количество запросов. Повторите позже",
            )

    return dependency


rate_limit_get_parking_data = rate_limiter_factory("parking_list", 5, 5)
rate_limit_park_car = rate_limiter_factory("park_car", 3, 10)
rate_limit_unpark_car = rate_limiter_factory("unpark_car", 3, 10)
