#!/usr/bin/env python
"""
build_sp500_history.py

위키피디아의 S&P 500 종목 목록을 크롤링한 뒤,
각 티커의 전 기간 데이터를 yfinance에서 받아
sp500_interpolated.csv와 동일한 포맷의 CSV로 저장합니다.
"""

from __future__ import annotations

import time
import json
from pathlib import Path
from typing import Dict
import inspect

import numpy as np
import pandas as pd
import yfinance as yf

try:
    from curl_cffi import requests as cf_requests
    _HAVE_CURL_CFFI = True
except ImportError:  # pragma: no cover - optional dependency
    cf_requests = None
    _HAVE_CURL_CFFI = False

import requests

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
OUTPUT_PATH = Path("database/sp500_interpolated.csv")
PROGRESS_PATH = OUTPUT_PATH.with_suffix(".progress.json")

# yfinance 심볼로 바꿔야 하는 케이스(필요 시 추가)
TICKER_SPECIAL_MAP: Dict[str, str] = {
    "BRK.B": "BRK-B",
    "BRK.A": "BRK-A",
    "BF.B": "BF-B",
    "BF.A": "BF-A",
    "PSKY": "PSNY",   # Polestar
    "META": "FB",     # Meta (상장 당시 티커)
}

OUTPUT_COLUMNS = [
    "Date", "Ticker",
    "Open", "High", "Low", "Close", "Adj_Close", "Volume",
    "Dividends", "Splits",
    "Market_Cap", "Shares_Outstanding",
    "EPS", "Revenue", "Net_Income", "Total_Assets", "Total_Debt", "Cash", "ROA",
]

# yfinance 함수가 session 파라미터를 지원하는지 확인
YF_DOWNLOAD_SUPPORTS_SESSION = "session" in inspect.signature(yf.download).parameters
YF_TICKER_SUPPORTS_SESSION = "session" in inspect.signature(yf.Ticker).parameters

_HTTP_SESSION = None


def get_http_session():
    """curl_cffi Session(impersonate="chrome") 또는 requests.Session을 반환."""
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        if _HAVE_CURL_CFFI:
            session = cf_requests.Session(impersonate="chrome")
        else:
            session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        _HTTP_SESSION = session
    return _HTTP_SESSION


def create_ticker(symbol: str):
    session = get_http_session()
    if YF_TICKER_SUPPORTS_SESSION:
        return yf.Ticker(symbol, session=session)
    return yf.Ticker(symbol)


def map_to_yf_symbol(ticker: str) -> str:
    """S&P 500 티커를 yfinance 심볼로 변환."""
    ticker = ticker.strip().upper()
    if ticker in TICKER_SPECIAL_MAP:
        return TICKER_SPECIAL_MAP[ticker]
    # yfinance는 '.' 대신 '-'를 사용
    return ticker.replace(".", "-")


def fetch_sp500_tickers() -> pd.Series:
    """위키피디아에서 S&P500 티커 목록을 추출."""
    try:
        session = get_http_session()
        resp = session.get(WIKI_URL, timeout=10)
        resp.raise_for_status()
        tables = pd.read_html(resp.text, header=0)
        table = tables[0]
        tickers = table["Symbol"].astype(str).str.strip().str.upper()
        print(f"✓ 위키에서 {len(tickers)}개 티커 로드")
        return tickers
    except Exception as exc:
        raise RuntimeError(f"위키피디아에서 티커를 가져오지 못했습니다: {exc}")


def normalized_price_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """yfinance DataFrame을 저장 포맷에 맞춰 정리."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        level_names = df.columns.names
        if level_names and "Ticker" in level_names:
            df = df.xs(ticker, axis=1, level="Ticker")
        else:
            df = df.xs(df.columns[0][1], axis=1, level=1)
        df.columns = [col if isinstance(col, str) else col[0] for col in df.columns]

    df.reset_index(inplace=True)          # Date 컬럼으로
    df.rename(columns={"Adj Close": "Adj_Close",
                       "Stock Splits": "Stock_Splits"}, inplace=True)

    # 필수 컬럼이 없으면 채우기
    for col in ["Dividends", "Stock_Splits"]:
        if col not in df.columns:
            df[col] = 0.0

    df["Splits"] = df.pop("Stock_Splits").replace(0, 1.0)
    df["Ticker"] = ticker

    # 나머지 재무 컬럼 채우기(현재는 NaN/0으로 두고 이후에 보간 가능)
    df["Market_Cap"] = np.nan
    df["Shares_Outstanding"] = np.nan
    df["EPS"] = np.nan
    df["Revenue"] = np.nan
    df["Net_Income"] = np.nan
    df["Total_Assets"] = np.nan
    df["Total_Debt"] = np.nan
    df["Cash"] = np.nan
    df["ROA"] = np.nan

    # 열 순서 맞추기 / 누락된 열 생성
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[OUTPUT_COLUMNS]

    return df


def download_full_history(ticker: str) -> pd.DataFrame:
    """한 종목의 전 기간 데이터를 다운로드(존재하는 가장 과거 시점부터)."""
    yf_symbol = map_to_yf_symbol(ticker)
    print(f"  → {ticker} (Yahoo: {yf_symbol}) 데이터 수집 중…", end=" ")

    data = try_yfinance_download(yf_symbol)
    if data.empty and yf_symbol != ticker:
        print("재시도…", end=" ")
        data = try_yfinance_download(ticker)

    if data.empty:
        data = try_history_download(yf_symbol)
        if data.empty and yf_symbol != ticker:
            data = try_history_download(ticker)

    if data.empty:
        data = download_from_chart_api(yf_symbol)
        if data.empty and yf_symbol != ticker:
            data = download_from_chart_api(ticker)

    if data.empty:
        print("데이터 없음")
        return pd.DataFrame()

    print(f"{len(data):,}건 OK")
    return normalized_price_frame(data, ticker)


def try_yfinance_download(symbol: str) -> pd.DataFrame:
    """yfinance 다운로드를 시도하고 RateLimit 시 지연 후 재시도."""
    wait_seconds = [1, 3, 6, 12]
    base_kwargs = dict(
        period="max",
        progress=False,
        auto_adjust=False,
        actions=True,
        threads=False,
    )
    session = get_http_session()
    if YF_DOWNLOAD_SUPPORTS_SESSION:
        base_kwargs["session"] = session

    for pause in wait_seconds:
        try:
            kwargs = dict(base_kwargs)
            data = yf.download(symbol, **kwargs)
            if not data.empty:
                return data
        except Exception as exc:
            msg = str(exc)
            if "Too Many Requests" not in msg:
                print(f"(yfinance 오류: {msg})", end=" ")
                return pd.DataFrame()
        time.sleep(pause)
    return pd.DataFrame()


def try_history_download(symbol: str) -> pd.DataFrame:
    """Ticker.history()를 이용한 페치. 각 호출 사이에 짧은 지연으로 Rate Limit 회피."""
    waits = [1, 2, 4, 8]
    ticker_obj = create_ticker(symbol)
    for pause in waits:
        try:
            data = ticker_obj.history(period="max", auto_adjust=False, actions=True)
            if not data.empty:
                return data
        except Exception as exc:
            msg = str(exc)
            if "Too Many Requests" not in msg:
                print(f"(history 오류: {msg})", end=" ")
                return pd.DataFrame()
        time.sleep(pause)
    return pd.DataFrame()


def download_from_chart_api(symbol: str) -> pd.DataFrame:
    """Yahoo Finance chart API로 직접 다운로드."""
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
    period1 = 0
    period2 = int(time.time())
    session = get_http_session()
    params = {
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
        "period1": period1,
        "period2": period2,
    }
    try:
        resp = session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json().get("chart", {}).get("result")
        if not payload:
            return pd.DataFrame()
        result = payload[0]
        timestamps = result.get("timestamp")
        indicators = result.get("indicators", {})
        quote = indicators.get("quote", [{}])[0]
        adjclose = indicators.get("adjclose", [{}])[0].get("adjclose")
        if not timestamps or not quote:
            return pd.DataFrame()

        date_index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("US/Eastern").tz_localize(None)
        df = pd.DataFrame({
            "Date": date_index,
            "Open": quote.get("open"),
            "High": quote.get("high"),
            "Low": quote.get("low"),
            "Close": quote.get("close"),
            "Adj Close": adjclose,
            "Volume": quote.get("volume"),
        })
        df.sort_values("Date", inplace=True)
        df.reset_index(drop=True, inplace=True)
        for col in ["Open", "High", "Low", "Close", "Adj Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype("int64")

        events = result.get("events", {})
        dividends = {
            pd.to_datetime(v.get("date"), unit="s"): v.get("amount", 0.0)
            for v in events.get("dividends", {}).values()
        }
        splits = {}
        for v in events.get("splits", {}).values():
            num = float(v.get("numerator", 1))
            den = float(v.get("denominator", 1)) or 1.0
            splits[pd.to_datetime(v.get("date"), unit="s")] = num / den

        df["Dividends"] = df["Date"].map(dividends).fillna(0.0)
        df["Splits"] = df["Date"].map(splits).fillna(1.0)
        df.dropna(subset=["Close"], inplace=True)
        return df
    except Exception as exc:
        print(f"(chart API 오류: {exc})", end=" ")
        return pd.DataFrame()


def load_processed_tickers(path: Path) -> set[str]:
    """이미 저장된 CSV에서 처리한 티커 목록을 수집."""
    if not path.exists():
        return set()

    processed: set[str] = set()
    try:
        for chunk in pd.read_csv(path, usecols=["Ticker"], chunksize=200_000):
            processed.update(chunk["Ticker"].dropna().astype(str).str.upper())
    except Exception as exc:  # pragma: no cover - 회복용
        print(f"⚠️ 기존 파일의 티커를 읽는 중 오류 발생, 전체 재생성 진행: {exc}")
        return set()
    return processed


def write_frame(df: pd.DataFrame, path: Path, write_header: bool):
    """DataFrame을 CSV로 누적 저장."""
    # append 모드로 열어 바로 flush 되도록 보장
    with path.open("a", newline="") as handle:
        df.to_csv(handle, index=False, header=write_header, lineterminator="\n")
        handle.flush()


def main():
    tickers = fetch_sp500_tickers()

    processed = load_processed_tickers(OUTPUT_PATH)
    if processed:
        print(f"ℹ️ 기존 CSV에서 {len(processed)}개 티커 확인, 이어서 저장합니다.")
        header_needed = False
    else:
        if OUTPUT_PATH.exists():
            print(f"⚠️ 기존 파일 삭제: {OUTPUT_PATH}")
            OUTPUT_PATH.unlink()
        header_needed = True

    start = time.time()

    for idx, ticker in enumerate(tickers, start=1):
        if ticker in processed:
            if idx % 25 == 0:
                print(f"… 진행률 {idx}/{len(tickers)} (중복/스킵 포함)")
            continue

        try:
            frame = download_full_history(ticker)
            if frame.empty:
                continue
            write_frame(frame, OUTPUT_PATH, header_needed)
            header_needed = False
            processed.add(ticker)
            # 최신 진행 상황 저장
            PROGRESS_PATH.write_text(json.dumps({
                "total_tickers": len(tickers),
                "processed": sorted(processed),
                "last_ticker": ticker,
                "updated": time.time(),
            }, ensure_ascii=False, indent=2))
            time.sleep(0.4)   # 간단한 rate-limit 보호
        except Exception as exc:
            print(f"  ✗ {ticker} 오류: {exc}")

        if idx % 25 == 0:
            elapsed = time.time() - start
            print(f"… 진행률 {idx}/{len(tickers)} ({idx/len(tickers)*100:.1f}%), 경과 {elapsed/60:.1f}분")

    if PROGRESS_PATH.exists():
        PROGRESS_PATH.unlink()
    print(f"완료! 총 {len(tickers)}개 티커 저장 / 경과 {(time.time()-start)/60:.1f}분")
    print(f"결과 파일: {OUTPUT_PATH.resolve()}")


if __name__ == "__main__":
    main()
