import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import os
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
import pandas_datareader.data as web
import gc
import os
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

SEC_BASE_URL = "https://data.sec.gov"
SEC_HEADERS = {
    'User-Agent': 'MyCompany MyApp contact@example.com',
    'Accept': 'application/json'
}

COMPANY_TICKERS_CACHE = None


def _load_company_tickers():
    global COMPANY_TICKERS_CACHE
    if COMPANY_TICKERS_CACHE is not None:
        return COMPANY_TICKERS_CACHE

    company_tickers_path = os.path.join(database_path, "company_tickers.json")
    if os.path.exists(company_tickers_path):
        with open(company_tickers_path, 'r') as f:
            COMPANY_TICKERS_CACHE = json.load(f)
    else:
        COMPANY_TICKERS_CACHE = {}
    return COMPANY_TICKERS_CACHE


def _ticker_variations(ticker: str) -> set[str]:
    upper = ticker.upper().strip()
    variations = {upper}
    replacements = [('-', '.'), ('-', ''), ('.', '-'), ('.', '')]
    for old, new in replacements:
        if old in upper:
            variations.add(upper.replace(old, new))
    variations.update({
        'BRK-B': 'BRK.B',
        'BRK.B': 'BRK-B',
        'PSKY': 'PSNY',
        'PSNY': 'PSKY'
    }.get(upper, '').split(','))
    return {v for v in variations if v}


def get_company_cik_from_sec(ticker: str) -> str | None:
    companies = _load_company_tickers()
    variations = _ticker_variations(ticker)
    for company_data in companies.values():
        listed = company_data.get('ticker', '').upper()
        if listed in variations:
            return str(company_data.get('cik_str')).zfill(10)
    return None


def fetch_stock_info_from_sec(ticker: str) -> dict:
    record = {
        'Ticker': ticker,
        'Company_Name': '',
        'Sector': '',
        'Industry': '',
        'Country': '',
        'Exchange': '',
        'Market_Cap': 0,
        'IPO_Date': '',
        'Website': '',
        'Business_Summary': ''
    }

    cik = get_company_cik_from_sec(ticker)
    if not cik:
        print(f"SEC: No CIK found for {ticker}")
        return record

    try:
        url = f"{SEC_BASE_URL}/submissions/CIK{cik}.json"
        response = requests.get(url, headers=SEC_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        record['Company_Name'] = data.get('name', record['Company_Name'])
        record['Exchange'] = (data.get('exchanges') or [''])[0]
        record['Website'] = data.get('website', record['Website'])
        summary = data.get('description') or data.get('sicDescription') or ''
        record['Business_Summary'] = summary

        address = data.get('addresses', {}).get('business', {})
        country = address.get('country') or address.get('stateOrCountryDescription')
        if country and len(country) == 2:
            country = 'United States'
        record['Country'] = country or record['Country']

        sector_overrides = {
            'APP': ('Communication Services', 'Internet Content & Information'),
            'BRK-B': ('Financial Services', 'Insurance—Diversified'),
            'EME': ('Industrials', 'Engineering & Construction'),
            'HOOD': ('Financial Services', 'Capital Markets'),
            'IBKR': ('Financial Services', 'Capital Markets'),
            'PSKY': ('Consumer Cyclical', 'Auto Manufacturers'),
        }
        sector, industry = sector_overrides.get(ticker.upper(), (None, None))
        record['Sector'] = sector or record['Sector']
        record['Industry'] = industry or data.get('sicDescription', record['Industry'])

        return record
    except Exception as e:
        print(f"SEC request failed for {ticker}: {e}")
        return record

# Function to get the current list of S&P 500 components
def get_sp500_tickers():
    """Get S&P 500 tickers with fallback methods"""
    try:
        # Try Wikipedia first
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        table = pd.read_html(sp500_url, header=0)
        df = table[0]
        gc.collect()
        return df['Symbol'].tolist()
    except Exception as e:
        print(f"Wikipedia 접근 실패: {e}")
        print("대체 방법으로 S&P 500 티커 목록을 생성합니다...")
        
        # Fallback: Use a predefined list of major S&P 500 tickers
        fallback_tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
            'V', 'PG', 'JPM', 'XOM', 'HD', 'CVX', 'MA', 'PFE', 'ABBV', 'BAC', 'KO', 'AVGO',
            'PEP', 'TMO', 'COST', 'WMT', 'DHR', 'VZ', 'ADBE', 'ABT', 'NFLX', 'CRM', 'ACN',
            'TXN', 'NKE', 'QCOM', 'LIN', 'PM', 'NEE', 'RTX', 'T', 'HON', 'UNP', 'LOW',
            'SPGI', 'INTU', 'IBM', 'AMGN', 'CAT', 'GE', 'BKNG', 'GS', 'AXP', 'SYK',
            'BLK', 'DE', 'ISRG', 'TJX', 'GILD', 'MDT', 'CVS', 'CI', 'ANTM', 'CMCSA',
            'PYPL', 'ADP', 'TGT', 'USB', 'MMM', 'ZTS', 'SO', 'DUK', 'EOG', 'CL', 'MO',
            'APD', 'SHW', 'ITW', 'BDX', 'PNC', 'BSX', 'ICE', 'AON', 'SPG', 'EW', 'AEP',
            'NSC', 'ECL', 'EMR', 'EXC', 'PSA', 'A', 'ETN', 'FDX', 'PGR', 'ALL', 'ROST',
            'NOC', 'CTAS', 'PAYX', 'YUM', 'CHTR', 'EA', 'MCO', 'WM', 'TEL', 'AFL',
            'STZ', 'COO', 'CME', 'ETR', 'ES', 'EXR', 'VRSK', 'WEC', 'AWK', 'DTE',
            'FIS', 'FTV', 'GLW', 'HSY', 'IEX', 'IP', 'IRM', 'JKHY', 'K', 'LHX',
            'LNT', 'LUV', 'MAS', 'MKC', 'NDAQ', 'NTRS', 'O', 'PKI', 'PPG', 'PRU',
            'RMD', 'ROP', 'SBAC', 'SRE', 'SWK', 'SYY', 'TROW', 'TRV', 'TSN', 'UAL',
            'VMC', 'WBA', 'WY', 'XEL', 'ZBH', 'ZBRA', 'ZION'
        ]
        
        print(f"대체 목록 사용: {len(fallback_tickers)}개 티커")
        return fallback_tickers

# Function to map problematic tickers to their correct Yahoo Finance symbols
def map_ticker_to_yahoo(ticker):
    """Map problematic tickers to their correct Yahoo Finance symbols"""
    # Known problematic tickers with their correct Yahoo Finance symbols
    known_mappings = {
        'BRK.B': 'BRK-B',  # Berkshire Hathaway Class B
        'BF.B': 'BF-B',    # Brown-Forman Class B
        'BRK.A': 'BRK-A',  # Berkshire Hathaway Class A
        'BF.A': 'BF-A',    # Brown-Forman Class A
        'PSKY': 'PSNY',    # Polestar Automotive (Yahoo: PSNY)
        'META': 'FB',      # Meta Platforms (pre-2022 symbol on Yahoo history)
    }
    
    # First check known mappings
    if ticker in known_mappings:
        return known_mappings[ticker]
    
    # For other tickers with dots, try both original and hyphenated versions
    if '.' in ticker:
        return ticker.replace('.', '-')
    
    return ticker

# 데이터베이스 폴더 경로 설정
database_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database')
os.makedirs(database_path, exist_ok=True)
filename = os.path.join(database_path, "sp500_data.csv")
stock_info_filename = os.path.join(database_path, "sp500_stock_info.csv")
last_update_filename = os.path.join(database_path, "last_update.json")

# Function to save last update date
def save_last_update_date(date_str):
    """Save the last update date"""
    last_update = {
        'last_date': date_str,
        'updated_at': datetime.now().isoformat()
    }
    with open(last_update_filename, 'w') as f:
        json.dump(last_update, f)

# Function to load last update date
def load_last_update_date():
    """Load the last update date"""
    if os.path.exists(last_update_filename):
        with open(last_update_filename, 'r') as f:
            last_update = json.load(f)
            return last_update.get('last_date')
    return None

# Function to download stock information (sector, industry, country)
def fetch_stock_info_record(ticker: str) -> dict:
    """Fetch stock info for a single ticker via Yahoo Finance."""
    default_record = {
        'Ticker': ticker,
        'Company_Name': '',
        'Sector': '',
        'Industry': '',
        'Country': '',
        'Exchange': '',
        'Market_Cap': 0,
        'IPO_Date': '',
        'Website': '',
        'Business_Summary': ''
    }

    yahoo_ticker = map_ticker_to_yahoo(ticker)
    print(f"Getting stock info for {ticker} (Yahoo: {yahoo_ticker})...")

    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{yahoo_ticker}"
    params = {
        'modules': 'assetProfile,price,summaryProfile'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36',
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        result = data.get('quoteSummary', {}).get('result', [{}])[0]

        asset_profile = result.get('assetProfile', {})
        summary_profile = result.get('summaryProfile', {})
        price_info = result.get('price', {})

        record = default_record.copy()
        record.update(
            Company_Name=price_info.get('longName') or price_info.get('shortName', ''),
            Sector=asset_profile.get('sector') or summary_profile.get('sector', ''),
            Industry=asset_profile.get('industry') or summary_profile.get('industry', ''),
            Country=asset_profile.get('country') or summary_profile.get('country', ''),
            Exchange=price_info.get('exchangeName', ''),
            Market_Cap=price_info.get('marketCap', {}).get('raw', 0),
            IPO_Date=price_info.get('firstTradeDateMilliseconds', ''),
            Website=asset_profile.get('website', ''),
            Business_Summary=asset_profile.get('longBusinessSummary', ''),
        )

        # Fallback to yfinance if critical fields missing
        if not any([record['Sector'], record['Industry'], record['Company_Name']]):
            raise ValueError('Incomplete data from Yahoo Finance API fallback to yfinance')

        return record
    except Exception as e:
        print(f"Yahoo Finance request failed for {ticker}: {e}")

        try:
            ticker_obj = yf.Ticker(yahoo_ticker)
            info = ticker_obj.info
            if info:
                record = default_record.copy()
                record.update(
                    Company_Name=info.get('longName', ''),
                    Sector=info.get('sector', ''),
                    Industry=info.get('industry', ''),
                    Country=info.get('country', ''),
                    Exchange=info.get('exchange', ''),
                    Market_Cap=info.get('marketCap', 0),
                    IPO_Date=info.get('firstTradeDateEpochUtc', ''),
                    Website=info.get('website', ''),
                    Business_Summary=info.get('longBusinessSummary', ''),
                )
                return record
        except Exception as inner_e:
            print(f"yfinance fallback failed for {ticker}: {inner_e}")

        sec_record = fetch_stock_info_from_sec(ticker)
        if any(sec_record.values()):
            return sec_record

        return default_record


def update_stock_info_records(records: list[dict]):
    """Merge fetched records into existing stock info CSV."""
    if not records:
        return

    if os.path.exists(stock_info_filename):
        stock_info_df = pd.read_csv(stock_info_filename)
    else:
        stock_info_df = pd.DataFrame(columns=[
            'Ticker', 'Company_Name', 'Sector', 'Industry', 'Country',
            'Exchange', 'Market_Cap', 'IPO_Date', 'Website', 'Business_Summary'
        ])

    for record in records:
        ticker_upper = record['Ticker'].upper()
        mask = stock_info_df['Ticker'].str.upper() == ticker_upper if not stock_info_df.empty else pd.Series(dtype=bool)
        if not stock_info_df.empty and mask.any():
            stock_info_df.loc[mask, record.keys()] = record
        else:
            stock_info_df = pd.concat([stock_info_df, pd.DataFrame([record])], ignore_index=True)

    stock_info_df.to_csv(stock_info_filename, index=False)
    print(f"Updated stock information saved to {stock_info_filename}")


def download_stock_info():
    """Download stock information for all S&P 500 stocks."""
    sp500_tickers = get_sp500_tickers()
    records = []

    print("Downloading stock information...")

    for ticker in sp500_tickers:
        records.append(fetch_stock_info_record(ticker))
        time.sleep(2.0)

    update_stock_info_records(records)
    return pd.DataFrame(records)


def update_stock_info_for_list(target_tickers: list[str]):
    """Fetch and update stock info for a specific list of tickers."""
    if not target_tickers:
        print("No target tickers specified for stock info update.")
        return

    records = []
    for ticker in target_tickers:
        records.append(fetch_stock_info_record(ticker))
        time.sleep(1.0)

    update_stock_info_records(records)

# Function to get quarterly financial data with actual earnings dates
def get_quarterly_financials_with_dates(ticker):
    try:
        yahoo_ticker = map_ticker_to_yahoo(ticker)
        ticker_obj = yf.Ticker(yahoo_ticker)

        income_stmt = ticker_obj.quarterly_income_stmt
        balance_sheet = ticker_obj.quarterly_balance_sheet
        earnings_dates = ticker_obj.earnings_dates

        # Convert columns to datetime for alignment
        if isinstance(income_stmt.columns[0], str):
            income_stmt.columns = pd.to_datetime(income_stmt.columns)
        if isinstance(balance_sheet.columns[0], str):
            balance_sheet.columns = pd.to_datetime(balance_sheet.columns)

        financial_data = {}

        def safe_get(row_names, df):
            """ row_names: list of possible row names """
            for name in row_names:
                if name in df.index:
                    series = df.loc[name]
                    if isinstance(series, pd.Series):  # 날짜별 재무정보가 있는 경우
                        return series
                    elif isinstance(series, (int, float)):  # 단일 숫자일 경우
                        return pd.Series([series])
            return pd.Series(dtype='float64')

        # 재무제표 수집
        financial_data = {}
        financial_data['EPS'] = safe_get(['Basic EPS', 'Diluted EPS', 'Earnings Per Share'], income_stmt)
        financial_data['Revenue'] = safe_get(['Total Revenue', 'TotalRevenue'], income_stmt)
        financial_data['Net_Income'] = safe_get(['Net Income', 'NetIncome', 'NetIncomeApplicableToCommonShares'], income_stmt)
        financial_data['Total_Assets'] = safe_get(['Total Assets', 'TotalAssets'], balance_sheet)
        financial_data['Total_Debt'] = safe_get(['Total Debt', 'Long Term Debt', 'LongTermDebt', 'Short Long Term Debt'], balance_sheet)
        financial_data['Cash'] = safe_get(['Cash', 'Cash And Cash Equivalents', 'CashAndCashEquivalents'], balance_sheet)

        # ROA 계산
        try:
            roa = financial_data['Net_Income'] / financial_data['Total_Assets']
            roa = roa.replace([float('inf'), -float('inf')], pd.NA).dropna()
            financial_data['ROA'] = roa
        except Exception as e:
            print(f"ROA 계산 실패: {e}")
            financial_data['ROA'] = pd.Series(dtype='float64')


        # 실제 수치들이 하나라도 존재하는지 확인
        if all([v.empty for v in financial_data.values()]):
            return None, None

        return financial_data, earnings_dates

    except Exception as e:
        print(f"[{ticker}] 재무 데이터 수집 실패: {e}")
        return None, None


# Function to expand quarterly data to daily data using actual earnings dates
def expand_quarterly_to_daily_correct(quarterly_data, earnings_dates, start_date, end_date):
    if quarterly_data is None:
        return pd.DataFrame()

    daily_index = pd.date_range(start=start_date, end=end_date, freq='D')
    daily_df = pd.DataFrame(index=daily_index)

    for metric, series in quarterly_data.items():
        for date, value in series.items():
            date = pd.to_datetime(date)
            if date in daily_df.index:
                daily_df.loc[date, metric] = value

    return daily_df.ffill()

# Function to process single ticker data
def process_ticker_data(ticker, start_date):
    """Process data for a single ticker"""
    try:
        print(f"Downloading data for {ticker}...")
        
        # Map ticker to correct Yahoo Finance symbol
        yahoo_ticker = map_ticker_to_yahoo(ticker)
        
        # Always download from the earliest available date to avoid pre-IPO artifacts
        ticker_data = yf.download(yahoo_ticker, period="max", progress=False, auto_adjust=True)
        
        # If mapped ticker fails, try original ticker symbol
        if ticker_data.empty and yahoo_ticker != ticker:
            print(f"Retrying with original ticker {ticker} (period=max)...")
            ticker_data = yf.download(ticker, period="max", progress=False, auto_adjust=True)
        
        if ticker_data.empty:
            print(f"No data available for {ticker}")
            return None
        
        # Clip to start_date if provided (keeps only earliest available rows)
        if start_date:
            try:
                start_dt = pd.to_datetime(start_date)
                ticker_data = ticker_data[ticker_data.index >= start_dt]
            except Exception:
                pass

        # Get dividends and splits using the mapped yahoo symbol
        ticker_obj = yf.Ticker(yahoo_ticker)
        dividends = ticker_obj.dividends
        splits = ticker_obj.splits
        
        # Get stock info
        info = ticker_obj.info or {}
        market_cap = info.get('marketCap', 0)
        shares_outstanding = info.get('sharesOutstanding', 0)
        
        # Get quarterly financial data
        quarterly_financials, earnings_dates = get_quarterly_financials_with_dates(ticker)
        
        # Process price data
        ticker_data.dropna(inplace=True)
        ticker_data.reset_index(inplace=True)
        ticker_data['Ticker'] = ticker
        
        # Handle auto_adjust=True case where Adj Close column might not exist
        if 'Adj Close' not in ticker_data.columns:
            ticker_data['Adj Close'] = ticker_data['Close']
        
        # Ensure Adj_Close column exists (for consistency)
        if 'Adj_Close' not in ticker_data.columns:
            ticker_data['Adj_Close'] = ticker_data['Adj Close']
        
        # Add dividends and splits
        ticker_data['Dividends'] = 0.0
        ticker_data['Splits'] = 1.0
        
        # Fill dividends
        if not dividends.empty:
            for date, div in dividends.items():
                mask = ticker_data['Date'].dt.date == date.date()
                ticker_data.loc[mask, 'Dividends'] = div
        
        # Fill splits
        if not splits.empty:
            for date, split in splits.items():
                mask = ticker_data['Date'].dt.date == date.date()
                ticker_data.loc[mask, 'Splits'] = split
        
        # Add market cap and shares outstanding
        ticker_data['Market_Cap'] = market_cap
        ticker_data['Shares_Outstanding'] = shares_outstanding
        
        # Add financial data
        ticker_data['EPS'] = np.nan
        ticker_data['Revenue'] = np.nan
        ticker_data['Net_Income'] = np.nan
        ticker_data['Total_Assets'] = np.nan
        ticker_data['Total_Debt'] = np.nan
        ticker_data['Cash'] = np.nan
        ticker_data['ROA'] = np.nan
        
        # Expand quarterly financials to daily data
        if quarterly_financials and len(quarterly_financials) > 0:
            daily_financials = expand_quarterly_to_daily_correct(quarterly_financials, earnings_dates, ticker_data['Date'].min(), ticker_data['Date'].max())
            
            if not daily_financials.empty:
                # Merge financial data with price data
                for col in daily_financials.columns:
                    if col in ticker_data.columns:
                        ticker_data[col] = daily_financials[col]
        
        # Reorder columns - ensure all required columns exist
        required_columns = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume', 
                          'Dividends', 'Splits', 'Market_Cap', 'Shares_Outstanding', 
                          'EPS', 'Revenue', 'Net_Income', 'Total_Assets', 'Total_Debt', 'Cash', 'ROA']
        
        # Check which columns exist and create missing ones
        for col in required_columns:
            if col not in ticker_data.columns:
                if col == 'Adj_Close' and 'Adj Close' in ticker_data.columns:
                    ticker_data['Adj_Close'] = ticker_data['Adj Close']
                elif col == 'Adj_Close' and 'Adj Close' not in ticker_data.columns:
                    ticker_data['Adj_Close'] = ticker_data['Close']  # Use Close as Adj_Close when auto_adjust=True
                else:
                    ticker_data[col] = np.nan
        
        # Reorder columns
        ticker_data = ticker_data[required_columns]
        
        # Optimize data types
        ticker_data = ticker_data.astype({
            'Open': 'float32',
            'High': 'float32',
            'Low': 'float32',
            'Close': 'float32',
            'Adj_Close': 'float32',
            'Volume': 'int32',
            'Dividends': 'float32',
            'Splits': 'float32',
            'Market_Cap': 'float64',
            'Shares_Outstanding': 'float64',
            'EPS': 'float32',
            'Revenue': 'float64',
            'Net_Income': 'float64',
            'Total_Assets': 'float64',
            'Total_Debt': 'float64',
            'Cash': 'float64',
            'ROA': 'float32'
        })
        
        print(f"Successfully processed data for {ticker} ({len(ticker_data)} rows)")
        return ticker_data
        
    except Exception as e:
        print(f"Error processing data for {ticker}: {e}")
        return None

# Function to download data and save to CSV incrementally
def download_data(start_date="2000-01-01"):
    # Get the list of S&P 500 tickers
    sp500_tickers = get_sp500_tickers()
    
    # Initialize the CSV file with headers (expanded columns)
    with open(filename, 'w') as f:
        f.write('Date,Ticker,Open,High,Low,Close,Adj_Close,Volume,Dividends,Splits,Market_Cap,Shares_Outstanding,EPS,Revenue,Net_Income,Total_Assets,Total_Debt,Cash,ROA\n')
    
    # Process tickers in parallel with limited workers to avoid API rate limiting
    successful_downloads = 0
    failed_downloads = 0
    
    # Use ThreadPoolExecutor with limited workers to avoid API rate limiting
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(process_ticker_data, ticker, start_date): ticker for ticker in sp500_tickers}
        
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                ticker_data = future.result()
                if ticker_data is not None:
                    # Append to CSV immediately
                    ticker_data.to_csv(filename, mode='a', index=False, header=False)
                    print(f"Successfully appended data for {ticker} ({len(ticker_data)} rows)")
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                gc.collect()
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                failed_downloads += 1
    
    print(f"Data download completed and saved to {filename}")
    print(f"Successful downloads: {successful_downloads}")
    print(f"Failed downloads: {failed_downloads}")

# Function to update data
def update_data():
    # Check if file exists
    if not os.path.exists(filename):
        print(f"{filename} does not exist. Starting full download.")
        download_data()
        return
    
    # Load last update date
    last_update_date = load_last_update_date()
    
    if last_update_date:
        # Add one day to start from the next day
        start_date = (pd.to_datetime(last_update_date) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        print(f"Starting update from {start_date} (last update: {last_update_date})")
    else:
        # If no last update date, start from 2000-01-01
        start_date = "2000-01-01"
        print(f"No last update date found. Starting from {start_date}")
    
    # Get the list of S&P 500 tickers
    sp500_tickers = get_sp500_tickers()
    
    # Initialize a temporary CSV for new data
    temp_filename = os.path.join(database_path, "sp500_data_new.csv")
    with open(temp_filename, 'w') as f:
        f.write('Date,Ticker,Open,High,Low,Close,Adj_Close,Volume,Dividends,Splits,Market_Cap,Shares_Outstanding,EPS,Revenue,Net_Income,Total_Assets,Total_Debt,Cash,ROA\n')
    
    # Process tickers in parallel with limited workers to avoid API rate limiting
    successful_updates = 0
    failed_updates = 0
    
    # Use ThreadPoolExecutor with limited workers to avoid API rate limiting
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = {executor.submit(process_ticker_data, ticker, start_date): ticker for ticker in sp500_tickers}
        
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                ticker_data = future.result()
                if ticker_data is not None:
                    # Append to CSV immediately
                    ticker_data.to_csv(filename, mode='a', index=False, header=False)
                    print(f"Successfully updated data for {ticker} ({len(ticker_data)} rows)")
                    successful_updates += 1
                else:
                    failed_updates += 1
                gc.collect()
                
            except Exception as e:
                print(f"Error processing {ticker}: {e}")
                failed_updates += 1
    
    print(f"Successful updates: {successful_updates}")
    print(f"Failed updates: {failed_updates}")
    
    # Remove duplicates from the CSV file
    try:
        # Read the entire CSV and remove duplicates
        all_data = pd.read_csv(filename, parse_dates=['Date'])
        all_data.drop_duplicates(subset=['Date', 'Ticker'], keep='last', inplace=True)
        
        # Optimize data types before saving
        all_data = all_data.astype({
            'Open': 'float32',
            'High': 'float32',
            'Low': 'float32',
            'Close': 'float32',
            'Adj_Close': 'float32',
            'Volume': 'int32',
            'Dividends': 'float32',
            'Splits': 'float32',
            'Market_Cap': 'float64',
            'Shares_Outstanding': 'float64',
            'EPS': 'float32',
            'Revenue': 'float64',
            'Net_Income': 'float64',
            'Total_Assets': 'float64',
            'Total_Debt': 'float64',
            'Cash': 'float64',
            'ROA': 'float32'
        })
        
        all_data.to_csv(filename, index=False)
        
        # Save last update date
        last_date = all_data['Date'].max()
        save_last_update_date(last_date.strftime('%Y-%m-%d'))
        
        print(f"Data updated successfully in {filename}")
        print(f"Last update date: {last_date.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"Error updating the main CSV: {e}")
    
    # Remove temporary file if it exists
    if os.path.exists(temp_filename):
        os.remove(temp_filename)

# 데이터 로드 함수
def load_data():
    """저장된 데이터를 로드하는 함수"""
    if os.path.exists(filename):
        df = pd.read_csv(filename, parse_dates=['Date'])
        print(f"데이터 로드 완료: {len(df)} 행, {df['Ticker'].nunique()} 개 종목")
        return df
    else:
        print(f"데이터 파일이 존재하지 않습니다: {filename}")
        return None

# Run the update function
if __name__ == "__main__":
    print("S&P 500 데이터 업데이트 시작...")
    
    # First, download stock information
    print("Downloading stock information...")
    download_stock_info()
    
    # Then update price and financial data
    update_data()
    
    # 데이터 로드 및 확인
    df = load_data()
    if df is not None:
        print("\n데이터 미리보기:")
        print(df.head())
        print(f"\n데이터 정보:")
        print(f"- 총 행 수: {len(df)}")
        print(f"- 종목 수: {df['Ticker'].nunique()}")
        print(f"- 날짜 범위: {df['Date'].min()} ~ {df['Date'].max()}")
        print(f"- 컬럼 수: {len(df.columns)}")
        print(f"- 컬럼 목록: {list(df.columns)}")
