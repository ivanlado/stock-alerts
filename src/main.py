from alerts.analysts_alert import PriceAlert
from notifications.notifier import send_email
from providers import DataProviderImpl

def main():
    data_provider = DataProviderImpl()
    tickers = data_provider.get_tickers()
    tickers = tickers[:5]  # Limitar a los primeros 10 tickers para pruebas
    print(f"Number of tickers: {len(tickers)}")
    print(f"Tickers: {tickers}")
    alert = PriceAlert(tickers, data_provider=data_provider)
    msg = alert.run()
    print(msg)

    # if alerts:
    #     send_email(alerts)
    #     print(f"Email enviado con {len(alerts)} alerta(s)")
    # else:
    #     print("Sin alertas, no se envía correo")



if __name__ == "__main__":
    main()