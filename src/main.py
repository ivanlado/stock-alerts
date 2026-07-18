from price_alert import PriceAlert
from notifier import send_email
from utils.data import load_tickers

def main():
    tickers = load_tickers()
    tickers = tickers[:10]  # Limitar a los primeros 10 tickers para pruebas
    print(f"Number of tickers: {len(tickers)}")
    alert = PriceAlert(tickers)
    msg = alert.run()
    print(msg)

    # if alerts:
    #     send_email(alerts)
    #     print(f"Email enviado con {len(alerts)} alerta(s)")
    # else:
    #     print("Sin alertas, no se envía correo")



if __name__ == "__main__":
    main()