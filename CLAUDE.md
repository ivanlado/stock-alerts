# Stock Alerts

Sistema de alertas bursátiles que filtra tickers por fundamentales y detecta oportunidades mediante dos reglas: precio actual vs precio objetivo de analistas (`AnalystAlerts`) y caídas de precio en distintas ventanas temporales (`PriceAlert`). Se ejecuta diariamente a las 14:00 (hora peninsular) via GitHub Actions.

## Cómo ejecutar

```bash
# Desde la raíz del repo, con el venv activo
cd src && python main.py
```

El workflow de GitHub Actions ejecuta `python main.py` con `working-directory: src`, por lo que todos los imports son relativos a `src/`.

## Estructura del proyecto

```
repo/
  src/                  # Código fuente (todo import relativo a aquí)
    alerts/             # Reglas de alerta (BaseAlert, AnalystAlerts, PriceAlert)
    providers/          # Hexagonal: puerto (base.py) + adaptadores (yfinance)
    screening/          # Filtros fundamentales pre-alerta
    notifications/      # Envío de emails (Gmail SMTP)
    scripts/            # Scripts CLI de ingesta de datos (no parte del flujo principal)
    main.py             # Punto de entrada
  data/                 # Datos estáticos (tickers JSON, CSV, dashboard HTML)
  tests/                # Tests
  notebooks/            # Exploración y prototipos
  docs/                 # Documentación
  .github/workflows/    # CI/CD
```

## Arquitectura

- **Hexagonal**: `providers/base.py` define la interfaz `DataProvider` (ABC). `YFinanceProvider` es el adaptador concreto. `DataProviderImpl` compone los adaptadores y añade la carga de tickers desde JSON.
- **Flujo principal**: `main.py` → cargar tickers → filtrar por fundamentales (`FundamentalScreener`) → ejecutar alertas (`AnalystAlerts` y `PriceAlert`, cuyos mensajes se concatenan) → notificar por email.
- **Scripts de ingesta** (`src/scripts/`): se ejecutan manualmente para actualizar `data/`. No forman parte del flujo principal.

## Convenciones

- Idioma del código: inglés para nombres de variables, clases y funciones. Inglés en comentarios y docstrings.
- Type hints en todas las firmas de función.
- Imports relativos a `src/` (no absolutos desde la raíz del repo).
- Los paths a ficheros de datos usan `Path(__file__).resolve().parents[N] / "data"` para ser independientes del working directory.

## Variables de entorno

Definidas en `.env` (local) o GitHub Secrets (CI):
- `GMAIL_USER`: dirección Gmail para envío
- `GMAIL_APP_PASSWORD`: App Password de 16 caracteres
- `ALERT_TO`: destinatario de las alertas (opcional, default: GMAIL_USER)

## Dependencias

- `yfinance`: datos de mercado (price targets, fundamentales, statements)
- `pandas`: DataFrames para todo el flujo de datos
- `requests`: scraping de Wikipedia (tickers de índices)
- `python-dotenv`: carga de `.env` en local
