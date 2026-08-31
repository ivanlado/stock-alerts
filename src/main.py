from alerts.analysts_alert import AnalystAlerts
from notifications.notifier import send_email
from providers import DataProviderImpl
from screening import FundamentalScreener
from alerts.price_alerts import PriceAlert

def main():
    data_provider = DataProviderImpl()
    tickers = data_provider.get_tickers()
    # tickers = tickers[:5]  # Limitar a los primeros 10 tickers para pruebas
    print(f"Number of tickers: {len(tickers)}")
    print(f"Tickers: {tickers}")

    screener = FundamentalScreener(data_provider)
    tickers = screener.filter(tickers)
    tickers = tickers[:20]  # Limitar a los primeros 10 tickers para pruebas
    print(f"Tickers tras filtro fundamental: {len(tickers)} -> {tickers}")

    msg = ""

    if not tickers:
        print("Ningún ticker pasa el filtro fundamental, no se envía correo")
        return

    alert = AnalystAlerts(tickers, data_provider=data_provider)
    msg_analyst = alert.run()
    print(msg_analyst)
    msg += msg_analyst
    
    alert = PriceAlert(tickers, data_provider=data_provider)
    msg_price = alert.run()
    print(msg_price)
    
    msg += "\n\n" + msg_price

    if msg:
        send_email(msg)
        print(f"Email enviado")
    else:
        print("Sin alertas, no se envía correo")



if __name__ == "__main__":
    main()