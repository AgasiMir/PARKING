from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.car import CarStatus


class ParkingReadSchema(BaseModel):
    id: UUID
    mark: str = Field(min_length=2, max_length=50)
    model: str = Field(min_length=2, max_length=50)
    number: str = Field(min_length=6, max_length=8)
    color: str = Field(min_length=2, max_length=50)
    status: CarStatus = Field(description="Статус парковки")
    created_at: datetime = Field(description="Дата и время захода в парковку")
    updated_at: datetime = Field(description="Дата и время выхода из парковки")

    model_config = ConfigDict(from_attributes=True)


class CarParkSchema(BaseModel):
    mark: str = Field(min_length=2, max_length=50)
    model: str = Field(min_length=2, max_length=50)
    number: str = Field(min_length=6, max_length=8)
    color: str = Field(min_length=2, max_length=50)


class CarUnparkSchema(BaseModel):
    number: str = Field(min_length=6, max_length=8)


class CarParkTimePriceSchema(BaseModel):
    park_time: float
    price: float


class CarParkingAndPriceSchema(BaseModel):
    parking_data: ParkingReadSchema
    price_time_data: CarParkTimePriceSchema


class CursorReadSchema(BaseModel):
    """
    Схема для передачи курсора при курсорной пагинации.

    Используется для указания позиции в списке парковок
    (последняя полученная парковка), чтобы запросить следующую порцию.

    Attributes:
        last_id: UUID последней парковки в текущей порции.
        last_created_at: Дата создания последней парковки.
    """

    last_id: UUID
    last_created_at: datetime


class ParkingReadSchemaWithCursor(BaseModel):
    """
    Схема ответа API для курсорной пагинации списка парковок.

    Содержит список парковок за текущую страницу, флаг,
    указывающий наличие дополнительных записей, и объект курсора
    для запроса следующей порции.

    Attributes:
        cars: Список парковок в формате ParkingReadSchema|CarParkingAndPriceSchema.
        has_more: True, если в списке есть ещё записи после текущей страницы.
        next_cursor: Курсор для получения следующей порции парковок.
            Содержит UUID и дату создания последней парковки в текущей порции.
            Равно None, если дополнительных записей нет (has_more=False).
    """

    cars: list[ParkingReadSchema]
    has_more: bool
    next_cursor: CursorReadSchema | None = None


class ParkingPriceTimeCursorSchema(BaseModel):
    parking_and_price_data: list[CarParkingAndPriceSchema]
    has_more: bool
    next_cursor: CursorReadSchema | None = None


class CursorPaginationSchema(BaseModel):
    """
    Схема пагинации с использованием курсора.

    Используется для запросов постраничной навигации, где каждая страница
    определяется позицией (курсором) в упорядоченном списке парковок.
    Курсор состоит из UUID последней полученной парковки и даты ее создания,
    что обеспечивает стабильную навигацию даже при изменениях в данных.

    Attributes:
        limit: Количество парковок на странице. По умолчанию — 5,
            допустимый диапазон: от 1 до 50.
        cursor_id: UUID парковки, с которого начинается следующая порция.
            Не обязателен для первого запроса.
            Должен указываться вместе с created_at.
        created_at: Дата создания парковки-курсора.
            Не обязателен для первого запроса.
            Должен указываться вместе с cursor_id.
    """

    limit: int = Field(default=5, ge=1, le=50, description="Количество парковок на странице")
    cursor_id: UUID | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def validate_cursor(self):
        if self.cursor_id is None and self.created_at is not None:
            raise ValueError("cursor_id должен быть передан, если передан created_at")
        if self.cursor_id is not None and self.created_at is None:
            raise ValueError("created_at должен быть передан, если передан cursor_id")

        return self
