"""Фейковые сервисы для тестов арены: честные, лживые, медленные, падающие."""
import json
import time
import uuid

import httpx

from arena.services.client import ServiceClient
from arena.services.rules import COLUMNS, Field

# заведомо корректная расстановка (проверена валидатором)
GOOD_FLEET = [
    ["A1", "A2", "A3", "A4"],
    ["C1", "C2", "C3"],
    ["E1", "E2", "E3"],
    ["A6", "A7"],
    ["C6", "C7"],
    ["E6", "E7"],
    ["J1"], ["J3"], ["J5"], ["J7"],
]

_MIRROR = str.maketrans(COLUMNS, COLUMNS[::-1])


def mirror(fleet):
    """Зеркало по горизонтали: тоже корректная расстановка, но другие клетки."""
    return [[c.translate(_MIRROR) for c in ship] for ship in fleet]


ALL_CELLS = [f"{col}{row}" for col in COLUMNS for row in range(1, 11)]


def order_perfect(opponent_fleet):
    """Стрелок, который знает чужой флот: сначала только корабли (20 попаданий подряд)."""
    ships = [c for ship in opponent_fleet for c in ship]
    return ships + [c for c in ALL_CELLS if c not in ships]


def order_misses_first(opponent_fleet, misses=1):
    """Стрелок, который начинает с промахов, а потом знает корабли."""
    ships = {c for ship in opponent_fleet for c in ship}
    empty = [c for c in ALL_CELLS if c not in ships]
    return empty[:misses] + [c for ship in opponent_fleet for c in ship] + empty[misses:]


class FakeService:
    """
    faults: {"shot": "timeout"} или {"shot": ("timeout", 3)} — со 2-го вызова и далее и т.п.
    Режимы: timeout | connect | 500 | badjson | slow
    """

    def __init__(self, fleet, shot_order, always_answer=None, faults=None, slow_sleep=0.1):
        self.fleet = fleet
        self.shot_order = list(shot_order)
        self.always_answer = always_answer
        self.faults = faults or {}
        self.slow_sleep = slow_sleep

        self.session_id = str(uuid.uuid4())
        self.field = Field(fleet)
        self.calls = {"start": 0, "shot": 0, "opponent_shot": 0, "shot_result": 0, "close": 0}
        self.received_results: list[str] = []
        self.closed = False
        self._shot_index = 0

    # ---------- маршрутизация ----------
    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/game":
            handle = "start"
        elif path.endswith("/shot/result"):
            handle = "shot_result"
        elif path.endswith("/opponent-shot"):
            handle = "opponent_shot"
        elif path.endswith("/shot"):
            handle = "shot"
        elif path.endswith("/close"):
            handle = "close"
        else:
            return httpx.Response(404, json={"detail": "нет такой ручки"})

        self.calls[handle] += 1
        fault = self.faults.get(handle)
        if fault:
            mode, from_call = (fault, 1) if isinstance(fault, str) else fault
            if self.calls[handle] >= from_call:
                if mode == "timeout":
                    raise httpx.ReadTimeout("fake timeout", request=request)
                if mode == "connect":
                    raise httpx.ConnectError("fake connection refused", request=request)
                if mode == "500":
                    return httpx.Response(500, json={"detail": "boom"})
                if mode == "badjson":
                    return httpx.Response(200, content=b"<html>not json</html>")
                if mode == "slow":
                    time.sleep(self.slow_sleep)

        body = json.loads(request.content) if request.content else {}
        return getattr(self, f"_{handle}")(body)

    # ---------- честное поведение ----------
    def _start(self, body):
        # как настоящий сервис: каждый POST /game — это НОВАЯ сессия с чистым состоянием
        self.session_id = str(uuid.uuid4())
        self.field = Field(self.fleet)
        self._shot_index = 0
        self.received_results = []
        self.closed = False
        return httpx.Response(201, json={
            "session_id": self.session_id,
            "ships": [{"coordinates": ship} for ship in self.fleet],
        })

    def _shot(self, body):
        index = min(self._shot_index, len(self.shot_order) - 1)
        self._shot_index += 1
        return httpx.Response(200, json={"coordinate": self.shot_order[index]})

    def _opponent_shot(self, body):
        truth = self.field.shoot(body["coordinate"])
        return httpx.Response(200, json={"result": self.always_answer or truth})

    def _shot_result(self, body):
        self.received_results.append(body["result"])
        return httpx.Response(200, json={"status": "accepted"})

    def _close(self, body):
        self.closed = True
        return httpx.Response(200, json={"status": "closed"})


def make_client(service: FakeService, name: str, timeout: float = 1.0) -> ServiceClient:
    return ServiceClient(name, "http://fake", timeout=timeout, transport=httpx.MockTransport(service.handler))
