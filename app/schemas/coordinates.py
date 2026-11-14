"""Mars coordinate API schema."""

from pydantic import BaseModel


class Coordinates(BaseModel):
    """Named latitude and longitude fields; no planetary convention is assumed."""

    latitude: float
    longitude: float
