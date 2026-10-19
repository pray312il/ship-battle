import asyncio

import httpx
import pytest

from app.main import app
from DB.database import SessionLocal
from DB.models.models import GameSession

N = 12


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _create_session(ships):
    db = SessionLocal()
    session = GameSession(ships=ships)
    db.add(session)
    db.commit()
    db.refresh(session)
    session_id = session.session_id
    db.close()
    return session_id


@pytest.mark.anyio
async def test_parallel_close_same_session_only_one_succeeds(client):
    session_id = _create_session([{"coordinates": ["A1"]}])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        responses = await asyncio.gather(*[ac.post(f"/game/{session_id}/close") for _ in range(N)])
    codes = sorted(r.status_code for r in responses)
    assert codes.count(200) == 1, codes
    assert codes.count(400) == N - 1, codes


@pytest.mark.anyio
async def test_parallel_shot_same_session_only_one_gets_coordinate(client):
    session_id = _create_session([{"coordinates": ["A1"]}])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        responses = await asyncio.gather(*[ac.post(f"/game/{session_id}/shot") for _ in range(N)])
    codes = sorted(r.status_code for r in responses)
    assert codes.count(200) == 1, codes
    assert codes.count(409) == N - 1, codes


@pytest.mark.anyio
async def test_parallel_opponent_shots_do_not_lose_hits(client):
    ship = ["A1", "A2", "A3", "A4"]
    session_id = _create_session([{"coordinates": ship}])
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        responses = await asyncio.gather(
            *[ac.post(f"/game/{session_id}/opponent-shot", json={"coordinate": c}) for c in ship]
        )
    results = sorted(r.json()["result"] for r in responses)
    assert results.count("killed") == 1, results

    db = SessionLocal()
    stored = db.get(GameSession, session_id)
    db.close()
    assert set(stored.hits) == set(ship), stored.hits