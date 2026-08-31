import pandas as pd

from providers.base import DataProvider


class FundamentalScreener:
    """Filtra una lista de tickers en base a criterios fundamentales.

    Los criterios se pasan como un ``dict`` para que el constructor no crezca
    al añadir métricas nuevas. Un criterio nuevo = una key en el dict + un
    método ``_xxx_ok`` + una línea en ``_passes``.
    """

    # Defaults en un único sitio; el dict de entrada solo sobreescribe lo que quiera.
    DEFAULT_CRITERIA = {
        "max_debt_to_equity": 1.0,      # 100%, solo último año
        "min_operating_margin": 0.07,   # 7%, cada uno de los últimos N años
        "operating_margin_years": 3,
    }

    def __init__(
        self,
        data_provider: DataProvider,
        criteria: dict | None = None,
    ):
        self.data_provider = data_provider
        self.criteria = {**self.DEFAULT_CRITERIA, **(criteria or {})}

    def filter(self, tickers: list[str]) -> list[str]:
        """Devuelve el subconjunto de tickers que cumple TODOS los criterios."""
        fundamentals = self.data_provider.get_fundamentals(tickers)
        return [
            t for t in tickers
            if self._passes(fundamentals[fundamentals["ticker"] == t])
        ]

    def _passes(self, df: pd.DataFrame) -> bool:
        c = self.criteria
        return (
            self._debt_to_equity_ok(df, c["max_debt_to_equity"])
            and self._operating_margin_ok(
                df, c["min_operating_margin"], c["operating_margin_years"]
            )
        )

    def _debt_to_equity_ok(self, df: pd.DataFrame, threshold: float) -> bool:
        """debtToEquity del último año disponible <= threshold. Falta dato -> descarta."""
        dte = df[df["metric"] == "debtToEquity"]
        if dte.empty:
            return False
        last = dte.loc[dte["year"].idxmax(), "value"]
        return last <= threshold

    def _operating_margin_ok(
        self, df: pd.DataFrame, threshold: float, years: int
    ) -> bool:
        """operatingMargins >= threshold en cada uno de los últimos ``years``.

        Si hay menos de ``years`` años de datos, descarta el ticker.
        """
        om = df[df["metric"] == "operatingMargins"].nlargest(years, "year")
        if len(om) < years:
            return False
        return bool((om["value"] >= threshold).all())
