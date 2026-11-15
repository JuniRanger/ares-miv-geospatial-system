"""Mars coordinate API schema."""

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    """Named latitude and longitude fields; no planetary convention is assumed."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
