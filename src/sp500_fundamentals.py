import yfinance as yf
import pandas as pd
from typing import Dict, List

def get_sp500_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch fundamental metrics for given S&P 500 companies.

    Args:
        tickers: List of stock ticker symbols

    Returns:
        DataFrame with fundamental metrics for each company
    """
    fundamentals_data = []

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Extract key metrics
            company_data = {
                'Ticker': ticker,
                'Company': info.get('longName', 'N/A'),
                'Sector': info.get('sector', 'N/A'),
                'P/E Ratio': info.get('trailingPE', 'N/A'),
                'Forward P/E': info.get('forwardPE', 'N/A'),
                'PEG Ratio': info.get('pegRatio', 'N/A'),
                'Price/Book': info.get('priceToBook', 'N/A'),
                'Dividend Yield': info.get('dividendYield', 'N/A'),
                'ROE': info.get('returnOnEquity', 'N/A'),
                'ROA': info.get('returnOnAssets', 'N/A'),
                'Debt/Equity': info.get('debtToEquity', 'N/A'),
                'Current Ratio': info.get('currentRatio', 'N/A'),
                'Quick Ratio': info.get('quickRatio', 'N/A'),
                'Operating Margin': info.get('operatingMargins', 'N/A'),
                'Net Margin': info.get('profitMargins', 'N/A'),
                'EPS Growth': info.get('epsTrailingTwelveMonths', 'N/A'),
                'Revenue Growth': info.get('revenueGrowth', 'N/A'),
                'Market Cap': info.get('marketCap', 'N/A'),
                'Total Debt': info.get('totalDebt', 'N/A'),
                'Total Cash': info.get('totalCash', 'N/A'),
                '52 Week Change': info.get('fiftyTwoWeekChange', 'N/A'),
            }

            fundamentals_data.append(company_data)
            print(f"✓ Fetched data for {ticker}")

        except Exception as e:
            print(f"✗ Error fetching {ticker}: {str(e)}")
            continue

    df = pd.DataFrame(fundamentals_data)
    return df


def display_metrics(df: pd.DataFrame):
    """Display metrics in a readable format."""
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    print("\n" + "="*150)
    print("S&P 500 FUNDAMENTAL METRICS")
    print("="*150 + "\n")

    # Display key valuation metrics
    valuation_cols = ['Ticker', 'Company', 'Sector', 'P/E Ratio', 'Forward P/E', 'PEG Ratio', 'Price/Book']
    print("VALUATION METRICS:")
    print(df[valuation_cols].to_string(index=False))

    print("\n" + "-"*150 + "\n")

    # Display profitability metrics
    profitability_cols = ['Ticker', 'ROE', 'ROA', 'Operating Margin', 'Net Margin']
    print("PROFITABILITY METRICS:")
    print(df[profitability_cols].to_string(index=False))

    print("\n" + "-"*150 + "\n")

    # Display financial health metrics
    health_cols = ['Ticker', 'Debt/Equity', 'Current Ratio', 'Quick Ratio', 'Total Debt', 'Total Cash']
    print("FINANCIAL HEALTH METRICS:")
    print(df[health_cols].to_string(index=False))

    print("\n" + "-"*150 + "\n")

    # Display growth and yield metrics
    growth_cols = ['Ticker', 'Revenue Growth', 'EPS Growth', 'Dividend Yield', '52 Week Change']
    print("GROWTH & YIELD METRICS:")
    print(df[growth_cols].to_string(index=False))


if __name__ == "__main__":
    # Top 10 S&P 500 companies by market cap
    sp500_tickers = [
        'MSFT',  # Microsoft
        'AAPL',  # Apple
        'NVDA',  # Nvidia
        'GOOGL', # Alphabet
        'AMZN',  # Amazon
        'META',  # Meta
        'TSLA',  # Tesla
        'BRK.B', # Berkshire Hathaway
        'JNJ',   # Johnson & Johnson
        'V',     # Visa
    ]

    print("Fetching fundamental data for 10 S&P 500 companies...\n")

    # Get fundamentals
    df = get_sp500_fundamentals(sp500_tickers)

    # Display results
    display_metrics(df)

    # Save to CSV
    csv_filename = 'sp500_fundamentals.csv'
    df.to_csv(csv_filename, index=False)
    print(f"\n\nData saved to {csv_filename}")
