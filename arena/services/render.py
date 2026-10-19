from arena.services.match import MatchResult
from arena.services.rules import COLUMNS, FIELD_SIZE, parse_coordinate

LEGEND = "#  корабль   X  попадание   o  промах   .  пусто"


def render_board(ships: list[list[str]], shots_at_it: dict[str, str]) -> list[str]:
    """Поле одного игрока: его корабли + все выстрелы соперника по нему."""
    ship_cells = {c for ship in ships for c in ship}
    lines = ["    " + " ".join(COLUMNS)]
    for row in range(1, FIELD_SIZE + 1):
        cells = []
        for col in COLUMNS:
            coord = f"{col}{row}"
            if coord in ship_cells:
                cells.append("X" if coord in shots_at_it else "#")
            elif coord in shots_at_it:
                cells.append("o")
            else:
                cells.append(".")
        lines.append(f"{row:>2}  " + " ".join(cells))
    return lines


def render_match(result: MatchResult) -> str:
    """Оба поля рядом: слева поле первого игрока, справа — второго."""
    name_a, name_b = result.names
    if name_a not in result.fleets or name_b not in result.fleets:
        return "(расстановки не получены — рисовать нечего)"

    # по полю игрока A стрелял B, и наоборот
    board_a = render_board(_safe_fleet(result.fleets[name_a]), result.history.get(name_b, {}))
    board_b = render_board(_safe_fleet(result.fleets[name_b]), result.history.get(name_a, {}))

    title_a = f"{name_a} (по нему стрелял {name_b})"
    title_b = f"{name_b} (по нему стрелял {name_a})"
    width = max(len(board_a[0]), len(title_a)) + 6
    out = [title_a.ljust(width) + title_b]
    for left, right in zip(board_a, board_b):
        out.append(left.ljust(width) + right)
    out.append(LEGEND)
    return "\n".join(out)


def _safe_fleet(ships: list[list[str]]) -> list[list[str]]:
    """Нарисовать можно только валидные координаты — мусор от нарушителя пропускаем."""
    cleaned = []
    for ship in ships:
        good = []
        for coord in ship:
            try:
                parse_coordinate(coord)
                good.append(coord)
            except ValueError:
                pass
        cleaned.append(good)
    return cleaned


def format_match_line(result: MatchResult) -> str:
    name_a, name_b = result.names
    head = f"{name_a} vs {name_b}"
    if result.reason == "fleet_sunk":
        return (f"{head}: победил {result.winner} — {result.detail} "
                f"(ходов: {name_a} {result.shots[name_a]}, {name_b} {result.shots[name_b]})")
    if result.reason == "violation":
        return f"{head}: победил {result.winner} — нарушил контракт {result.detail}"
    if result.reason == "both_violated":
        return f"{head}: ничья — оба нарушили контракт ({result.detail})"
    return f"{head}: ничья — {result.detail}"


def format_standings(standings) -> str:
    header = f"{'#':>2}  {'Сервис':<16}{'Очки':>5}{'Побед':>7}{'Пораж.':>8}{'Ничьих':>8}{'Наруш.':>8}"
    lines = [header, "-" * len(header)]
    for place, s in enumerate(standings, start=1):
        lines.append(
            f"{place:>2}  {s.name:<16}{s.points:>5}{s.wins:>7}{s.losses:>8}{s.draws:>8}{s.violations:>8}"
        )
    return "\n".join(lines)


def format_report_markdown(standings, results) -> str:
    """Итоговый отчёт турнира в Markdown: таблица очков + все партии + нарушения."""
    lines = ["# Итоги турнира", "", "| # | Сервис | Очки | Победы | Поражения | Ничьи | Нарушения |",
             "|---|--------|------|--------|-----------|-------|-----------|"]
    for place, s in enumerate(standings, start=1):
        lines.append(f"| {place} | {s.name} | {s.points} | {s.wins} | {s.losses} | {s.draws} | {s.violations} |")

    lines += ["", "## Все партии", ""]
    for number, result in enumerate(results, start=1):
        lines.append(f"{number}. {format_match_line(result)}")

    violations = [r for r in results if r.reason in ("violation", "both_violated")]
    if violations:
        lines += ["", "## Нарушения контракта", ""]
        for result in violations:
            lines.append(f"- {result.names[0]} vs {result.names[1]}: {result.detail}")
    return "\n".join(lines) + "\n"
