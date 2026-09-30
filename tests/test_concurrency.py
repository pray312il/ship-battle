import asyncio
import time
import uuid as uuid_module

import httpx
import pytest

from app.main import app
from DB.database import SessionLocal
from DB.models.models import GameSession


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_sessions_do_not_mix_state(client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        start_responses = await asyncio.gather(*[async_client.post("/game") for _ in range(8)])
        session_ids = [r.json()["session_id"] for r in start_responses]
        assert len(set(session_ids)) == 8 

        shot_responses = await asyncio.gather(
            *[async_client.post(f"/game/{sid}/shot") for sid in session_ids]
        )
        coordinates = {sid: r.json()["coordinate"] for sid, r in zip(session_ids, shot_responses)}

        results = ["miss", "hit", "miss", "hit", "miss", "hit", "miss", "hit"]
        await asyncio.gather(
            *[
                async_client.post(f"/game/{sid}/shot/result", json={"result": result})
                for sid, result in zip(session_ids, results)
            ]
        )

    db = SessionLocal()
    try:
        for sid, expected_result in zip(session_ids, results):
            stored = db.get(GameSession, uuid_module.UUID(sid))
            coordinate = coordinates[sid]
            assert stored.own_shots == {coordinate: expected_result}
    finally:
        db.close()


@pytest.mark.anyio
async def test_concurrent_requests_stay_within_sla(client):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as async_client:
        session_ids = []
        for _ in range(20):
            response = await async_client.post("/game")
            session_ids.append(response.json()["session_id"])

        start = time.perf_counter()
        responses = await asyncio.gather(
            *[async_client.post(f"/game/{sid}/shot") for sid in session_ids]
        )
        elapsed = time.perf_counter() - start

    assert all(r.status_code == 200 for r in responses)
    assert elapsed < 1.0, f"20 параллельных /shot заняли {elapsed:.2f}s"