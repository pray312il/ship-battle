from app.services.fleet import generate_fleet, validate_fleet


def test_generated_fleet_is_valid_many_times():
    for _ in range(300):
        ships = generate_fleet()
        valid, errors = validate_fleet(ships)
        assert valid, errors


def test_valid_fleet_composition():
    ships = generate_fleet()
    sizes = sorted((len(s["coordinates"]) for s in ships), reverse=True)
    assert sizes == [4, 3, 3, 2, 2, 2, 1, 1, 1, 1]


def test_rejects_wrong_fleet_composition():
    ships = [{"coordinates": ["A1", "A2", "A3", "A4", "A5"]}]
    valid, errors = validate_fleet(ships)
    assert not valid


def test_rejects_non_straight_ship():
    ships = [{"coordinates": ["A1", "B2"]}]
    valid, errors = validate_fleet(ships)
    assert not valid


def test_rejects_ships_touching_by_corner():
    ships = [{"coordinates": ["A1"]}, {"coordinates": ["B2"]}]
    valid, errors = validate_fleet(ships)
    assert not valid


def test_rejects_out_of_bounds_coordinate():
    ships = [{"coordinates": ["K1"]}]
    valid, errors = validate_fleet(ships)
    assert not valid


def test_rejects_overlapping_ships():
    ships = [{"coordinates": ["A1", "A2"]}, {"coordinates": ["A2", "A3"]}]
    valid, errors = validate_fleet(ships)
    assert not valid


def test_accepts_known_good_fleet():
    ships = [
        {"coordinates": ["A1", "A2", "A3", "A4"]},
        {"coordinates": ["C1", "C2", "C3"]},
        {"coordinates": ["E1", "E2", "E3"]},
        {"coordinates": ["A6", "A7"]},
        {"coordinates": ["C6", "C7"]},
        {"coordinates": ["E6", "E7"]},
        {"coordinates": ["J1"]},
        {"coordinates": ["J3"]},
        {"coordinates": ["J5"]},
        {"coordinates": ["J7"]},
    ]
    valid, errors = validate_fleet(ships)
    assert valid, errors