from abc import ABC, abstractmethod 
from typing import Any, List, Dict
import requests
import pandas as pd


class BaseAlert(ABC):
    def __init__(self, tickers: List[str]):
        if not tickers:
            raise ValueError("tickers cannot be empty")

        self.tickers = tickers
        self.tickers_info = pd.read_csv("data/tickers.csv")
    @abstractmethod
    def get_data(self) -> Any:
        pass
    @abstractmethod
    def apply_rules(self, data: Any) -> List[Dict]:
        pass
    
    
