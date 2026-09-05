from export import export_json
from notifications.formatter import format_snapshot
from notifications.notifier import send_email
from pipeline import run_pipeline


def main() -> None:
    snapshot = run_pipeline()

    export_json(snapshot)

    if not snapshot.has_alerts:
        print("Sin alertas, no se envía correo")
        return

    body = format_snapshot(snapshot)
    print(body)
    send_email(body)
    print("Email enviado")


if __name__ == "__main__":
    main()
