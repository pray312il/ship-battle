from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.services.fleet import generate_fleet
from DB.database import get_db
from DB.models.models import GameSession
from DB.schemas.schemas import StartGameResponse

router = APIRouter()

@router.post("/game", response_model = StartGameResponse, status_code = 201)
def start_game(db: Session = Depends(get_db)):
    ships = generate_fleet()

    session = GameSession(ships = ships)
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartGameResponse(session_id = session.session_id, ships = ships)