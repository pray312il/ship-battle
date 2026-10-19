import uuid

from DB.database import SessionLocal
from DB.models.models import GameSession

SIMPLE_SHIPS = [{"coordinates": ["A1", "A2"]}, {"coordinates": ["C3"]}]


def _create_session(ships=None, status="active"):
    db = SessionLocal()
    session = GameSession(ships=ships or SIMPLE_SHIPS, status=status)
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.session_id
    db.close()
    return session_id


def test_close_game_returns_closed_status(client):
    session_id = _create_session()
    response = client.post(f"/game/{session_id}/close")
    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_close_game_persists_status_to_db(client):
    session_id = _create_session()
    client.post(f"/game/{session_id}/close")

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert stored.status == "closed"


def test_close_game_twice_returns_400(client):
    session_id = _create_session()
    assert client.post(f"/game/{session_id}/close").status_code == 200
    assert client.post(f"/game/{session_id}/close").status_code == 400


def test_close_unknown_session_returns_404(client):
    response = client.post(f"/game/{uuid.uuid4()}/close")
    assert response.status_code == 404


def test_close_one_session_does_not_affect_another(client):
    session_a = _create_session()
    session_b = _create_session()

    client.post(f"/game/{session_a}/close")

    db = SessionLocal()
    stored_b = db.get(GameSession, session_b)
    db.close()
    assert stored_b.status == "active"


def test_closed_session_rejects_shot(client):
    session_id = _create_session()
    client.post(f"/game/{session_id}/close")
    assert client.post(f"/game/{session_id}/shot").status_code == 410


def test_closed_session_rejects_opponent_shot(client):
    session_id = _create_session()
    client.post(f"/game/{session_id}/close")
    response = client.post(f"/game/{session_id}/opponent-shot", json={"coordinate": "A1"})
    assert response.status_code == 410