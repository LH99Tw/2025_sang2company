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
from concurrent.futures import ThreadPoolExecutor, as_completed

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
def download_stock_info():
    """Download stock information for all S&P 500 stocks"""
    sp500_tickers = get_sp500_tickers()
    stock_info_list = []
    
    print("Downloading stock information...")
    
    # Use ThreadPoolExecutor for parallel processing
    def process_stock_info(ticker):
        try:
            print(f"Getting info for {ticker}...")
            # Map ticker to correct Yahoo Finance symbol
            yahoo_ticker = map_ticker_to_yahoo(ticker)
            ticker_obj = yf.Ticker(yahoo_ticker)
            info = ticker_obj.info
            
            stock_info = {
                'Ticker': ticker,
                'Company_Name': info.get('longName', ''),
                'Sector': info.get('sector', ''),
                'Industry': info.get('industry', ''),
                'Country': info.get('country', ''),
                'Exchange': info.get('exchange', ''),
                'Market_Cap': info.get('marketCap', 0),
                'IPO_Date': info.get('firstTradeDateEpochUtc', ''),
                'Website': info.get('website', ''),
                'Business_Summary': info.get('longBusinessSummary', '')
            }
            
            return stock_info
            
        except Exception as e:
            print(f"Error getting info for {ticker}: {e}")
            # Return empty info for failed tickers
            return {
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
    
    # Process stock info sequentially
    for ticker in sp500_tickers:
        stock_info = process_stock_info(ticker)
        stock_info_list.append(stock_info)
        
        # Add longer delay to avoid rate limiting
        time.sleep(2.0)
    
    # Save stock info
    stock_info_df = pd.DataFrame(stock_info_list)
    stock_info_df.to_csv(stock_info_filename, index=False)
    print(f"Stock information saved to {stock_info_filename}")
    
    return stock_info_df

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
        
        # Download price data with fallback
        ticker_data = yf.download(yahoo_ticker, start=start_date, progress=False, auto_adjust=True)
        
        # If mapped ticker fails, try original ticker
        if ticker_data.empty and yahoo_ticker != ticker:
            print(f"Retrying with original ticker {ticker}...")
            ticker_data = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        
        if ticker_data.empty:
            print(f"No data available for {ticker}")
            return None
        
        # Get dividends and splits
        ticker_obj = yf.Ticker(ticker)
        dividends = ticker_obj.dividends
        splits = ticker_obj.splits
        
        # Get stock info
        info = ticker_obj.info
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
