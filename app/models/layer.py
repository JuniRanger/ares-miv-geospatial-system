"""Persistence model for a validated data-layer record."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Layer(Base):
    """Metadata record for a data layer; no Mars SRID is assumed."""

    __tablename__ = "layers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
