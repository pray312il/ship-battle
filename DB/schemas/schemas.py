import uuid

from pydantic import BaseModel, ConfigDict


class ShipSchema(BaseModel):
    coordinates: list[str]


class StartGameResponse(BaseModel):
    session_id: uuid.UUID
    ships: list[ShipSchema]

class OpponentShotRequest(BaseModel):
    coordinate: str

class OpponentShotResponse(BaseModel):
    result: str

class ShotResponse(BaseModel):
    coordinate: str


class ShotResultRequest(BaseModel):
    result: str


class ShotResultResponse(BaseModel):
    status: str

class CloseGameResponse(BaseModel):
    status: str