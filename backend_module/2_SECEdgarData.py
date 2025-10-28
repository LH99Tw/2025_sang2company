import pandas as pd
import numpy as np
import requests
import time
import os
import gc
from datetime import datetime
from typing import Dict, Optional
import json

# ------------------ Config ------------------
SEC_BASE_URL = "https://data.sec.gov"
HEADERS = {
    'User-Agent': 'MyCompany MyApp contact@example.com',
    'Accept': 'application/json',
    'Host': 'data.sec.gov'
}

# 데이터베이스 폴더 경로 설정
database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database')
filename = os.path.join(database_path, "sp500_data.csv")

# ------------------ Helper Functions ------------------
TICKER_ALIASES = {
    'BRK-B': ['BRK.B', 'BRKB', 'BRK B'],
    'BRK.B': ['BRK-B', 'BRKB', 'BRK B'],
    'IBKR': ['IBKR', 'IBKR-A'],
    'PSKY': ['PSNY', 'PSKY'],
}


def _generate_ticker_variations(raw_ticker: str) -> set[str]:
    """Generate possible variations for SEC lookup."""
    upper = raw_ticker.upper().strip()
    variations = {upper}

    if '-' in upper:
        variations.add(upper.replace('-', '.'))
        variations.add(upper.replace('-', ''))
    if '.' in upper:
        variations.add(upper.replace('.', '-'))
        variations.add(upper.replace('.', ''))

    variations.update(TICKER_ALIASES.get(upper, []))
    variations = {v.upper() for v in variations if v}
    return variations


def get_company_cik(ticker: str) -> Optional[str]:
    """Get the CIK for a given ticker using local company_tickers.json file"""
    try:
        # Load local company_tickers.json file
        company_tickers_path = os.path.join(database_path, "company_tickers.json")

        if not os.path.exists(company_tickers_path):
            print(f"Company tickers file not found at {company_tickers_path}")
            return None

        with open(company_tickers_path, 'r') as f:
            companies = json.load(f)

        variations = _generate_ticker_variations(ticker)

        for company_data in companies.values():
            listed_ticker = company_data.get('ticker', '').upper()
            if listed_ticker in variations:
                cik = str(company_data.get('cik_str')).zfill(10)
                print(f"Found CIK {cik} for ticker {ticker} (matched {listed_ticker})")
                return cik

        print(f"No CIK found for ticker {ticker} in local file")
        return None

    except Exception as e:
        print(f"Error getting CIK for {ticker}: {e}")
        return None

def get_company_facts(cik: str) -> Optional[dict]:
    try:
        cik_padded = str(cik).zfill(10)
        url = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting facts for CIK {cik}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting company facts: {e}")
        return None

def extract_financial_data(facts_data: dict) -> Optional[Dict[str, Dict[str, float]]]:
    try:
        if not facts_data or 'facts' not in facts_data:
            return None

        financial_data = {
            'EPS': {},
            'Revenue': {},
            'Net_Income': {},
            'Total_Assets': {},
            'Total_Debt': {},
            'Cash': {}
        }

        facts = facts_data['facts']
        if 'us-gaap' in facts:
            us_gaap = facts['us-gaap']
            
            # EPS (Earnings Per Share)
            if 'EarningsPerShareBasic' in us_gaap:
                eps_data = us_gaap['EarningsPerShareBasic']['units']['USD/shares']
                for period in eps_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['EPS'][date] = value
            
            # Revenue
            if 'Revenues' in us_gaap:
                revenue_data = us_gaap['Revenues']['units']['USD']
                for period in revenue_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['Revenue'][date] = value
            
            # Net Income
            if 'NetIncomeLoss' in us_gaap:
                net_income_data = us_gaap['NetIncomeLoss']['units']['USD']
                for period in net_income_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['Net_Income'][date] = value
            
            # Total Assets
            if 'Assets' in us_gaap:
                assets_data = us_gaap['Assets']['units']['USD']
                for period in assets_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['Total_Assets'][date] = value
            
            # Total Debt
            if 'LongTermDebt' in us_gaap:
                debt_data = us_gaap['LongTermDebt']['units']['USD']
                for period in debt_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['Total_Debt'][date] = value
            
            # Cash
            if 'CashAndCashEquivalentsAtCarryingValue' in us_gaap:
                cash_data = us_gaap['CashAndCashEquivalentsAtCarryingValue']['units']['USD']
                for period in cash_data:
                    if 'end' in period and 'val' in period:
                        date = period['end']
                        value = period['val']
                        financial_data['Cash'][date] = value

        return financial_data
    except Exception as e:
        print(f"Error extracting financial data: {e}")
        return None

def expand_quarterly_to_daily_sec(quarterly_data: dict, start_date, end_date):
    """Expand quarterly financial data to daily data with forward fill"""
    if quarterly_data is None:
        return pd.DataFrame()

    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    daily_data = pd.DataFrame(index=date_range)

    for metric_name, metric_data in quarterly_data.items():
        if metric_data:
            for date_str, value in metric_data.items():
                try:
                    date = pd.to_datetime(date_str)
                    if date in date_range:
                        daily_data.loc[date, metric_name] = value
                    else:
                        closest_date = date_range[date_range.get_indexer([date], method='nearest')[0]]
                        daily_data.loc[closest_date, metric_name] = value
                except Exception as e:
                    print(f"Error processing date {date_str}: {e}")
                    continue

    return daily_data.ffill()

def fill_financial_data_sec_for_ticker(ticker, df_ticker):
    """Fill financial data for a specific ticker using SEC EDGAR"""
    try:
        print(f"Processing SEC financial data for {ticker}...")
        
        # Get CIK for the ticker
        cik = get_company_cik(ticker)
        if not cik:
            print(f"No CIK found for {ticker}")
            return False
        
        print(f"  Found CIK: {cik} for {ticker}")
        
        # Get company facts from SEC
        facts_data = get_company_facts(cik)
        if not facts_data:
            print(f"No facts data available for {ticker}")
            return False
        
        # Extract financial data
        quarterly_financials = extract_financial_data(facts_data)
        
        if quarterly_financials:
            print(f"  Found financial data for {ticker}")
            for metric, data in quarterly_financials.items():
                if data:
                    print(f"    {metric}: {len(data)} periods")
            
            # Get date range for this ticker
            start_date = df_ticker['Date'].min()
            end_date = df_ticker['Date'].max()
            print(f"  Date range: {start_date} to {end_date}")
            
            # Expand quarterly data to daily data
            daily_financials = expand_quarterly_to_daily_sec(quarterly_financials, start_date, end_date)
            
            if not daily_financials.empty:
                print(f"  Generated daily data with {len(daily_financials.columns)} columns")
                # Update the dataframe with financial data
                for col in daily_financials.columns:
                    if col in df_ticker.columns:
                        # Merge financial data with price data based on date
                        for date in daily_financials.index:
                            if date in df_ticker['Date'].values:
                                mask = df_ticker['Date'] == date
                                df_ticker.loc[mask, col] = daily_financials.loc[date, col]
                
                print(f"Successfully filled SEC financial data for {ticker}")
                return True
            else:
                print(f"No daily financial data generated for {ticker}")
                return False
        else:
            print(f"No quarterly financial data available for {ticker}")
            return False
            
    except Exception as e:
        print(f"Error processing SEC financial data for {ticker}: {e}")
        return False

def fill_financial_data_sec_for_list(target_tickers: list[str]):
    """Fill financial data for a specific list of tickers."""
    try:
        if not target_tickers:
            print("No target tickers provided.")
            return

        df = pd.read_csv(filename, parse_dates=['Date'])
        if df.empty:
            print("CSV file is empty!")
            return

        normalized_targets = [ticker.upper().strip() for ticker in target_tickers]
        print(f"Processing target tickers: {', '.join(normalized_targets)}")

        successful_fills = 0
        failed_fills = 0

        for raw_ticker in normalized_targets:
            df_ticker = df[df['Ticker'].str.upper() == raw_ticker].copy()

            if df_ticker.empty:
                print(f"Ticker {raw_ticker} not found in source CSV. Skipping.")
                failed_fills += 1
                continue

            if fill_financial_data_sec_for_ticker(raw_ticker, df_ticker):
                df.loc[df['Ticker'].str.upper() == raw_ticker, df_ticker.columns] = df_ticker.values
                successful_fills += 1
            else:
                failed_fills += 1

            time.sleep(0.5)
            gc.collect()

        print("Saving updated data...")
        df.to_csv(filename, index=False)
        print(f"Completed SEC fills for target list. Success: {successful_fills}, Failed: {failed_fills}")

    except Exception as e:
        print(f"Error in fill_financial_data_sec_for_list: {e}")


def fill_all_financial_data_sec():
    """Fill financial data for all tickers in the CSV file using SEC EDGAR"""
    try:
        # Read the CSV file
        print("Reading CSV file...")
        df = pd.read_csv(filename, parse_dates=['Date'])
        
        if df.empty:
            print("CSV file is empty!")
            return
        
        print(f"Found {len(df)} rows with {df['Ticker'].nunique()} unique tickers")
        
        # Get unique tickers
        unique_tickers = df['Ticker'].unique()
        print(f"Processing {len(unique_tickers)} tickers...")
        
        successful_fills = 0
        failed_fills = 0
        
        for ticker in unique_tickers:
            try:
                # Get data for this ticker
                df_ticker = df[df['Ticker'] == ticker].copy()
                
                if fill_financial_data_sec_for_ticker(ticker, df_ticker):
                    # Update the main dataframe
                    df.loc[df['Ticker'] == ticker] = df_ticker
                    successful_fills += 1
                else:
                    failed_fills += 1
                
                # Add small delay to avoid rate limiting
                time.sleep(0.5)  # SEC API는 더 긴 대기시간 필요
                gc.collect()
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                failed_fills += 1
                continue
        
        # Save the updated dataframe
        print("Saving updated data...")
        df.to_csv(filename, index=False)
        
        print(f"SEC financial data filling completed!")
        print(f"Successful fills: {successful_fills}")
        print(f"Failed fills: {failed_fills}")
        
    except Exception as e:
        print(f"Error in fill_all_financial_data_sec: {e}")

if __name__ == "__main__":
    print("Starting SEC EDGAR financial data filling process...")
    target_tickers = ["APP", "BRK-B", "EME", "HOOD", "IBKR", "PSKY"]
    fill_financial_data_sec_for_list(target_tickers)
    print("Process completed!")
