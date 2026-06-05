from src.price_alert import PriceAlert

def main():
    tickers = ["AAPL", "MSFT", "AMZN", "GOOG", "META", "ITX.MC"]
    alert = PriceAlert(tickers)
    alerts = alert.run()
    print(alerts)



if __name__ == "__main__":
    main()