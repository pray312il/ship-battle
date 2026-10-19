import pytest

from arena.services.rules import Field, parse_coordinate, validate_fleet
from tests.fakes import GOOD_FLEET, mirror


def test_parse_coordinate_ok():
    assert parse_coordinate("A1") == (0, 0)
    assert parse_coordinate("J10") == (9, 9)
    assert parse_coordinate("E5") == (4, 4)


@pytest.mark.parametrize("bad", ["K1", "A0", "A11", "a1", "A01", "", "1A", "AA", "A 1", None, 5, ["A1"]])
def test_parse_coordinate_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_coordinate(bad)


def test_valid_fleets_pass():
    assert validate_fleet(GOOD_FLEET) == []
    assert validate_fleet(mirror(GOOD_FLEET)) == []


def test_wrong_composition():
    assert validate_fleet(GOOD_FLEET[:-1])  # 9 кораблей
    assert validate_fleet(GOOD_FLEET + [["H10"]])  # 11 кораблей


def test_diagonal_touch_is_rejected():
    fleet = [list(s) for s in GOOD_FLEET]
    fleet[6] = ["B5"]  # B5 касается A4 углом
    assert any("касаются" in e for e in validate_fleet(fleet))


def test_side_touch_is_rejected():
    fleet = [list(s) for s in GOOD_FLEET]
    fleet[6] = ["B1"]  # B1 рядом с A1 и C1
    assert any("касаются" in e for e in validate_fleet(fleet))


def test_bent_and_gapped_ships_are_rejected():
    bent = [list(s) for s in GOOD_FLEET]
    bent[3] = ["A6", "B7"]
    assert any("не прямой" in e for e in validate_fleet(bent))
    gapped = [list(s) for s in GOOD_FLEET]
    gapped[1] = ["C1", "C3", "C4"]
    assert any("не прямой" in e for e in validate_fleet(gapped))


def test_out_of_field_and_duplicates():
    fleet = [list(s) for s in GOOD_FLEET]
    fleet[6] = ["K1"]
    assert any("некорректная координата" in e for e in validate_fleet(fleet))
    fleet = [list(s) for s in GOOD_FLEET]
    fleet[0] = ["A1", "A1", "A2", "A3"]
    assert any("повторяющиеся" in e for e in validate_fleet(fleet))


def test_overlapping_ships_are_rejected():
    fleet = [list(s) for s in GOOD_FLEET]
    fleet[1] = ["A3", "A4", "A5"]  # пересекается с кораблём A1-A4
    assert validate_fleet(fleet)


def test_field_shoot_results():
    field = Field([["A1", "A2"], ["C3"]])
    assert field.shoot("J10") == "miss"
    assert field.shoot("A1") == "hit"
    assert field.shoot("A2") == "killed"
    assert field.shoot("C3") == "killed"
    assert field.all_sunk()


def test_field_decks_left():
    field = Field([["A1", "A2"], ["C3"]])
    assert field.decks_left() == 3
    field.shoot("A1")
    assert field.decks_left() == 2
    assert not field.all_sunk()
