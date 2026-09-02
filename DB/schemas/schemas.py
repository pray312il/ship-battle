import uuid

from pydantic import BaseModel, ConfigDict


class ShipSchema(BaseModel):
    coordinates: list[str]


class StartGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[ShipSchema]
