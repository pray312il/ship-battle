import time
import uuid

import httpx

from arena.services.rules import parse_coordinate

RESULTS = {"miss", "hit", "killed"}


class Violation(Exception):

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


class ServiceClient:
    def __init__(self, name: str, base_url: str, timeout: float = 1.0, transport=None):
        self.name = name
        self.base_url = base_url
        self.timeout = timeout
        self.session_id: str | None = None
        self._http = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(timeout),
            transport=transport,
        )

    def close_http(self) -> None:
        self._http.close()

    # ---------- общий вызов с контролем контракта ----------

    def _call(self, path: str, expected_status: int, json: dict | None = None) -> dict:
        started = time.perf_counter()
        try:
            response = self._http.post(path, json=json)
        except httpx.TimeoutException:
            raise Violation("timeout", f"{path}: нет ответа за {self.timeout} с")
        except httpx.HTTPError as exc:
            raise Violation("connection", f"{path}: {type(exc).__name__}: {exc}")
        elapsed = time.perf_counter() - started
        if elapsed > self.timeout:
            raise Violation("too_slow", f"{path}: ответ за {elapsed:.3f} с при лимите {self.timeout} с")

        if response.status_code != expected_status:
            raise Violation("bad_status", f"{path}: ожидали {expected_status}, пришло {response.status_code}")

        try:
            body = response.json()
        except ValueError:
            raise Violation("bad_body", f"{path}: ответ — не JSON")
        if not isinstance(body, dict):
            raise Violation("bad_body", f"{path}: ожидали JSON-объект, пришло {type(body).__name__}")
        return body

    # ---------- пять ручек контракта ----------

    def start_game(self) -> list[list[str]]:
        body = self._call("/game", 201)

        session_id = body.get("session_id")
        try:
            uuid.UUID(str(session_id))
        except ValueError:
            raise Violation("bad_body", f"/game: session_id не UUID: {session_id!r}")
        self.session_id = str(session_id)

        ships = body.get("ships")
        if not isinstance(ships, list):
            raise Violation("bad_body", "/game: ships должен быть списком")
        result = []
        for ship in ships:
            coords = ship.get("coordinates") if isinstance(ship, dict) else None
            if not isinstance(coords, list) or not all(isinstance(c, str) for c in coords):
                raise Violation("bad_body", f"/game: некорректный корабль {ship!r}")
            result.append(coords)
        return result

    def shot(self) -> str:
        """Ручка 2. Возвращает координату выстрела (формат проверяется отдельно, в матче)."""
        body = self._call(f"/game/{self.session_id}/shot", 200)
        coordinate = body.get("coordinate")
        if not isinstance(coordinate, str):
            raise Violation("bad_body", f"/shot: coordinate должен быть строкой, пришло {coordinate!r}")
        return coordinate

    def opponent_shot(self, coordinate: str) -> str:
        """Ручка 4. Возвращает то, что сервис ЗАЯВИЛ про свой флот."""
        body = self._call(f"/game/{self.session_id}/opponent-shot", 200, json={"coordinate": coordinate})
        result = body.get("result")
        if result not in RESULTS:
            raise Violation("bad_body", f"/opponent-shot: недопустимый result {result!r}")
        return result

    def shot_result(self, result: str) -> None:
        """Ручка 3. Сообщает стрелявшему истинный результат его выстрела."""
        body = self._call(f"/game/{self.session_id}/shot/result", 200, json={"result": result})
        if body.get("status") != "accepted":
            raise Violation("bad_body", f"/shot/result: ожидали status=accepted, пришло {body!r}")

    def close(self) -> None:
        """Ручка 5."""
        body = self._call(f"/game/{self.session_id}/close", 200)
        if body.get("status") != "closed":
            raise Violation("bad_body", f"/close: ожидали status=closed, пришло {body!r}")


def check_coordinate(coord: str) -> None:
    """Выстрел обязан быть валидной координатой A1–J10, иначе — нарушение."""
    try:
        parse_coordinate(coord)
    except ValueError as exc:
        raise Violation("invalid_coordinate", str(exc))
