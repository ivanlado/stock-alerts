from alerts.base_alert import BaseAlert
import pandas as pd

class PriceAlert(BaseAlert):
    def __init__(self, tickers: list[str], data_provider):
        super().__init__(tickers, data_provider)
        self.prices = self.data_provider.get_prices(tickers, period="1y", interval="1d")
        
    def get_variations(df: pd.DataFrame, var: str = "close") -> pd.DataFrame:
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        for ticker in df['ticker'].unique():
            mask = df['ticker'] == ticker
            ticker_data = df[mask].sort_values('date')
            
            df.loc[mask, 'var_1m'] = ticker_data[var].pct_change(periods=30) * 100
            df.loc[mask, 'var_3m'] = ticker_data[var].pct_change(periods=90) * 100
            df.loc[mask, 'var_6m'] = ticker_data[var].pct_change(periods=180) * 100
            df.loc[mask, 'var_9m'] = ticker_data[var].pct_change(periods=270) * 100
        
        return df[df.groupby('ticker').cumcount(ascending=False) == 0]
        
    def apply_rules(self) -> list[dict]:
        data = self.prices
        variations = PriceAlert.get_variations(data)
        alerts = variations.loc[(variations['var_1m'] < -5) | (variations['var_3m'] < -10) | (variations['var_6m'] < -15) | (variations['var_9m'] < -20)]
        return alerts
    
    def alert_message(self, alerts: pd.DataFrame) -> str:
        msg = ""
        alerts = alerts.merge(self.tickers_info, on="ticker", how="left")
        for index, row in alerts.iterrows():
            aux = f"{row['ticker']} ({row['short_name']}): 1M={row['var_1m']:.2f}% | 3M={row['var_3m']:.2f}% | 6M={row['var_6m']:.2f}% | 9M={row['var_9m']:.2f}%\n"
            msg += aux
        return msg
    
    def run(self) -> str:
        alerts = self.apply_rules()
        msg = self.alert_message(alerts)
        return msg