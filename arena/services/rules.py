import re

FIELD_SIZE = 10
COLUMNS = "ABCDEFGHIJ"
EXPECTED_SIZES = [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]  # 10 кораблей, 20 палуб
TOTAL_DECKS = sum(EXPECTED_SIZES)

_COORD_RE = re.compile(r"([A-J])(10|[1-9])")


def parse_coordinate(coord) -> tuple[int, int]:
    """'A1' -> (0, 0), 'J10' -> (9, 9). ValueError, если это не координата A1–J10."""
    if not isinstance(coord, str):
        raise ValueError(f"координата должна быть строкой, пришло {type(coord).__name__}")
    match = _COORD_RE.fullmatch(coord)
    if match is None:
        raise ValueError(f"некорректная координата: {coord!r}")
    return COLUMNS.index(match.group(1)), int(match.group(2)) - 1


def to_coordinate(cell: tuple[int, int]) -> str:
    x, y = cell
    return f"{COLUMNS[x]}{y + 1}"


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


def validate_fleet(ships: list[list[str]]) -> list[str]:
    """
    Проверяет расстановку по правилам: состав флота, прямизна и целостность
    кораблей, границы A1–J10, отсутствие пересечений и касаний (в том числе
    углами). Возвращает список нарушений — пустой, если всё в порядке.
    """
    errors: list[str] = []
    owner: dict[tuple[int, int], int] = {}
    parsed: list[list[tuple[int, int]]] = []
    sizes: list[int] = []

    for idx, coords in enumerate(ships):
        if not coords:
            errors.append(f"корабль #{idx}: пустой список координат")
            parsed.append([])
            continue
        try:
            cells = [parse_coordinate(c) for c in coords]
        except ValueError as exc:
            errors.append(f"корабль #{idx}: {exc}")
            parsed.append([])
            continue

        if len(set(cells)) != len(cells):
            errors.append(f"корабль #{idx}: повторяющиеся координаты")
        if not _is_straight_and_contiguous(cells):
            errors.append(f"корабль #{idx}: не прямой или не сплошной {coords}")

        sizes.append(len(cells))
        parsed.append(cells)
        for cell in cells:
            if cell in owner and owner[cell] != idx:
                errors.append(f"корабль #{idx}: клетка {to_coordinate(cell)} занята кораблём #{owner[cell]}")
            owner[cell] = idx

    if sorted(sizes, reverse=True) != EXPECTED_SIZES:
        errors.append(f"состав флота: ожидалось {EXPECTED_SIZES}, получено {sorted(sizes, reverse=True)}")

    for idx, cells in enumerate(parsed):
        for (x, y) in cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    other = owner.get((x + dx, y + dy))
                    if other is not None and other != idx:
                        errors.append(f"корабли #{idx} и #{other} касаются у {to_coordinate((x, y))}")

    return list(dict.fromkeys(errors))


class Field:
    """Истинное состояние флота одного игрока: корабли и попадания по ним."""

    def __init__(self, ships: list[list[str]]):
        self.ships: list[set[str]] = [set(coords) for coords in ships]
        self.hits: set[str] = set()

    def shoot(self, coord: str) -> str:
        """Применяет выстрел и возвращает ИСТИННЫЙ результат: miss / hit / killed."""
        for ship in self.ships:
            if coord in ship:
                self.hits.add(coord)
                return "killed" if ship <= self.hits else "hit"
        return "miss"

    def all_sunk(self) -> bool:
        return all(ship <= self.hits for ship in self.ships)

    def decks_left(self) -> int:
        return sum(len(ship - self.hits) for ship in self.ships)
