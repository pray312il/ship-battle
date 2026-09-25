from app.services.targeting import build_target_queue, pick_next_shot
from app.services.fleet import parse_coordinate


def test_single_hit_gives_four_orthogonal_candidates():
    queue = build_target_queue(["E5"], shot_coords={"E5"})
    assert set(queue) == {"F5", "D5", "E6", "E4"}


def test_two_vertical_hits_extend_the_line_only():
    queue = build_target_queue(["E5", "E6"], shot_coords={"E5", "E6"})
    assert set(queue) == {"E4", "E7"}


def test_two_horizontal_hits_extend_the_line_only():
    queue = build_target_queue(["C3", "D3"], shot_coords={"C3", "D3"})
    assert set(queue) == {"B3", "E3"}


def test_queue_excludes_already_shot_cells():
    queue = build_target_queue(["E5"], shot_coords={"E5", "E6", "F5"})
    assert set(queue) == {"D5", "E4"}


def test_edge_cell_has_fewer_candidates():
    queue = build_target_queue(["A1"], shot_coords={"A1"})
    assert set(queue) == {"A2", "B1"}


def test_pick_next_shot_uses_queue_first():
    coordinate = pick_next_shot(own_shots={"E5": "hit"}, current_hits=["E5"], target_queue=["F5", "D5"])
    assert coordinate == "F5"


def test_pick_next_shot_skips_already_shot_queue_entries():
    coordinate = pick_next_shot(
        own_shots={"E5": "hit", "F5": "miss"}, current_hits=["E5"], target_queue=["F5", "D5"]
    )
    assert coordinate == "D5"


def test_pick_next_shot_rebuilds_queue_when_empty_but_hits_remain():
    coordinate = pick_next_shot(own_shots={"E5": "hit"}, current_hits=["E5"], target_queue=[])
    assert coordinate in {"F5", "D5", "E6", "E4"}


def test_pick_next_shot_falls_back_to_hunt_mode():
    coordinate = pick_next_shot(own_shots={}, current_hits=[], target_queue=[])
    x, y = parse_coordinate(coordinate)
    assert (x + y) % 2 == 0


def test_pick_next_shot_never_repeats_across_full_sweep():
    own_shots = {}
    for _ in range(100):
        coordinate = pick_next_shot(own_shots, current_hits=[], target_queue=[])
        assert coordinate not in own_shots
        own_shots[coordinate] = "miss"