from content.tutorial_loader import load_tutorial


def test_load_starter_tutorial() -> None:
    tutorial = load_tutorial("packs/starter/tutorials/dm_tutorial_map.json")
    assert tutorial.tutorial_id == "dm_quickstart"
    assert tutorial.estimated_minutes <= 15
    assert len(tutorial.steps) >= 4
