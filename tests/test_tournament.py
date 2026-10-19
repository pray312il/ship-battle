import random

from arena.__main__ import main, parse_service
from arena.services.match import play_match
from arena.services.render import format_match_line, format_standings, render_board, render_match
from arena.services.tournament import run_tournament
from tests.fakes import GOOD_FLEET, FakeService, make_client, order_misses_first, order_perfect


def _roster():
    """Все с одинаковой расстановкой, чтобы сила определялась только порядком выстрелов."""
    ace = FakeService(GOOD_FLEET, order_perfect(GOOD_FLEET))
    mid = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET, misses=3))
    liar = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET, misses=3), always_answer="miss")
    return ace, mid, liar


def test_round_robin_plays_every_pair_the_requested_number_of_times():
    ace, mid, liar = _roster()
    clients = [make_client(ace, "ace"), make_client(mid, "mid"), make_client(liar, "liar")]
    standings, results = run_tournament(clients, games_per_pair=2, rng=random.Random(0))

    assert len(results) == 6  # 3 пары x 2 партии
    pairs = sorted(tuple(sorted(r.names)) for r in results)
    assert pairs == sorted([("ace", "mid")] * 2 + [("ace", "liar")] * 2 + [("liar", "mid")] * 2)


def test_strongest_service_tops_the_table_and_liar_gets_violations():
    ace, mid, liar = _roster()
    clients = [make_client(ace, "ace"), make_client(mid, "mid"), make_client(liar, "liar")]
    standings, results = run_tournament(clients, games_per_pair=2, rng=random.Random(0))
    by_name = {s.name: s for s in standings}

    assert standings[0].name == "ace"
    assert by_name["ace"].wins == 4 and by_name["ace"].losses == 0
    assert by_name["ace"].points == 4
    assert by_name["liar"].violations >= 1
    assert by_name["mid"].violations == 0


def test_wins_and_losses_balance():
    ace, mid, liar = _roster()
    clients = [make_client(ace, "ace"), make_client(mid, "mid"), make_client(liar, "liar")]
    standings, results = run_tournament(clients, games_per_pair=2, rng=random.Random(0))
    decisive = [r for r in results if r.winner]
    assert sum(s.wins for s in standings) == len(decisive)
    assert sum(s.losses for s in standings) == len(decisive)
    assert sum(s.points for s in standings) == len(decisive)  # 1 очко за победу


def test_win_points_are_configurable():
    ace, mid, _ = _roster()
    clients = [make_client(ace, "ace"), make_client(mid, "mid")]
    standings, _ = run_tournament(clients, games_per_pair=2, win_points=3, rng=random.Random(0))
    assert standings[0].name == "ace" and standings[0].points == 6


def test_dead_service_does_not_stop_the_tournament():
    ace = FakeService(GOOD_FLEET, order_perfect(GOOD_FLEET))
    mid = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET, misses=3))
    dead = FakeService(GOOD_FLEET, ["A1"], faults={"start": "connect"})
    clients = [make_client(ace, "ace"), make_client(mid, "mid"), make_client(dead, "dead")]
    standings, results = run_tournament(clients, games_per_pair=2, rng=random.Random(0))

    by_name = {s.name: s for s in standings}
    assert len(results) == 6
    assert standings[-1].name == "dead"
    assert by_name["dead"].points == 0
    assert by_name["dead"].losses == 4
    assert by_name["dead"].violations == 4
    assert by_name["ace"].wins >= 2 and by_name["mid"].wins >= 2


def test_first_shooter_alternates_between_games_of_a_pair():
    ace = FakeService(GOOD_FLEET, order_perfect(GOOD_FLEET))
    mid = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET))
    _, results = run_tournament([make_client(ace, "ace"), make_client(mid, "mid")], games_per_pair=4)
    assert [r.first for r in results] == ["ace", "mid", "ace", "mid"]


def test_unexpected_arena_error_is_contained(monkeypatch):
    import arena.services.tournament as tournament

    def boom(*args, **kwargs):
        raise RuntimeError("баг в арене")

    monkeypatch.setattr(tournament, "play_match", boom)
    ace = FakeService(GOOD_FLEET, ["A1"])
    mid = FakeService(GOOD_FLEET, ["A1"])
    standings, results = tournament.run_tournament([make_client(ace, "ace"), make_client(mid, "mid")], games_per_pair=1)
    assert results[0].reason == "arena_error"
    assert all(s.draws == 1 for s in standings)


# ---------- визуализация ----------

def test_render_board_marks_ships_hits_and_misses():
    lines = render_board([["A1", "A2"], ["C3"]], {"A1": "hit", "J10": "miss"})
    assert lines[0].split() == list("ABCDEFGHIJ")
    row1 = lines[1].split()
    assert row1[0] == "1" and row1[1] == "X"          # A1 — подбитая палуба
    assert lines[2].split()[1] == "#"                  # A2 — целая палуба
    assert lines[10].split()[-1] == "o"                # J10 — промах


def test_render_match_shows_both_boards():
    ace = FakeService(GOOD_FLEET, order_perfect(GOOD_FLEET))
    mid = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET))
    result = play_match(make_client(ace, "ace"), make_client(mid, "mid"), first=0)
    text = render_match(result)
    assert "ace" in text and "mid" in text
    assert text.count("X") >= 20  # все 20 палуб проигравшего подбиты


def test_render_survives_garbage_fleet():
    bad = [["Z99", "A1"], ["A2"]]
    ace = FakeService(GOOD_FLEET, ["A1"])
    junk = FakeService(bad, ["A1"])
    result = play_match(make_client(ace, "ace"), make_client(junk, "junk"), first=0)
    assert isinstance(render_match(result), str)


def test_match_line_and_standings_text():
    ace = FakeService(GOOD_FLEET, order_perfect(GOOD_FLEET))
    mid = FakeService(GOOD_FLEET, order_misses_first(GOOD_FLEET))
    result = play_match(make_client(ace, "ace"), make_client(mid, "mid"), first=0)
    assert "победил ace" in format_match_line(result)
    standings, _ = run_tournament([make_client(ace, "ace"), make_client(mid, "mid")], games_per_pair=1)
    table = format_standings(standings)
    assert "ace" in table and "Очки" in table


# ---------- CLI ----------

def test_parse_service_variants():
    c = parse_service("alice=8001", 1.0)
    assert (c.name, c.base_url) == ("alice", "http://127.0.0.1:8001")
    c = parse_service("8002", 1.0)
    assert (c.name, c.base_url) == ("port-8002", "http://127.0.0.1:8002")
    c = parse_service("bob=http://host.local:9000/", 1.0)
    assert (c.name, c.base_url) == ("bob", "http://host.local:9000")


def test_cli_rejects_duplicate_names(capsys):
    try:
        main(["a=8001", "a=8002"])
    except SystemExit as exc:
        assert exc.code == 2
    assert "уникальны" in capsys.readouterr().err


def test_markdown_report_contains_table_matches_and_violations():
    from arena.services.render import format_report_markdown

    ace, mid, liar = _roster()
    clients = [make_client(ace, "ace"), make_client(mid, "mid"), make_client(liar, "liar")]
    standings, results = run_tournament(clients, games_per_pair=1, rng=random.Random(0))
    report = format_report_markdown(standings, results)
    assert "| # | Сервис | Очки |" in report
    assert "## Все партии" in report
    assert "## Нарушения контракта" in report
    assert "lie" in report
