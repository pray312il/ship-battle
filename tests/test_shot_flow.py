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


def test_shot_returns_coordinate_and_sets_pending(client):
    session_id = _create_session()
    response = client.post(f"/game/{session_id}/shot")
    assert response.status_code == 200
    coordinate = response.json()["coordinate"]

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert stored.pending_shot == coordinate


def test_shot_conflict_when_pending_result_not_confirmed(client):
    session_id = _create_session()
    client.post(f"/game/{session_id}/shot")
    response = client.post(f"/game/{session_id}/shot")
    assert response.status_code == 409


def test_shot_result_accepts_and_clears_pending(client):
    session_id = _create_session()
    shot = client.post(f"/game/{session_id}/shot").json()

    response = client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert stored.pending_shot is None
    assert stored.own_shots[shot["coordinate"]] == "miss"


def test_shot_result_conflict_without_pending_shot(client):
    session_id = _create_session()
    response = client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})
    assert response.status_code == 409


def test_shot_result_rejects_invalid_result_value(client):
    session_id = _create_session()
    client.post(f"/game/{session_id}/shot")
    response = client.post(f"/game/{session_id}/shot/result", json={"result": "не попал"})
    assert response.status_code == 400


def test_shot_never_repeats_already_shot_cells_across_many_rounds(client):
    session_id = _create_session()
    seen = set()
    for _ in range(30):
        coordinate = client.post(f"/game/{session_id}/shot").json()["coordinate"]
        assert coordinate not in seen
        seen.add(coordinate)
        client.post(f"/game/{session_id}/shot/result", json={"result": "miss"})


def test_shot_after_hit_targets_orthogonal_neighbor(client):
    session_id = _create_session()

    db = SessionLocal()
    session = db.get(GameSession, session_id)
    session.pending_shot = "E5"
    db.commit()
    db.close()

    client.post(f"/game/{session_id}/shot/result", json={"result": "hit"})
    next_shot = client.post(f"/game/{session_id}/shot").json()["coordinate"]
    assert next_shot in {"F5", "D5", "E6", "E4"}


def test_shot_after_killed_resets_targeting_state(client):
    session_id = _create_session()

    db = SessionLocal()
    session = db.get(GameSession, session_id)
    session.pending_shot = "C3"
    db.commit()
    db.close()

    client.post(f"/game/{session_id}/shot/result", json={"result": "killed"})

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert stored.current_hits == []
    assert stored.target_queue == []


def test_shot_unknown_session_returns_404(client):
    response = client.post(f"/game/{uuid.uuid4()}/shot")
    assert response.status_code == 404


def test_shot_closed_session_returns_410(client):
    session_id = _create_session(status="closed")
    response = client.post(f"/game/{session_id}/shot")
    assert response.status_code == 410