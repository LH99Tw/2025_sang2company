import os
import pandas as pd
from datetime import datetime

# Paths
database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database')
prices_csv = os.path.join(database_path, 'sp500_data.csv')

# Earliest valid trading date per ticker (IPO/listing or first realistic date)
EARLIEST_VALID = {
    'META': '2012-05-18',  # Meta (Facebook) IPO
    'HOOD': '2021-07-29',  # Robinhood IPO
    'IBKR': '2007-05-03',  # Interactive Brokers IPO
    'PSKY': '2022-06-24',  # Polestar (PSNY) listing
    'APP':  '2021-04-15',  # AppLovin IPO
    # Add/adjust tickers here as needed
}

def clean_anachronistic_rows(csv_path: str = prices_csv, dry_run: bool = False) -> pd.DataFrame:
    """
    Remove rows where a ticker appears before its earliest valid date.
    Returns the cleaned DataFrame. If dry_run=True, do not save.
    """
    df = pd.read_csv(csv_path, parse_dates=['Date'])
    before = len(df)

    masks = []
    for ticker, date_str in EARLIEST_VALID.items():
        cutoff = pd.to_datetime(date_str)
        mask = (df['Ticker'].str.upper() == ticker) & (df['Date'] < cutoff)
        masks.append(mask)

    if masks:
        combined = masks[0]
        for m in masks[1:]:
            combined |= m
        removed = df[combined]
        if not removed.empty:
            print(f"Removing {len(removed)} anachronistic rows:")
            print(removed[['Date','Ticker']].head())
        df = df[~combined]

    after = len(df)
    print(f"Cleaned rows: {before - after} | Remaining: {after}")

    if not dry_run:
        df.to_csv(csv_path, index=False)
        print(f"Saved cleaned data to {csv_path}")
    return df

if __name__ == '__main__':
    clean_anachronistic_rows()

