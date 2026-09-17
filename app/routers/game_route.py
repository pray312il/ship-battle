from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.fleet import generate_fleet, parse_coordinate
from DB.database import get_db
from DB.models.models import GameSession
from DB.schemas.schemas import StartGameResponse, OpponentShotRequest, OpponentShotResponse
import uuid

router = APIRouter()

@router.post("/game", response_model = StartGameResponse, status_code = 201)
def start_game(db: Session = Depends(get_db)):
    ships = generate_fleet()

    session = GameSession(ships = ships)
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartGameResponse(session_id = session.session_id, ships = ships)

@router.post("/game/{session_id}/opponent-shot", response_model=OpponentShotResponse)
def opponent_shot(
    session_id: uuid.UUID,
    payload: OpponentShotRequest,
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Сессия завершена")

    try: 
        parse_coordinate(payload.coordinate)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректная координата")

    coordinate = payload.coordinate
    target_ship = None

    for ship in session.ships:
        if coordinate in ship["coordinates"]:
            target_ship = ship
            break

    if target_ship is None:
        return OpponentShotResponse(result="miss")

    hits = set(session.hits)
    hits.add(coordinate)
    session.hits = list(hits)
    db.commit()

    if set(target_ship["coordinates"]).issubset(hits):
        return OpponentShotResponse(result="killed")
    return OpponentShotResponse(result="hit")
    
