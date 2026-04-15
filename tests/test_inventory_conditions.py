from engine.inventory_conditions import InventoryConditionsService


def test_inventory_and_conditions() -> None:
    svc = InventoryConditionsService()
    svc.add_item("hero", "Torch")
    svc.add_condition("hero", "Poisoned")
    svc.set_hit_points("hero", 9)
    state = svc.get_state("hero")
    assert "Torch" in state.held_items
    assert "Poisoned" in state.conditions
    assert state.hit_points == 9
