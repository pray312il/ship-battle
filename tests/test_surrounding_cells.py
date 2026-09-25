from app.services.targeting import surrounding_cells


def test_single_deck_ship_surrounding_is_all_eight_neighbors():
    cells = surrounding_cells(["E5"])
    assert set(cells) == {"D4", "D5", "D6", "E4", "E6", "F4", "F5", "F6"}


def test_two_deck_vertical_ship_surrounding_is_bounding_box_minus_ship():
    cells = surrounding_cells(["E5", "E6"])
    assert set(cells) == {
        "D4", "D5", "D6", "D7",
        "F4", "F5", "F6", "F7",
        "E4", "E7",
    }


def test_corner_ship_has_fewer_surrounding_cells():
    cells = surrounding_cells(["A1"])
    assert set(cells) == {"A2", "B1", "B2"}


def test_surrounding_cells_excludes_the_ship_itself():
    cells = surrounding_cells(["E5", "E6"])
    assert "E5" not in cells
    assert "E6" not in cells