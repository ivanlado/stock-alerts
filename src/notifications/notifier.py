import os
import smtplib
from email.message import EmailMessage
from typing import List

try:
    # En local carga las variables desde un fichero .env si existe.
    # En GitHub Actions no hay .env y las variables vienen de los secrets,
    # así que si python-dotenv no está instalado simplemente se ignora.
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_email(msg_text: str) -> None:
    """
    Envía por correo el mensaje de alerta usando el SMTP de Gmail.

    Requiere las variables de entorno:
      - GMAIL_USER:         dirección de Gmail que envía (ej. tu@gmail.com)
      - GMAIL_APP_PASSWORD: App Password de 16 caracteres de esa cuenta
      - ALERT_TO (opcional): destinatario; por defecto el propio GMAIL_USER
    """
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("ALERT_TO", "iviivilaca@gmail.com")

    msg = EmailMessage()
    msg["Subject"] = f"Alertas de acciones"
    msg["From"] = user
    msg["To"] = to

    body = "Tickers con alerta:\n\n" + msg_text
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
