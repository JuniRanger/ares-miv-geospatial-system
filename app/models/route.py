"""Persistence model for a calculated route."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Route(Base):
    """Route record placeholder without unverified geometry or spatial metadata."""

    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
