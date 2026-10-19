import random
from dataclasses import dataclass, field
from typing import Callable

from arena.services.client import ServiceClient, Violation, check_coordinate
from arena.services.rules import Field, validate_fleet

MAX_SHOT_CALLS = 1000  # защита от бесконечной партии (законная партия — не больше ~200)


@dataclass
class MatchResult:
    names: tuple[str, str]
    first: str | None = None
    winner: str | None = None
    violator: str | None = None
    reason: str = ""  # fleet_sunk | violation | both_violated | move_limit | arena_error
    detail: str = ""
    shots: dict[str, int] = field(default_factory=dict)
    repeats: dict[str, int] = field(default_factory=dict)
    fleets: dict[str, list[list[str]]] = field(default_factory=dict)
    history: dict[str, dict[str, str]] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def play_match(
    a: ServiceClient,
    b: ServiceClient,
    rng: random.Random | None = None,
    first: int | None = None,
    emit: Callable[[str], None] | None = None,
    max_shot_calls: int = MAX_SHOT_CALLS,
) -> MatchResult:
    rng = rng or random.Random()
    players = [a, b]
    result = MatchResult(
        names=(a.name, b.name),
        shots={a.name: 0, b.name: 0},
        repeats={a.name: 0, b.name: 0},
        history={a.name: {}, b.name: {}},
    )

    def note(message: str) -> None:
        result.log.append(message)
        if emit:
            emit(message)

    for p in players:
        p.session_id = None

    # ---------- 1. старт сессий и проверка расстановок ----------
    start_violations: dict[str, Violation] = {}
    for p in players:
        try:
            ships = p.start_game()
            result.fleets[p.name] = ships
            errors = validate_fleet(ships)
            if errors:
                raise Violation("invalid_fleet", "; ".join(errors[:3]))
            note(f"{p.name}: сессия {p.session_id}, расстановка корректна")
        except Violation as exc:
            start_violations[p.name] = exc
            note(f"{p.name}: НАРУШЕНИЕ при старте — {exc}")

    if start_violations:
        _finish_with_violations(result, players, start_violations)
        _close_sessions(players, result, note)
        return result

    # ---------- 2. очерёдность определяет арена ----------
    first_index = rng.randrange(2) if first is None else first
    result.first = players[first_index].name
    note(f"Первым ходит {result.first}")

    fields = {p.name: Field(result.fleets[p.name]) for p in players}
    turn = first_index
    shot_calls = 0
    violator: ServiceClient | None = None
    violation: Violation | None = None

    # ---------- 3. игровой цикл ----------
    while shot_calls < max_shot_calls:
        shooter, defender = players[turn], players[1 - turn]
        shot_calls += 1

        try:
            coordinate = shooter.shot()
            check_coordinate(coordinate)
            result.shots[shooter.name] += 1

            if coordinate in result.history[shooter.name]:
                # Повторный выстрел — не ошибка, но арена считает это
                # нежеланием победить: ход переходит сопернику.
                result.repeats[shooter.name] += 1
                note(f"{shooter.name} → {coordinate}: повторный выстрел, ход переходит к {defender.name}")
                shooter.shot_result("miss")
                turn = 1 - turn
                continue
        except Violation as exc:
            violator, violation = shooter, exc
            break

        try:
            truth = fields[defender.name].shoot(coordinate)
            claimed = defender.opponent_shot(coordinate)
            if claimed != truth:
                raise Violation(
                    "lie",
                    f"на {coordinate} ответил {claimed!r}, а по его расстановке — {truth!r}",
                )
        except Violation as exc:
            violator, violation = defender, exc
            break

        result.history[shooter.name][coordinate] = truth
        try:
            shooter.shot_result(truth)
        except Violation as exc:
            violator, violation = shooter, exc
            break

        note(f"#{shot_calls} {shooter.name} → {coordinate}: {truth}")

        if fields[defender.name].all_sunk():
            result.winner = shooter.name
            result.reason = "fleet_sunk"
            result.detail = f"флот {defender.name} потоплен"
            break
        if truth == "miss":
            turn = 1 - turn
    else:
        result.reason = "move_limit"
        result.detail = f"партия не закончилась за {max_shot_calls} ходов"

    if violator is not None:
        _finish_with_violations(result, players, {violator.name: violation})
        note(f"{violator.name}: НАРУШЕНИЕ — {violation}")

    # ---------- 4. закрытие сессий у обоих ----------
    _close_sessions(players, result, note)
    return result


def _finish_with_violations(result: MatchResult, players, violations: dict[str, Violation]) -> None:
    if len(violations) == 2:
        result.reason = "both_violated"
        result.detail = "; ".join(f"{name}: {v}" for name, v in violations.items())
        return
    (name, violation), = violations.items()
    other = next(p.name for p in players if p.name != name)
    result.reason = "violation"
    result.violator = name
    result.winner = other
    result.detail = f"{name}: {violation}"


def _close_sessions(players, result: MatchResult, note) -> None:
    for p in players:
        if p.session_id is None:
            continue
        try:
            p.close()
            note(f"{p.name}: сессия закрыта")
        except Violation as exc:
            # на победителя это не влияет, но в отчёте должно быть видно
            result.warnings.append(f"{p.name}: сессию закрыть не удалось — {exc}")
            note(f"{p.name}: сессию закрыть не удалось — {exc}")
