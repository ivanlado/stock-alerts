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
    pipeline.py         # Orquesta el cálculo y devuelve un Snapshot (sin efectos)
    notifications/      # Sink: formateo (formatter.py) + envío de emails (notifier.py)
    export/             # Sink: Snapshot -> JSON para la web
    scripts/            # Scripts CLI de ingesta de datos (no parte del flujo principal)
    main.py             # Punto de entrada: pipeline -> export + email
  data/                 # Input curado a mano (tickers JSON, CSV)
  web/public/data/      # Output generado por export/ (gitignored)
  tests/                # Tests
  notebooks/            # Exploración y prototipos
  docs/                 # Documentación
  .github/workflows/    # CI/CD
```

## Arquitectura

- **Hexagonal**: `providers/base.py` define la interfaz `DataProvider` (ABC). `YFinanceProvider` es el adaptador concreto. `DataProviderImpl` compone los adaptadores y añade la carga de tickers desde JSON.
- **Una fuente, N sinks**: `pipeline.run_pipeline()` calcula y devuelve un `Snapshot` (dataclass con `screened`, `analyst_alerts`, `price_alerts`) sin efectos secundarios. Los consumidores lo formatean: `notifications/` a texto para el email, `export/` a JSON para la web.
- **Las alertas devuelven datos, no texto**: `BaseAlert.run()` devuelve un `DataFrame` enriquecido con `short_name`. Las subclases solo implementan `apply_rules()`. Ningún formateo dentro de `alerts/`.
- **Flujo principal**: `main.py` → `run_pipeline()` → `export_json()` + (si hay alertas) `format_snapshot()` → `send_email()`.
- **Contrato con la web**: cada fichero de `web/public/data/` es `{"generated_at": <ISO>, "rows": [...]}`. El frontend depende de esa forma, no del código Python.
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
