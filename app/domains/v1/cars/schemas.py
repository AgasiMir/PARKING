from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CarReadSchema(BaseModel):
    id: UUID
    mark: str = Field(min_length=2, max_length=50)
    model: str = Field(min_length=2, max_length=50)
    number: str = Field(min_length=6, max_length=8)
    color: str = Field(min_length=2, max_length=50)
    status: str = Field(description="Статус парковки")
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
