from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.fleet import generate_fleet, parse_coordinate
from app.services.targeting import pick_next_shot, build_target_queue, surrounding_cells
from DB.database import get_db
from DB.models.models import GameSession
from DB.schemas.schemas import StartGameResponse, OpponentShotRequest, OpponentShotResponse, ShotResponse, ShotResultRequest, ShotResultResponse
import uuid

router = APIRouter()

VALID_RESULTS = {"miss", "hit", "killed"}

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
    
@router.post("/game/{session_id}/shot", response_model=ShotResponse)
def make_shot(session_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.get(GameSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Сессия завершена")
    if session.pending_shot is not None:
        raise HTTPException(status_code=409, detail="Ожидается результат предыдущего выстрела")

    coordinate = pick_next_shot(session.own_shots, session.current_hits, session.target_queue)

    session.pending_shot = coordinate
    db.commit()

    return ShotResponse(coordinate=coordinate)


@router.post("/game/{session_id}/shot/result", response_model=ShotResultResponse)
def accept_shot_result(
    session_id: uuid.UUID,
    payload: ShotResultRequest,
    db: Session = Depends(get_db),
):
    session = db.get(GameSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.status == "closed":
        raise HTTPException(status_code=410, detail="Сессия завершена")
    if payload.result not in VALID_RESULTS:
        raise HTTPException(status_code=400, detail="Недопустимое значение result")
    if session.pending_shot is None:
        raise HTTPException(status_code=409, detail="Нет выстрела, ожидающего результата")

    coordinate = session.pending_shot

    own_shots = dict(session.own_shots)
    own_shots[coordinate] = payload.result
    current_hits = list(session.current_hits)
    target_queue = list(session.target_queue)

    if payload.result == "hit":
        current_hits.append(coordinate)
        target_queue = build_target_queue(current_hits, set(own_shots.keys()))

    elif payload.result == "killed":
        sunk_ship_cells = current_hits + [coordinate]
        for cell in surrounding_cells(sunk_ship_cells):
            own_shots.setdefault(cell, "miss")

    current_hits = []
    target_queue = []

    session.own_shots = own_shots
    session.current_hits = current_hits
    session.target_queue = target_queue
    session.pending_shot = None
    db.commit()

    return ShotResultResponse(status="accepted")