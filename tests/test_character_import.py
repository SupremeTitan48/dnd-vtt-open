from content.character_import import (
    import_character_by_format,
    normalize_character,
    validate_character_or_errors,
)


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


def test_import_dndbeyond_json() -> None:
    payload = '{"name":"Borin","classes":[{"name":"Fighter","level":3}],"baseHitPoints":25,"inventory":[{"name":"Shield"}]}'
    sheet = import_character_by_format('dndbeyond_json', payload)
    assert sheet.character_class == 'Fighter'
    assert sheet.level == 3


def test_import_csv() -> None:
    payload = "name,class,level,hit_points,items\nKara,Wizard,4,18,Staff;Potion\n"
    sheet = import_character_by_format('csv_basic', payload)
    assert sheet.name == 'Kara'
    assert 'Potion' in sheet.items


def test_import_pdf_best_effort() -> None:
    payload = "Name: Lira\nClass: Bard\nLevel: 5\nHP: 31\nItems: Lute, Dagger\n"
    sheet = import_character_by_format('pdf_parse', payload)
    assert sheet.name == 'Lira'
    assert sheet.hit_points == 31
