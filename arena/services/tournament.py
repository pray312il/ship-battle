import itertools
import random
import sys
from dataclasses import dataclass
from typing import Callable

from arena.services.client import ServiceClient
from arena.services.match import MatchResult, play_match


@dataclass
class Standing:
    name: str
    wins: int = 0
    losses: int = 0
    draws: int = 0
    points: int = 0
    violations: int = 0


def run_tournament(
    clients: list[ServiceClient],
    games_per_pair: int = 2,
    rng: random.Random | None = None,
    win_points: int = 1,
    on_match: Callable[[MatchResult], None] | None = None,
    emit: Callable[[str], None] | None = None,
    ) -> tuple[list[Standing], list[MatchResult]]:
    rng = rng or random.Random()
    table = {c.name: Standing(c.name) for c in clients}
    results: list[MatchResult] = []

    for a, b in itertools.combinations(clients, 2):
        for game in range(games_per_pair):
            first = game % 2
            try:
                result = play_match(a, b, rng=rng, first=first, emit=emit)
            except Exception as exc:
                print(f"[arena] неожиданная ошибка арены в матче {a.name} vs {b.name}: {exc!r}", file=sys.stderr)
                result = MatchResult(names=(a.name, b.name), reason="arena_error", detail=repr(exc))

            results.append(result)
            _apply(table, result, win_points)
            if on_match:
                on_match(result)

    standings = sorted(table.values(), key=lambda s: (-s.points, -s.wins, s.violations, s.name))
    return standings, results


def _apply(table: dict[str, Standing], result: MatchResult, win_points: int) -> None:
    if result.winner is None:
        for name in result.names:
            table[name].draws += 1
    else:
        loser = next(n for n in result.names if n != result.winner)
        table[result.winner].wins += 1
        table[result.winner].points += win_points
        table[loser].losses += 1
    if result.violator is not None:
        table[result.violator].violations += 1
    if result.reason == "both_violated":
        for name in result.names:
            table[name].violations += 1
