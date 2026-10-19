import random

import pytest

from arena.services.match import play_match
from tests.fakes import (
    ALL_CELLS, GOOD_FLEET, FakeService, make_client, mirror,
    order_misses_first, order_perfect,
)

FLEET_A = GOOD_FLEET
FLEET_B = mirror(GOOD_FLEET)


def _pair(a_kwargs=None, b_kwargs=None, a_order=None, b_order=None, timeout=1.0):
    """A атакует флот B, B атакует флот A. По умолчанию — A «идеальный», B начинает с промаха."""
    a = FakeService(FLEET_A, a_order or order_perfect(FLEET_B), **(a_kwargs or {}))
    b = FakeService(FLEET_B, b_order or order_misses_first(FLEET_A), **(b_kwargs or {}))
    return a, b, make_client(a, "A", timeout), make_client(b, "B", timeout)


@pytest.mark.parametrize("first", [0, 1])
def test_perfect_shooter_wins_regardless_of_who_goes_first(first):
    a, b, ca, cb = _pair()
    result = play_match(ca, cb, first=first)
    assert result.winner == "A"
    assert result.reason == "fleet_sunk"
    assert result.violator is None
    assert result.shots["A"] == 20


def test_series_of_hits_keeps_the_turn():
    a, b, ca, cb = _pair()
    play_match(ca, cb, first=1)
    # B ходит первым и промахивается один раз -> дальше A подряд 20 раз без передачи хода
    assert b.calls["shot"] == 1
    assert a.calls["shot"] == 20
    assert a.received_results.count("killed") == 10  # ровно 10 кораблей
    assert a.received_results.count("hit") == 10      # 20 палуб - 10 финальных


def test_first_shooter_is_chosen_by_arena_and_reported():
    a, b, ca, cb = _pair()
    assert play_match(ca, cb, first=0).first == "A"
    a, b, ca, cb = _pair()
    assert play_match(ca, cb, first=1).first == "B"
    a, b, ca, cb = _pair()
    assert play_match(ca, cb, rng=random.Random(1)).first in {"A", "B"}


def test_both_sessions_are_closed_after_match():
    a, b, ca, cb = _pair()
    play_match(ca, cb, first=0)
    assert a.closed and b.closed


def test_arena_sends_true_results_to_shooter_not_claims():
    a, b, ca, cb = _pair()
    play_match(ca, cb, first=1)  # B ходит первым и промахивается, дальше 20 попаданий A
    assert set(a.received_results) <= {"hit", "killed"}
    assert b.received_results == ["miss"]


@pytest.mark.parametrize("lie", ["miss", "hit", "killed"])
def test_liar_loses_the_match(lie):
    a, b, ca, cb = _pair(b_kwargs={"always_answer": lie})
    result = play_match(ca, cb, first=0)
    assert result.winner == "A"
    assert result.violator == "B"
    assert result.reason == "violation"
    assert "lie" in result.detail


def test_liar_is_caught_even_when_lie_is_about_a_miss():
    # B врёт «killed» на промах A -> ловим на самой первой реплике
    a, b, ca, cb = _pair(a_order=["J10"] + order_perfect(FLEET_B), b_kwargs={"always_answer": "killed"})
    result = play_match(ca, cb, first=0)
    assert result.violator == "B"
    assert a.calls["shot"] == 1


def test_invalid_fleet_loses_before_first_shot():
    bad_fleet = [list(s) for s in FLEET_B]
    bad_fleet[6] = ["B5"]  # касание углом
    a = FakeService(FLEET_A, order_perfect(FLEET_B))
    b = FakeService(bad_fleet, order_perfect(FLEET_A))
    result = play_match(make_client(a, "A"), make_client(b, "B"), first=1)
    assert result.winner == "A"
    assert result.violator == "B"
    assert "invalid_fleet" in result.detail
    assert result.shots == {"A": 0, "B": 0}
    assert a.closed and b.closed


def test_both_invalid_is_a_draw():
    bad = [list(s) for s in FLEET_A]
    bad[6] = ["B5"]
    a = FakeService(bad, ["A1"])
    b = FakeService(bad, ["A1"])
    result = play_match(make_client(a, "A"), make_client(b, "B"))
    assert result.winner is None
    assert result.reason == "both_violated"


@pytest.mark.parametrize("handle,mode,kind", [
    ("shot", "timeout", "timeout"),
    ("shot", "connect", "connection"),
    ("shot", "500", "bad_status"),
    ("shot", "badjson", "bad_body"),
    ("start", "connect", "connection"),
])
def test_attacker_faults_lose_the_match(handle, mode, kind):
    a, b, ca, cb = _pair(a_kwargs={"faults": {handle: mode}})
    result = play_match(ca, cb, first=0)
    assert result.winner == "B"
    assert result.violator == "A"
    assert kind in result.detail


@pytest.mark.parametrize("handle,mode,kind", [
    ("opponent_shot", "timeout", "timeout"),
    ("opponent_shot", "500", "bad_status"),
    ("opponent_shot", "badjson", "bad_body"),
])
def test_defender_faults_lose_the_match(handle, mode, kind):
    a, b, ca, cb = _pair(b_kwargs={"faults": {handle: mode}})
    result = play_match(ca, cb, first=0)
    assert result.winner == "A"
    assert result.violator == "B"
    assert kind in result.detail


def test_shot_result_fault_loses_the_match_for_the_shooter():
    a, b, ca, cb = _pair(a_kwargs={"faults": {"shot_result": "500"}})
    result = play_match(ca, cb, first=0)
    assert result.winner == "B"
    assert result.violator == "A"


def test_slow_answer_is_a_violation_even_if_it_is_correct():
    a, b, ca, cb = _pair(b_kwargs={"faults": {"opponent_shot": "slow"}, "slow_sleep": 0.1}, timeout=0.05)
    result = play_match(ca, cb, first=0)
    assert result.winner == "A"
    assert result.violator == "B"
    assert "too_slow" in result.detail


def test_fault_in_the_middle_of_the_game():
    a, b, ca, cb = _pair(b_kwargs={"faults": {"opponent_shot": ("timeout", 5)}})
    result = play_match(ca, cb, first=0)
    assert result.violator == "B"
    assert a.calls["shot"] == 5  # 4 нормальных ответа и 5-й без ответа


def test_invalid_coordinate_loses():
    a, b, ca, cb = _pair(a_order=["Z99"])
    result = play_match(ca, cb, first=0)
    assert result.winner == "B"
    assert "invalid_coordinate" in result.detail


def test_repeated_shot_is_not_an_error_but_passes_the_turn():
    # A попадает по B, затем стреляет в ту же клетку -> ход переходит к B, B топит A
    a, b, ca, cb = _pair(
        a_order=[FLEET_B[0][0], FLEET_B[0][0]],
        b_order=order_perfect(FLEET_A),
    )
    result = play_match(ca, cb, first=0)
    assert result.repeats["A"] == 1
    assert result.violator is None
    assert result.winner == "B"
    assert a.received_results[:2] == ["hit", "miss"]  # повтор арена записала как miss
    assert b.calls["opponent_shot"] == 1              # по повтору соперника не дёргали


def test_move_limit_ends_endless_match_as_draw():
    a = FakeService(FLEET_A, ["J10"])
    b = FakeService(FLEET_B, ["J10"])
    result = play_match(make_client(a, "A"), make_client(b, "B"), first=0, max_shot_calls=20)
    assert result.winner is None
    assert result.reason == "move_limit"
    assert a.closed and b.closed


def test_close_failure_is_a_warning_and_does_not_change_the_winner():
    a, b, ca, cb = _pair(b_kwargs={"faults": {"close": "500"}})
    result = play_match(ca, cb, first=0)
    assert result.winner == "A"
    assert any("B" in w for w in result.warnings)
    assert a.closed


def test_client_can_be_reused_for_next_match():
    a, b, ca, cb = _pair()
    play_match(ca, cb, first=0)
    a2 = FakeService(FLEET_A, order_perfect(FLEET_B))
    b2 = FakeService(FLEET_B, order_misses_first(FLEET_A))
    ca.session_id = "stale-id"
    ca._http = make_client(a2, "A")._http
    cb._http = make_client(b2, "B")._http
    result = play_match(ca, cb, first=0)
    assert result.winner == "A"
    assert ca.session_id == a2.session_id
