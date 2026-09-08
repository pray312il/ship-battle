from DB.database import SessionLocal
from DB.models.models import GameSession
from app.services.fleet import validate_fleet

def test_start_game(client):
    response = client.post("/game")

    assert response.status_code == 201
    body = response.json()

    assert "session_id" in body
    assert "ships" in body

    total_decks = sum(len(ship["coordinates"]) for ship in body["ships"])
    assert total_decks == 20
    assert len(body["ships"]) == 10

def test_db(client):
    response = client.post("/game")
    session_id = response.json()["session_id"]

    db = SessionLocal()
    try:
        stored = db.get(GameSession, session_id)
    finally:
        db.close()


    assert stored is not None
    assert stored.status == "active"
    assert stored.ships == response.json()["ships"]

def test_valid_placement(client):
    response = client.post("/game")
    ships = response.json()["ships"]

    valid, errors = validate_fleet(ships)
    assert valid, errors


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200