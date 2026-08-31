# Diagrama de clases UML

Diagrama de clases del proyecto `stock-alerts`, generado a partir del código en `src/`.

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
    DataProviderImpl o-- YFinanceProvider : usa

    BaseAlert <|-- AnalystAlerts
    BaseAlert <|-- PriceAlert
    BaseAlert o-- DataProvider : usa
    FundamentalScreener o-- DataProvider : usa

    Main ..> FundamentalScreener : crea
    Main ..> AnalystAlerts : crea
    Main ..> PriceAlert : crea
    Main ..> DataProviderImpl : crea
    Main ..> Notifier : usa
```

## Notas

- `DataProvider` (`src/providers/base.py`) es el puerto de la arquitectura hexagonal para acceder a datos de mercado. Declara `get_tickers()` y `get_analyst_targets()`; `get_fundamentals()` y `get_prices()` existen en los adaptadores pero todavía no están declaradas en el puerto.
- `DataProviderImpl` (`src/providers/data_provider_impl.py`) implementa `DataProvider` delegando en `YFinanceProvider` para price targets, fundamentales y precios históricos, y lee los tickers desde ficheros JSON locales en `data/tickers/`.
- `YFinanceProvider` (`src/providers/yfinance_provider.py`) es el adaptador concreto hacia la librería `yfinance`; no implementa `get_tickers()`.
- `BaseAlert` (`src/alerts/base_alert.py`) es la clase abstracta base de las alertas: mantiene la lista de tickers, una referencia al `DataProvider` y carga `data/tickers.csv` en `tickers_info` para enriquecer los mensajes con el nombre de la empresa.
- `AnalystAlerts` (`src/alerts/analysts_alert.py`) implementa la regla basada en la diferencia porcentual entre el precio actual y el precio objetivo medio de analistas (alerta si está más de un 10% por debajo).
- `PriceAlert` (`src/alerts/price_alerts.py`) implementa la regla basada en la variación del precio de cierre en distintas ventanas (1M, 3M, 6M, 9M) sobre un histórico de 1 año: alerta si cae más de -5%, -10%, -15% o -20% respectivamente.
- `FundamentalScreener` (`src/screening/fundamental_screener.py`) filtra los tickers antes de las alertas según criterios fundamentales (deuda/equity y márgenes operativos).
- `Notifier` (`src/notifications/notifier.py`) expone `send_email` para notificar las alertas por correo vía SMTP de Gmail.
- `Main` (`src/main.py`) es el punto de entrada que orquesta el flujo: obtiene tickers, aplica el filtro fundamental, ejecuta ambas alertas y envía el email con los dos mensajes concatenados.
