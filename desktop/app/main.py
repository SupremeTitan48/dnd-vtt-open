from desktop.app.session_controller import SessionController


def main() -> None:
    controller = SessionController()
    controller.start_local_session("Tutorial Session")
    print("DND VTT running:", controller.active_session_name)


if __name__ == "__main__":
    main()
