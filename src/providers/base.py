from abc import ABC, abstractmethod

import pandas as pd


class DataProvider(ABC):
    """Puerto (en el sentido de arquitectura hexagonal) hacia la fuente de datos de mercado.

    Cada adaptador concreto (yfinance, etc.) vive en su propio fichero e implementa
    esta interfaz. Cuando se añadan capacidades nuevas (p. ej. ``get_fundamentals``),
    se declaran aquí y todos los adaptadores deben proporcionarlas.
    """
    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Lista de tickers disponibles en la fuente de datos."""
        raise NotImplementedError

    @abstractmethod
    def get_analyst_targets(self, tickers: list[str]) -> pd.DataFrame:
        """Precio objetivo medio de analistas para cada ticker."""
        raise NotImplementedError
