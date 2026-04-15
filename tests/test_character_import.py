from content.character_import import normalize_character, validate_character_or_errors


def test_character_import_valid() -> None:
    sheet = normalize_character(
        {
            "name": "Aria",
            "character_class": "Rogue",
            "level": 2,
            "hit_points": 14,
            "items": ["Dagger"],
        }
    )
    assert sheet.name == "Aria"


def test_character_import_invalid() -> None:
    sheet, errors = validate_character_or_errors({"name": "", "level": 0, "hit_points": 0})
    assert sheet is None
    assert errors
