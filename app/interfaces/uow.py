# app/interfaces/uow.py
from abc import ABC, abstractmethod
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domains.v1.cars.repository import CarRepository  # только для типов


class UnitOfWorkInterface(ABC):
    """
    Интерфейс (абстрактный базовый класс) для UnitOfWork-подобных объектов.
    Определяет минимальный контракт: контекстный менеджер async и репозитории.
    """

    cars: "CarRepository"

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWorkInterface": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
