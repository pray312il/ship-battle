import random

from app.services.fleet import FIELD_SIZE, parse_coordinate, to_coord, diagonal_neighbors 


def _neighbors_orthogonal(cell: tuple[int, int]) -> list[tuple[int, int]]:
    x, y = cell
    candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return [c for c in candidates if 0 <= c[0] < FIELD_SIZE and 0 <= c[1] < FIELD_SIZE]


def _line_direction(cells: list[tuple[int, int]]) -> str | None:
    xs = {c[0] for c in cells}
    ys = {c[1] for c in cells}
    if len(xs) == 1 and len(ys) > 1:
        return "vertical"
    if len(ys) == 1 and len(xs) > 1:
        return "horizontal"
    return None


def build_target_queue(current_hits: list[str], shot_coords: set[str]) -> list[str]:

    if not current_hits:
        return []

    hit_cells = [parse_coordinate(c) for c in current_hits]

    if len(hit_cells) == 1:
        candidates = _neighbors_orthogonal(hit_cells[0])
    else:
        direction = _line_direction(hit_cells)
        if direction == "vertical":
            x = hit_cells[0][0]
            ys = sorted(c[1] for c in hit_cells)
            candidates = [(x, ys[0] - 1), (x, ys[-1] + 1)]
        elif direction == "horizontal":
            y = hit_cells[0][1]
            xs = sorted(c[0] for c in hit_cells)
            candidates = [(xs[0] - 1, y), (xs[-1] + 1, y)]
        else:
            candidates = []
            for cell in hit_cells:
                candidates += _neighbors_orthogonal(cell)

    result: list[str] = []
    for c in candidates:
        if 0 <= c[0] < FIELD_SIZE and 0 <= c[1] < FIELD_SIZE:
            coord = to_coord(c)
            if coord not in shot_coords and coord not in result:
                result.append(coord)
    return result


def _checkerboard_candidates(shot_coords: set[str]) -> list[str]:
    result = []
    for x in range(FIELD_SIZE):
        for y in range(FIELD_SIZE):
            if (x + y) % 2 == 0:
                coord = to_coord((x, y))
                if coord not in shot_coords:
                    result.append(coord)
    return result


def _all_remaining_candidates(shot_coords: set[str]) -> list[str]:
    result = []
    for x in range(FIELD_SIZE):
        for y in range(FIELD_SIZE):
            coord = to_coord((x, y))
            if coord not in shot_coords:
                result.append(coord)
    return result

def pick_next_shot(own_shots: dict, current_hits: list[str], target_queue: list[str]) -> str:
    shot_coords = set(own_shots.keys())

    queue = [c for c in target_queue if c not in shot_coords]
    if queue:
        return queue[0]

    if current_hits:
        rebuilt = build_target_queue(current_hits, shot_coords)
        if rebuilt:
            return rebuilt[0]

    candidates = _checkerboard_candidates(shot_coords)
    if candidates:
        return random.choice(candidates)

    remaining = _all_remaining_candidates(shot_coords)
    if not remaining:
        raise RuntimeError("на поле не осталось необстрелянных клеток")
    return random.choice(remaining)

def surrounding_cells(ship_cells: list[str]) -> list[str]:
    ship_set = set(ship_cells)
    result: list[str] = []
    for coord in ship_cells:
        cell = parse_coordinate(coord)
        for nx, ny in diagonal_neighbors(cell):
            if 0 <= nx < FIELD_SIZE and 0 <= ny < FIELD_SIZE:
                neighbor_coord = to_coord((nx, ny))
                if neighbor_coord not in ship_set and neighbor_coord not in result:
                    result.append(neighbor_coord)
    return result