import os
import smtplib
from email.message import EmailMessage
from typing import List

try:
    # Locally, load the variables from a .env file if there is one.
    # On GitHub Actions there is no .env and the variables come from the
    # secrets, so if python-dotenv is not installed this is simply ignored.
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def send_email(msg_text: str) -> None:
    """
    Emails the alert message through Gmail's SMTP server.

    Requires the environment variables:
      - GMAIL_USER:          sending Gmail address (e.g. you@gmail.com)
      - GMAIL_APP_PASSWORD:  that account's 16-character App Password
      - ALERT_TO (optional): recipient; defaults to GMAIL_USER itself
    """
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    to = os.environ.get("ALERT_TO", "iviivilaca@gmail.com")

    msg = EmailMessage()
    msg["Subject"] = "Stock alerts"
    msg["From"] = user
    msg["To"] = to

    body = "Tickers with alerts:\n\n" + msg_text
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
