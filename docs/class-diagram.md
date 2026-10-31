# UML class diagram

Class diagram of the `stock-alerts` project, generated from the code in `src/`.

```mermaid
classDiagram
    class DataProvider {
        <<abstract>>
        +get_tickers() list~str~
        +get_analyst_targets(tickers: list~str~) DataFrame
    }

    class DataProviderImpl {
        -_yf: YFinanceProvider
        +get_tickers() list~str~
        +get_analyst_targets(tickers: list~str~) DataFrame
        +get_fundamentals(tickers: list~str~) DataFrame
        +get_prices(tickers: list~str~, period: str, interval: str) DataFrame
    }

    class YFinanceProvider {
        +get_tickers() list~str~
        +get_analyst_targets(tickers: list~str~) DataFrame
        +get_fundamentals(tickers: list~str~) DataFrame
        +get_prices(tickers: list~str~, period: str, interval: str) DataFrame
    }

    class BaseAlert {
        <<abstract>>
        +tickers: list~str~
        +data_provider: DataProvider
        +tickers_info: DataFrame
        +apply_rules(data: Any) list~Dict~
    }

    class AnalystAlerts {
        +data: DataFrame
        +apply_rules() list~Dict~
        +alert_message(alerts: DataFrame) str
        +run() str
    }

    class PriceAlert {
        +prices: DataFrame
        +get_variations(df: DataFrame, var: str) DataFrame
        +apply_rules() list~Dict~
        +alert_message(alerts: DataFrame) str
        +run() str
    }

    class FundamentalScreener {
        +data_provider: DataProvider
        +criteria: dict
        +filter(tickers: list~str~) list~str~
    }

    class Notifier {
        <<module: notifications.notifier>>
        +send_email(msg_text: str) None
    }

    class Main {
        <<module: main>>
        +main() None
    }

    DataProvider <|-- DataProviderImpl
    DataProvider <|-- YFinanceProvider
    DataProviderImpl o-- YFinanceProvider : uses

    BaseAlert <|-- AnalystAlerts
    BaseAlert <|-- PriceAlert
    BaseAlert o-- DataProvider : uses
    FundamentalScreener o-- DataProvider : uses

    Main ..> FundamentalScreener : creates
    Main ..> AnalystAlerts : creates
    Main ..> PriceAlert : creates
    Main ..> DataProviderImpl : creates
    Main ..> Notifier : uses
```

## Notes

- `DataProvider` (`src/providers/base.py`) is the hexagonal architecture's port for accessing market data. It declares `get_tickers()` and `get_analyst_targets()`; `get_fundamentals()` and `get_prices()` exist in the adapters but are not declared in the port yet.
- `DataProviderImpl` (`src/providers/data_provider_impl.py`) implements `DataProvider` by delegating to `YFinanceProvider` for price targets, fundamentals and historical prices, and reads the tickers from local JSON files in `data/tickers/`.
- `YFinanceProvider` (`src/providers/yfinance_provider.py`) is the concrete adapter towards the `yfinance` library; it does not implement `get_tickers()`.
- `BaseAlert` (`src/alerts/base_alert.py`) is the abstract base class of the alerts: it holds the ticker list, a reference to the `DataProvider`, and loads `data/tickers.csv` into `tickers_info` to enrich the messages with the company name.
- `AnalystAlerts` (`src/alerts/analysts_alert.py`) implements the rule based on the percentage difference between the current price and the analysts' median price target (alerts when it is more than 10% below).
- `PriceAlert` (`src/alerts/price_alerts.py`) implements the rule based on the closing price variation over several windows (1D, 1W, 1M, 3M, 6M, 9M, 1Y), measured in calendar time against the last price: it alerts on drops beyond -5%, -5%, -5%, -10%, -15%, -20% and -15% respectively.
- `FundamentalScreener` (`src/screening/fundamental_screener.py`) screens the tickers before the alerts according to fundamental criteria (debt/equity and operating margins).
- `Notifier` (`src/notifications/notifier.py`) exposes `send_email` to notify the alerts by email through Gmail's SMTP server.
- `Main` (`src/main.py`) is the entry point that orchestrates the flow: it fetches tickers, applies the fundamental screen, runs both alerts and sends the email with the two messages concatenated.
