from types import TracebackType
from typing import Self

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.v1.cars.repository import CarRepository


class UnitOfWork:
    """Единица работы: управляет жизненным циклом сессии и репозиториев."""

    _session: AsyncSession
    cars: CarRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self.session_factory()

        self.cars = CarRepository(self._session)

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()


class ReadOnlyUnitOfWork:
    """UoW для чтения с реплики: без коммитов, транзакция READ ONLY."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> Self:
        self._session = self.session_factory()
        # защита от случайной записи на реплике:
        await self._session.execute(text("SET TRANSACTION READ ONLY"))
        self.cars = CarRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._session.close()
