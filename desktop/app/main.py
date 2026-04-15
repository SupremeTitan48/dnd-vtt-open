from content.tutorial_loader import load_tutorial
from desktop.app.session_controller import SessionController
from desktop.ui.tabletop_app import TabletopApp


def main() -> None:
    controller = SessionController()
    controller.start_local_session("Tutorial Session")

    if controller.engine:
        controller.engine.move_token("hero", 2, 2)
        controller.engine.move_token("goblin", 8, 5)
        controller.engine.set_initiative(["hero", "goblin"])
        controller.engine.add_item("hero", "Torch")
        controller.engine.set_hit_points("hero", 12)
        controller.engine.set_hit_points("goblin", 7)
        controller.engine.add_condition("goblin", "Marked")

    tutorial = load_tutorial("packs/starter/tutorials/dm_tutorial_map.json")

    print("DND VTT running:", controller.active_session_name)
    print("Loaded tutorial:", tutorial.title)

    app = TabletopApp(controller, tutorial)
    app.run()


if __name__ == "__main__":
    main()
