import argparse
import random
import sys

from arena.services.client import ServiceClient
from arena.services.render import format_match_line, format_report_markdown, format_standings, render_match
from arena.services.tournament import run_tournament


def parse_service(spec: str, timeout: float) -> ServiceClient:
    name, _, target = spec.partition("=")
    if not target:  # передали только порт или url
        target, name = name, ""
    if target.isdigit():
        url = f"http://127.0.0.1:{target}"
        name = name or f"port-{target}"
    else:
        url = target.rstrip("/")
        name = name or url
    return ServiceClient(name=name, base_url=url, timeout=timeout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arena", description="Арена «Морского боя»: турнир 1 vs все")
    parser.add_argument("services", nargs="+", help="имя=порт | имя=url | порт")
    parser.add_argument("--games", type=int, default=2, help="партий на каждую пару (по умолчанию 2)")
    parser.add_argument("--timeout", type=float, default=1.0, help="лимит ответа, с (по умолчанию 1.0)")
    parser.add_argument("--win-points", type=int, default=1, help="очков за победу")
    parser.add_argument("--seed", type=int, default=None, help="seed для воспроизводимости")
    parser.add_argument("--verbose", action="store_true", help="печатать каждый ход")
    parser.add_argument("--boards", action="store_true", help="рисовать поля после каждой партии")
    parser.add_argument("--report", metavar="ФАЙЛ", help="записать итоговый отчёт в Markdown-файл")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # кириллица в консоли Windows

    clients = [parse_service(spec, args.timeout) for spec in args.services]
    names = [c.name for c in clients]
    if len(set(names)) != len(names):
        parser.error(f"имена сервисов должны быть уникальны: {names}")
    if len(clients) < 2:
        parser.error("нужно минимум два сервиса")

    def on_match(result):
        print(format_match_line(result))
        for warning in result.warnings:
            print(f"    ! {warning}")
        if args.boards:
            print(render_match(result))
            print()

    standings, results = run_tournament(
        clients,
        games_per_pair=args.games,
        rng=random.Random(args.seed),
        win_points=args.win_points,
        on_match=on_match,
        emit=print if args.verbose else None,
    )

    print("\nИТОГИ ТУРНИРА")
    print(format_standings(standings))
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(format_report_markdown(standings, results))
        print(f"\nОтчёт записан в {args.report}")
    for c in clients:
        c.close_http()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
