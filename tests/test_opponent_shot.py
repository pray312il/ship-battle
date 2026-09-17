import uuid
from DB.database import SessionLocal
from DB.models.models import GameSession

SIMPLE_SHIPS = [
    {"coordinates": ["A1", "A2"]},
    {"coordinates": ["C3"]},
]

def _create_session(ships,status="active"):
    db = SessionLocal()
    session = GameSession(ships=ships, status=status)
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.session_id
    db.close()
    return session_id

def test_opponent_miss(client):
    session_id = _create_session(SIMPLE_SHIPS)
    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinates": "J10"})
    assert response.status_code == 200
    assert response.json()["result"] == "miss"

def test_opponent_killed(client):
    session_id = _create_session(SIMPLE_SHIPS)

    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"})
    assert response.json()["result"] == "hit"

    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A2"})
    assert response.json()["result"] == "killed"


def test_opponent_single_ship_is_killed(client):
    session_id = _create_session(SIMPLE_SHIPS)
    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "C3"})
    assert response.json()["result"] == "killed"


def test_opponent_persists_hits_to_db(client):
    session_id = _create_session(SIMPLE_SHIPS)
    client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"})

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert "A1" in stored.hits


def test_opponent_unknown_session(client):
    response = client.post(f"/game/{uuid.uuid4()}/opponent-shot", json={"coordinate": "A1"})
    assert response.status_code == 404


def test_opponent_closed_session(client):
    session_id = _create_session(SIMPLE_SHIPS, status="closed")
    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"})
    assert response.status_code == 410


def test_opponent_invalid_coordinate(client):
    session_id = _create_session(SIMPLE_SHIPS)
    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "Z99"})
    assert response.status_code == 400