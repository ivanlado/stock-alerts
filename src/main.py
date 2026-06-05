from price_alert import PriceAlert
from notifier import send_email

def main():
    tickers = ["AAPL", "MSFT", "AMZN", "GOOG", "META", "ITX.MC"]
    alert = PriceAlert(tickers)
    alerts = alert.run()
    print(alerts)

    if alerts:
        send_email(alerts)
        print(f"Email enviado con {len(alerts)} alerta(s)")
    else:
        print("Sin alertas, no se envía correo")



if __name__ == "__main__":
    main()