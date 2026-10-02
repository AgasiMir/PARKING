import uuid
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class CarStatus(Enum):
    parked = "parked"
    unparked = "unparked"


class Car(TimestampMixin, Base):
    __tablename__ = "cars"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    mark: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    number: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(50), nullable=True)

    status: Mapped[CarStatus] = mapped_column(SAEnum(CarStatus))
