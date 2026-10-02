from typing import Annotated

from fastapi import Depends

from app.core.database import async_session
from app.domains.v1.cars.service import CarService
from app.uow import UnitOfWork


async def get_db():
    async with UnitOfWork(session_factory=async_session) as session:
        yield session


DBDep = Annotated[UnitOfWork, Depends(get_db)]


async def get_car_service(uow: DBDep):
    return CarService(uow=uow)


CarServiceDep = Annotated[CarService, Depends(get_car_service)]
