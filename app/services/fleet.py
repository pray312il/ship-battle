import random

FIELD_SIZE = 10
COLUMNS = "ABCDEFGHIJ"
FLEET_COMPOSITION = {4:1, 3:2, 2:3, 1:4}
SHIP_SIZES = sorted(
    (size for size, count in FLEET_COMPOSITION.items() for _ in range(count)),
    reverse=True
)

def _parse_coordinate(coord: str) -> tuple[int, int]:
    col_letter, row_part = coord[0], coord[1:]
    if col_letter not in COLUMNS or not row_part.isdigit():
        raise ValueError(f"некорректная координата: {coord!r}")
    row = int(row_part)
    if not (1 <= row <= FIELD_SIZE):
        raise ValueError(f"Координата вне поля: {coord!r}")
    return COLUMNS.index(col_letter), row - 1

def _diagonal_neighbors(cell: tuple[int, int]) -> set[tuple[int, int]]:
    x, y = cell
    return {(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)}

def _is_straight_and_contiguous(cells: list[tuple[int, int]]) -> bool:
    if len(cells) == 1:
        return True
    xs = {c[0] for c in cells}
    ys = {c[1] for c in cells}
    if len(xs) == 1:
        rows = sorted(c[1] for c in cells)
        return rows == list(range(rows[0], rows[0] + len(cells)))
    if len(ys) == 1:
        cols = sorted(c[0] for c in cells)
        return cols == list(range(cols[0], cols[0] + len(cells)))
    return False

def validate_fleet(ships: list[dict]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    sizes: list[int] = []
    all_cells: dict[tuple[int, int], int] = {}
    parsed_ships: list[list[tuple[int, int]]] = []

    for idx, ship in enumerate(ships):
        coords = ship.get("coordinates", [])
        if not coords: 
            errors.append(f"Корабль #{idx}: пустой список координат")
            parsed_ships.append([])
            continue

        try:
            cells = [_parse_coordinate(c)for c in coords]
        except ValueError as e:
            errors.append(f"Корабль #{idx}: {e}")
            parsed_ships.append([])
            continue

        if len(set(cells)) != len(cells):
            errors.append(f"Корабль #{idx}: повторяющиеся координаты внутри корабля")
        if not _is_straight_and_contiguous(cells):
            errors.append(f"Корабль #{idx}: корабль не прямой или не сплошной ({coords})")

        sizes.append(len(coords))
        parsed_ships.append(cells)

        for cell in cells:
            if cell in all_cells:
                errors.append(f"Корабль #{idx}: клетка {coords} уже занята кораблём #{all_cells[cell]}")
            all_cells[cell] = idx
    if sorted(sizes, reverse=True) != SHIP_SIZES:
        errors.append(f"состав флота не совпадает: ожидалось {SHIP_SIZES}, получено {sorted(sizes, reverse=True)}")

    for idx, cells in enumerate(parsed_ships):
        for cell in cells:
            for neighbor in _diagonal_neighbors(cell):
                other_idx = all_cells.get(neighbor)
                if other_idx is not None and other_idx != idx:
                    errors.append(f"корабль #{idx} касается корабля #{other_idx} рядом с {neighbor}")
    errors = list(dict.fromkeys(errors))
    return (len(errors) == 0, errors)

def _try_place_ship(size: int, placed_cells: set[tuple[int, int]], attempts: int = 200):
    for _ in range(attempts):
        horizontal = random.choice([True, False])
        if horizontal:
            x = random.randint(0, FIELD_SIZE - size)
            y = random.randint(0, FIELD_SIZE - 1)
            cells = [(x + i, y) for i in range(size)]
        else:
            x = random.randint(0, FIELD_SIZE - 1)
            y = random.randint(0, FIELD_SIZE - size)
            cells = [(x, y + i) for i in range(size)]

        forbidden: set[tuple[int, int]] = set()
        for cell in cells:
            forbidden |= _diagonal_neighbors(cell)

        if forbidden.isdisjoint(placed_cells):
            return cells
    return None

def _to_coord(cell: tuple[int, int]) -> str:
    x, y = cell
    return f"{COLUMNS[x]}{y + 1}"

def generate_fleet() -> list[dict]:
    max_restarts = 200
    for _ in range(max_restarts):
        placed_cells: set[tuple[int, int]] = set()
        ships: list[dict] = []
        ok = True

        for size in SHIP_SIZES:
            cells = _try_place_ship(size, placed_cells)
            if cells is None:
                ok = False
                break
            placed_cells.update(cells)
            ships.append({"coordinates": [_to_coord(c) for c in cells]})
        if ok:
            return ships

    raise RuntimeError("не удалось сгенерировать расстановку флота")