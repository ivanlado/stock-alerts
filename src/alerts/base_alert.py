from abc import ABC, abstractmethod
from typing import Any, List, Dict
from pathlib import Path
import requests
import pandas as pd

from providers.base import DataProvider


class BaseAlert(ABC):
    def __init__(self, tickers: List[str], data_provider: DataProvider):
        if not tickers:
            raise ValueError("tickers cannot be empty")

        self.tickers = tickers
        self.data_provider = data_provider
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        self.tickers_info = pd.read_csv(data_dir / "tickers.csv")
  
    @abstractmethod
    def apply_rules(self, data: Any) -> List[Dict]:
        pass
    
    
