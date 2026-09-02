def test_start_game_returns_session_and_fleet(client):
    response = client.post("/game")

    assert response.status_code == 201
    body = response.json()

    assert "session_id" in body
    assert "ships" in body

    total_decks = sum(len(ship["coordinates"]) for ship in body["ships"])
    assert total_decks == 20
    assert len(body["ships"]) == 10


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200