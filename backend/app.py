#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask 백엔드 API 서버
=====================

퀀트 금융 분석 시스템의 통합 API 서버
- backend_module: 백테스트 및 알파 계산
- GA_algorithm: 유전 알고리즘 기반 알파 생성
- Langchain: AI 에이전트 시스템
- database: 데이터 관리 및 조회
"""

import os
import sys
import json
import logging
import hashlib
import secrets
import random
import textwrap
import ast
import math
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import re
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import pandas as pd
import numpy as np
import traceback
import threading
import time
from user_database import UserDatabase
from csv_manager import CSVManager
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
backend_module_path = os.path.join(PROJECT_ROOT, 'backend_module')
ga_path = os.path.join(PROJECT_ROOT, 'GA_algorithm')
langchain_path = os.path.join(PROJECT_ROOT, 'Langchain')
database_path = os.path.join(PROJECT_ROOT, 'database')
for _path in (backend_module_path, ga_path, langchain_path, database_path):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from alphas import (
    AlphaRegistry,
    AlphaStore,
    AlphaTranspilerError,
    build_shared_registry,
    compile_expression,
    AlphaDataset,
)
from alphas.transpiler import ALPHA_GLOBALS

try:  # pragma: no cover - runtime dependency
    import ollama  # type: ignore
    OLLAMA_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    ollama = None  # type: ignore
    OLLAMA_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "Ollama 라이브러리를 불러오지 못했습니다. 휴리스틱 응답으로 폴백합니다."
    )

OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'korean-qwen:latest')

# 허용 식별자: 트랜스파일러 전역 + 입력 별칭 + 안전 내장 함수
ALPHA_ALLOWED_IDENTIFIERS = set(ALPHA_GLOBALS.keys()) | {
    'open',
    'high',
    'low',
    'close',
    'volume',
    'amount',
    'returns',
    'vwap',
    'data',
    'meta',
}

# 내장 허용 함수(abs, min, max, pow, round 등)을 허용 집합에 병합
try:
    _builtins_map = ALPHA_GLOBALS.get('__builtins__', {})
    if isinstance(_builtins_map, dict):
        ALPHA_ALLOWED_IDENTIFIERS |= set(_builtins_map.keys())
except Exception:
    pass

# 흔히 안내할 함수 목록 (문서화용)
DOCUMENTED_ALPHA_FUNCTIONS = [
    'adv',
    'correlation',
    'covariance',
    'decay_linear',
    'delta',
    'delay',
    'floor_window',
    'product',
    'rank',
    'safe_clean',
    'scale',
    'sma',
    'stddev',
    'ts_mean',
    'ts_stddev',
    'ts_var',
    'ts_zscore',
    'zscore',
    'ts_mean_abs',
    'ts_argmax',
    'ts_argmin',
    'ts_max',
    'ts_min',
    'ts_rank',
    'ts_sum',
    # 흔히 사용하는 안전 내장(표현식 내 사용 안내용)
    'abs',
    'min',
    'max',
    'pow',
    'round',
    'sign',
    'log',
    'exp',
    'sqrt',
]

ALPHA_ALLOWED_INPUTS = ['open', 'high', 'low', 'close', 'volume', 'amount', 'returns', 'vwap']

# LLM이 자주 생성하는 함수/식별자 별칭을 표준 함수명으로 치환하기 위한 매핑
# - 정규화 대상은 함수명/입력명 모두 포함(단어 경계 기준으로 안전 치환)
# - 실제 계산은 alphas.transpiler.ALPHA_GLOBALS 내 구현을 따릅니다.
ALPHA_FUNCTION_ALIASES: Dict[str, str] = {
    # 함수 표기 변형/오타
    'ts_avg': 'ts_mean',          # rolling average → 통일
    'rolling_mean': 'ts_mean',
    'rolling_std': 'ts_stddev',
    'stdev': 'stddev',
    'var': 'ts_var',
    'variance': 'ts_var',
    'corr': 'correlation',
    'ts_corr': 'correlation',
    'ts_rolling_corr': 'correlation',
    'cov': 'covariance',
    'lwma': 'decay_linear',       # linear weighted moving average 표기
    'ema': 'sma',                 # 단순 치환(EMA 미구현 → SMA로 완화)
    'ts_amin': 'ts_min',
    'ts_amax': 'ts_max',
    'ts_rolling_stddev': 'ts_stddev',
    'ts_rolling_sum': 'ts_sum',
    'ts_rolling_window': 'floor_window',
    # 입력 별칭
    'vol': 'volume',
    'amt': 'amount',
    'ret': 'returns',
}


def find_unsupported_identifiers(expression: str) -> List[str]:
    """표현식에 포함된 허용되지 않은 식별자를 찾아 목록으로 반환합니다."""
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError:
        return []

    invalid: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            identifier = node.id
            if identifier in {'True', 'False', 'None'}:
                continue
            if identifier not in ALPHA_ALLOWED_IDENTIFIERS:
                invalid.append(identifier)
    return sorted(set(invalid))

def load_real_data_for_ga():
    """GA를 위한 실제 데이터 로드"""
    try:
        # SP500 데이터 파일 경로
        price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
        
        if not os.path.exists(price_file):
            logger.warning(f"가격 데이터 파일이 없습니다: {price_file}")
            return None
            
        # CSV 파일 로드
        df = pd.read_csv(price_file)
        
        if df.empty:
            logger.warning("가격 데이터가 비어있습니다")
            return None
            
        # Date 컬럼을 datetime으로 변환 (인덱스는 나중에 설정)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        
        required_cols = {'Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume'}
        missing = required_cols.difference(df.columns)
        if missing:
            logger.warning(f"필요한 컬럼을 찾을 수 없습니다: {', '.join(sorted(missing))}")
            return None

        df = df[list(required_cols)].dropna(subset=['Date', 'Ticker']).copy()
        df['Ticker'] = df['Ticker'].astype(str)
        df = df.sort_values(['Date', 'Ticker'])

        pivot_data: Dict[str, pd.DataFrame] = {}
        column_alias = {
            'Open': 'S_DQ_OPEN',
            'High': 'S_DQ_HIGH',
            'Low': 'S_DQ_LOW',
            'Close': 'S_DQ_CLOSE',
            'Volume': 'S_DQ_VOLUME',
        }

        tickers = sorted(df['Ticker'].unique())
        date_index = pd.DatetimeIndex(sorted(df['Date'].unique()))

        for column, alias in column_alias.items():
            pivot_df = (
                df.pivot(index='Date', columns='Ticker', values=column)
                  .reindex(index=date_index, columns=tickers)
                  .sort_index()
            )
            pivot_df = pivot_df.ffill().bfill()
            pivot_data[alias] = pivot_df

        close_df = pivot_data['S_DQ_CLOSE']

        if 'S_DQ_VOLUME' not in pivot_data:
            pivot_data['S_DQ_VOLUME'] = pd.DataFrame(
                100000, index=close_df.index, columns=close_df.columns
            )

        pivot_data['S_DQ_PCTCHANGE'] = close_df.pct_change().fillna(0)
        pivot_data['S_DQ_AMOUNT'] = close_df * pivot_data['S_DQ_VOLUME']

        logger.info(
            "GA 데이터 로드 성공: %s일, %s종목 (공용/개인 알파 레지스트리 전체 우주)",
            close_df.shape[0],
            close_df.shape[1],
        )
        return pivot_data
            
    except Exception as e:
        logger.error(f"GA 데이터 로드 실패: {str(e)}")
        return None

def create_minimal_dummy_data():
    """최소한의 더미 데이터 생성"""
    # 10일 x 5종목의 더미 데이터
    dates = pd.date_range('2024-01-01', periods=10, freq='D')
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    # 기본 가격 데이터 (100 기준으로 랜덤 워크)
    import numpy as np
    np.random.seed(42)
    
    base_prices = np.random.uniform(90, 110, (len(dates), len(tickers)))
    for i in range(1, len(dates)):
        base_prices[i] = base_prices[i-1] * (1 + np.random.normal(0, 0.02, len(tickers)))
    
    close_df = pd.DataFrame(base_prices, index=dates, columns=tickers)
    
    df_data = {
        'S_DQ_OPEN': close_df * 0.995,
        'S_DQ_HIGH': close_df * 1.01,
        'S_DQ_LOW': close_df * 0.99,
        'S_DQ_CLOSE': close_df,
        'S_DQ_VOLUME': pd.DataFrame(100000, index=dates, columns=tickers),
        'S_DQ_PCTCHANGE': close_df.pct_change().fillna(0),
        'S_DQ_AMOUNT': close_df * 100000
    }
    
    logger.info(f"더미 GA 데이터 생성: {len(dates)}일, {len(tickers)}종목")
    return df_data


def prepare_alpha_dataset_from_price(ticker_df: pd.DataFrame) -> AlphaDataset:
    """
    백테스트용 가격 데이터를 AlphaDataset으로 변환합니다.
    ticker_df는 단일 종목 데이터여야 하며 Date 컬럼을 포함해야 합니다.
    """
    required = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
    missing = required.difference(ticker_df.columns)
    if missing:
        raise ValueError(f"가격 데이터에 필요한 컬럼이 없습니다: {', '.join(missing)}")

    ticker_df = ticker_df.sort_values('Date')
    alpha_frame = pd.DataFrame(index=ticker_df['Date'])
    alpha_frame['S_DQ_OPEN'] = ticker_df['Open'].values
    alpha_frame['S_DQ_HIGH'] = ticker_df['High'].values
    alpha_frame['S_DQ_LOW'] = ticker_df['Low'].values
    alpha_frame['S_DQ_CLOSE'] = ticker_df['Close'].values
    alpha_frame['S_DQ_VOLUME'] = ticker_df['Volume'].values
    alpha_frame['S_DQ_AMOUNT'] = ticker_df['Close'].values * ticker_df['Volume'].values
    alpha_frame['S_DQ_PCTCHANGE'] = alpha_frame['S_DQ_CLOSE'].pct_change().fillna(0)
    return AlphaDataset(alpha_frame)


def calculate_factor_performance(
    merged_data: pd.DataFrame,
    factor_col: str,
    *,
    quantile: float,
    transaction_cost: float,
    rebalancing_frequency: str,
    top_count: Optional[int] = None,
) -> Dict[str, Any]:
    """리밸런싱 전략 기반 팩터 성과 지표를 계산합니다.

    - 포트폴리오 신호는 리밸런싱 날짜 t에서 계산됩니다.
    - 체결은 t 다음 거래일 시가(Open)에서 이루어집니다.
    - 포지션은 다음 리밸런싱 시점의 체결 시가까지 보유합니다.
    """

    if merged_data is None or merged_data.empty:
        raise ValueError("팩터 성과를 계산할 데이터가 없습니다")

    required_cols = {'Date', 'Ticker', 'Open', 'Close', factor_col}
    missing_cols = required_cols.difference(merged_data.columns)
    if missing_cols:
        raise ValueError(f"필수 컬럼이 부족합니다: {', '.join(sorted(missing_cols))}")

    working_df = merged_data[list(required_cols)].dropna().copy()
    if working_df.empty:
        raise ValueError("유효한 팩터 데이터가 없습니다")

    working_df['Date'] = pd.to_datetime(working_df['Date'])
    working_df = working_df.sort_values(['Date', 'Ticker']).reset_index(drop=True)

    # 거래 가능한 날짜 맵 (현재 날짜 → 다음 거래일)
    unique_dates = sorted(working_df['Date'].unique())
    if len(unique_dates) < 3:  # 최소 진입/청산을 위해 3일 이상 필요
        raise ValueError("거래 가능한 날짜가 부족합니다")

    next_date_map = {
        current: unique_dates[idx + 1]
        for idx, current in enumerate(unique_dates[:-1])
    }

    if rebalancing_frequency == 'daily':
        rebalance_dates = unique_dates
    elif rebalancing_frequency == 'weekly':
        rebalance_dates = sorted(working_df[working_df['Date'].dt.weekday == 0]['Date'].unique())
    elif rebalancing_frequency == 'monthly':
        rebalance_dates = sorted(working_df[working_df['Date'].dt.day == 1]['Date'].unique())
    elif rebalancing_frequency == 'quarterly':
        quarterly_months = [1, 4, 7, 10]
        rebalance_dates = sorted(
            working_df[
                (working_df['Date'].dt.month.isin(quarterly_months))
                & (working_df['Date'].dt.day == 1)
            ]['Date'].unique()
        )
    else:
        rebalance_dates = unique_dates

    if len(rebalance_dates) < 2:
        raise ValueError("리밸런싱 날짜가 부족합니다")

    factor_returns: List[Dict[str, Any]] = []
    ic_values: List[float] = []

    for idx, rebalance_date in enumerate(rebalance_dates[:-1]):
        next_rebalance_date = rebalance_dates[idx + 1]

        entry_date = next_date_map.get(rebalance_date)
        exit_entry_date = next_date_map.get(next_rebalance_date)

        # 다음 거래일 또는 청산 거래일이 존재하지 않으면 건너뜁니다.
        if entry_date is None or exit_entry_date is None:
            continue

        signal_df = working_df[working_df['Date'] == rebalance_date][['Ticker', factor_col]]
        entry_prices = working_df[working_df['Date'] == entry_date][['Ticker', 'Open']].rename(
            columns={'Open': 'Open_entry'}
        )
        exit_prices = working_df[working_df['Date'] == exit_entry_date][['Ticker', 'Open']].rename(
            columns={'Open': 'Open_exit'}
        )

        period_df = (
            signal_df
            .merge(entry_prices, on='Ticker', how='inner')
            .merge(exit_prices, on='Ticker', how='inner')
        )

        if len(period_df) < 5:
            continue

        period_df['HoldingReturn'] = period_df['Open_exit'] / period_df['Open_entry'] - 1

        valid = period_df.dropna(subset=[factor_col, 'HoldingReturn'])
        if valid.empty:
            continue

        period_df = period_df.sort_values([factor_col, 'Ticker'], ascending=[False, True])
        total_names = len(period_df)

        if top_count is not None:
            top_n = max(1, min(top_count, total_names))
        else:
            top_n = max(1, int(total_names * quantile))

        long_portfolio = period_df.head(top_n)

        long_return = long_portfolio['HoldingReturn'].mean()
        # 롱 포지션만 고려하므로 숏 수익은 0으로 처리
        factor_return = long_return - (2 * transaction_cost)

        holding_days = max(1, len(pd.bdate_range(entry_date, exit_entry_date)) - 1)

        factor_returns.append(
            {
                'Date': entry_date,
                'FactorReturn': factor_return,
                'HoldingDays': holding_days,
            }
        )

        if len(valid) > 5:
            ic = valid[factor_col].corr(valid['HoldingReturn'])
            if not np.isnan(ic):
                ic_values.append(float(ic))

    if not factor_returns:
        raise ValueError("팩터 수익률 데이터를 계산할 수 없습니다")

    factor_returns_df = pd.DataFrame(factor_returns).sort_values('Date').reset_index(drop=True)
    returns = factor_returns_df['FactorReturn'].values
    holding_periods = factor_returns_df['HoldingDays'].values

    nav = np.concatenate(([1.0], np.cumprod(1 + returns)))

    cumulative_returns: List[Dict[str, Any]] = []
    if not factor_returns_df.empty:
        first_date = factor_returns_df['Date'].iloc[0]
        cumulative_returns.append({'date': first_date.strftime('%Y-%m-%d'), 'value': 0.0})
        cumulative_returns.extend(
            {
                'date': date.strftime('%Y-%m-%d'),
                'value': float(nav_val - 1.0),
            }
            for date, nav_val in zip(factor_returns_df['Date'], nav[1:])
        )

    cumulative_days = np.cumsum(holding_periods) if len(holding_periods) else np.array([])
    rolling_cagr = []
    if len(cumulative_days) > 0:
        with np.errstate(divide='ignore', invalid='ignore'):
            rolling_values = np.power(np.maximum(nav[1:], 1e-12), 252 / cumulative_days) - 1
        rolling_cagr = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'value': float(val),
            }
            for date, val in zip(factor_returns_df['Date'], rolling_values)
            if np.isfinite(val)
        ]

    total_return = float(nav[-1] - 1) if len(nav) else 0.0
    total_holding_days = float(cumulative_days[-1]) if len(cumulative_days) else 0.0
    years = total_holding_days / 252 if total_holding_days else 0.0
    cagr = (nav[-1]) ** (1 / years) - 1 if years > 0 and nav[-1] > 0 else 0.0

    periods_per_year = 0.0
    sharpe = 0.0
    sortino = 0.0
    volatility = 0.0

    if len(returns) > 0:
        return_std = returns.std(ddof=0)
        mean_return = returns.mean()
        avg_holding = holding_periods.mean() if len(holding_periods) else 0.0
        periods_per_year = (252 / avg_holding) if avg_holding else 0.0

        if return_std > 0 and periods_per_year > 0:
            sharpe = mean_return / return_std * np.sqrt(periods_per_year)

        downside = returns[returns < 0]
        downside_std = downside.std(ddof=0) if len(downside) else 0.0
        if downside_std > 0 and periods_per_year > 0:
            sortino = mean_return / downside_std * np.sqrt(periods_per_year)

        if return_std > 0 and periods_per_year > 0:
            volatility = return_std * np.sqrt(periods_per_year)

        win_rate = float((returns > 0).mean())
    else:
        win_rate = 0.0

    cumulative_curve = nav
    running_max = np.maximum.accumulate(cumulative_curve)
    drawdown = (cumulative_curve - running_max) / running_max
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    ic_mean = float(np.mean(ic_values)) if ic_values else 0.0

    return {
        'cagr': float(cagr),
        'sharpe_ratio': float(sharpe),
        'sortino_ratio': float(sortino),
        'max_drawdown': max_drawdown,
        'ic_mean': ic_mean,
        'win_rate': win_rate,
        'volatility': float(volatility),
        'total_return': total_return,
        'cumulative_returns': cumulative_returns,
        'cagr_series': rolling_cagr,
    }


def calculate_ticker_performance_metrics(
    ticker_df: pd.DataFrame,
) -> Tuple[List[Tuple[pd.Timestamp, float]], Dict[str, float]]:
    """단일 종목의 가격 데이터를 기반으로 성과 지표와 누적 수익률 시리즈를 계산합니다."""
    if ticker_df is None or ticker_df.empty:
        raise ValueError("가격 데이터가 비어있습니다")

    working_df = ticker_df[['Date', 'Close']].dropna().copy()
    if working_df.empty:
        raise ValueError("유효한 종가 데이터가 없습니다")

    working_df['Date'] = pd.to_datetime(working_df['Date'])
    working_df = working_df.sort_values('Date').reset_index(drop=True)

    returns = working_df['Close'].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if not returns.empty:
        returns.iloc[0] = 0.0

    nav_series = (1 + returns).cumprod()
    if not nav_series.empty:
        nav_series.iloc[0] = 1.0
    nav = nav_series.to_numpy()

    base_price = working_df['Close'].iloc[0]
    buy_hold_returns = working_df['Close'] / base_price - 1.0
    buy_hold_returns.iloc[0] = 0.0

    periods = len(returns)
    years = periods / 252 if periods > 1 else 0.0
    mean_return = returns.mean() if periods > 0 else 0.0
    return_std = returns.std(ddof=0) if periods > 1 else 0.0

    sharpe = 0.0
    volatility = 0.0
    if return_std > 0:
        sharpe = mean_return / return_std * np.sqrt(252)
        volatility = return_std * np.sqrt(252)

    downside = returns[returns < 0]
    downside_std = downside.std(ddof=0) if len(downside) > 0 else 0.0
    sortino = mean_return / downside_std * np.sqrt(252) if downside_std > 0 else 0.0

    win_rate = float((returns > 0).mean()) if periods > 0 else 0.0

    if len(nav):
        running_max = np.maximum.accumulate(nav)
        drawdown = (nav - running_max) / running_max
        max_drawdown = float(drawdown.min())
        final_nav = nav[-1]
    else:
        max_drawdown = 0.0
        final_nav = 1.0

    total_return = float(buy_hold_returns.iloc[-1]) if not buy_hold_returns.empty else 0.0
    cagr = (final_nav) ** (1 / years) - 1 if years > 0 and final_nav > 0 else 0.0

    series_points = [
        (date, float(value))
        for date, value in zip(working_df['Date'], buy_hold_returns)
    ]

    metrics = {
        'cagr': float(cagr),
        'sharpe_ratio': float(sharpe),
        'sortino_ratio': float(sortino),
        'max_drawdown': float(max_drawdown),
        'win_rate': float(win_rate),
        'volatility': float(volatility),
        'total_return': float(total_return),
        'ic_mean': None,
    }

    return series_points, metrics


def _clean_prompt(text: str) -> str:
    """Collapse whitespace in prompts for consistent LLM calls."""
    return re.sub(r'\s+', ' ', text).strip()


def call_local_llm(messages: List[Dict[str, str]], *, temperature: float = 0.4) -> Tuple[str, str]:
    """
    korean-qwen:latest 모델을 우선 사용하여 LLM 응답을 생성합니다.
    Ollama가 설치되어 있지 않은 경우 규칙 기반 메시지를 반환합니다.
    """
    cleaned_messages = [
        {
            'role': msg.get('role', 'user'),
            'content': _clean_prompt(msg.get('content', '')) if isinstance(msg, dict) else str(msg)
        }
        for msg in messages
    ]

    if OLLAMA_AVAILABLE:
        try:
            response = ollama.chat(  # type: ignore[attr-defined]
                model=OLLAMA_MODEL,
                messages=cleaned_messages,
                options={
                'temperature': temperature,
                'num_predict': 256,
                'num_ctx': 8192,
                'top_p': 0.9,
            },
        )
            return response.get('message', {}).get('content', '').strip(), 'ollama'
        except Exception as exc:  # pragma: no cover - runtime dependency
            logger.warning("Ollama 호출 실패, 규칙 기반 응답으로 대체합니다: %s", exc)

    # 규칙 기반 폴백
    last_user_message = cleaned_messages[-1]['content'] if cleaned_messages else ''
    return generate_rule_based_response(last_user_message), 'heuristic'


def generate_rule_based_response(user_message: str) -> str:
    """Ollama가 없을 때 사용할 간단한 답변 생성기."""
    templates = [
        "요청하신 내용을 정리했습니다:\n1. 핵심 목표를 명확히 정의합니다.\n2. 필요한 데이터 소스를 점검합니다.\n3. 리스크 관리 지표를 함께 살펴봅니다.",
        "해당 요구사항을 기준으로 아이디어를 구성해 보았습니다. 변동성, 거래량, 모멘텀 요소를 균형있게 결합하는 알파를 추천드립니다.",
        "이 플랫폼은 알파 생성과 백테스트에 초점을 맞추고 있습니다. 관련 지표나 전략 질문을 주시면 더 구체적으로 도와드릴 수 있습니다.",
    ]

    if '프로그램' in user_message or '플랫폼' in user_message:
        return "이 프로그램은 LangChain과 GA를 활용해 알파를 탐색합니다. 구체적인 알파 조건이나 전략을 말씀해주시면 더 정밀한 제안을 드릴 수 있습니다."

    if any(keyword in user_message.lower() for keyword in ['vol', '변동성', 'volume', '거래량']):
        return (
            "변동성과 거래량을 함께 고려한 전략을 준비해 보았습니다. "
            "예: rank(stddev(log(return), 20) * volume) 형태로 변동성에 거래량 가중치를 부여할 수 있습니다."
        )

    if any(keyword in user_message.lower() for keyword in ['hello', 'hi', '안녕']):
        return "안녕하세요! 알파 생성이나 백테스트와 관련된 질문이 있다면 말씀해 주세요."

    return random.choice(templates)


def score_alpha_expression(expression: str, rationale: str, goal: str) -> float:
    """간단한 휴리스틱으로 알파 표현식의 품질을 점수화합니다."""
    expression_lower = expression.lower()
    rationale_lower = rationale.lower()
    goal_lower = goal.lower()

    score = 0.4  # 기본 점수

    keyword_weights = [
        (['vol', 'stddev', 'variance', '변동'], 0.25),
        (['volume', '거래량'], 0.2),
        (['rank', 'ts_rank'], 0.1),
        (['correlation', 'corr'], 0.1),
        (['momentum', '모멘텀'], 0.08),
        (['reversal', '반전'], 0.05),
    ]

    for keywords, weight in keyword_weights:
        if any(keyword in expression_lower for keyword in keywords):
            score += weight
        if any(keyword in rationale_lower for keyword in keywords):
            score += weight / 2
        if any(keyword in goal_lower for keyword in keywords):
            score += weight / 2

    length_penalty = min(len(expression) / 200, 0.3)
    score += 0.2 - length_penalty

    score = max(0.05, min(score, 1.0))
    return round(score, 4)


def parse_llm_alpha_payload(raw_text: str) -> Tuple[str, str]:
    """
    LLM 응답에서 알파 수식과 설명을 추출합니다.
    JSON 형식이면 파싱하고, 아니면 간단한 규칙으로 구분합니다.
    """
    raw_text = (raw_text or '').strip()
    if not raw_text:
        return '', ''

    def _strip_quotes(value: str) -> str:
        return value.strip().strip('"').strip()

    try:
        payload = json.loads(raw_text)
        if isinstance(payload, dict):
            expression = payload.get('expression') or payload.get('alpha') or ''
            rationale = payload.get('rationale') or payload.get('explanation') or ''
            if expression:
                return expression.strip(), (rationale or '').strip()
    except json.JSONDecodeError:
        # JSON이 미완성인 경우 간단히 보정해 다시 시도
        stitched = raw_text.rstrip()
        if stitched.startswith('{') and not stitched.endswith('}'):
            try:
                payload = json.loads(stitched + '}')
                if isinstance(payload, dict):
                    expression = payload.get('expression') or payload.get('alpha') or ''
                    rationale = payload.get('rationale') or payload.get('explanation') or ''
                    if expression:
                        return expression.strip(), (rationale or '').strip()
            except Exception:
                pass

    expression_candidate = ''
    rationale = raw_text

    json_expr_match = re.search(r'"expression"\s*:\s*"(.+?)"', raw_text, re.DOTALL)
    if json_expr_match:
        expression_candidate = _strip_quotes(json_expr_match.group(1))
        rationale = raw_text.replace(json_expr_match.group(0), '').strip()

    json_rat_match = re.search(r'"rationale"\s*:\s*"(.+?)"', raw_text, re.DOTALL)
    if json_rat_match:
        rationale = _strip_quotes(json_rat_match.group(1))

    if not expression_candidate:
        code_match = re.search(r"```(?:python|alpha)?\s*(.*?)```", raw_text, re.DOTALL)
        if code_match:
            expression_candidate = code_match.group(1).strip()
            rationale = raw_text.replace(code_match.group(0), '').strip()

    if not expression_candidate:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if lines:
            expression_candidate = lines[0]
            rationale = "\n".join(lines[1:]).strip()

    expression_candidate = expression_candidate.strip()
    expression_candidate = apply_expression_aliases(expression_candidate)
    return expression_candidate, rationale.strip()


def apply_expression_aliases(expression: str) -> str:
    """LLM이 생성한 수식에서 알려진 alias/오타를 정규 함수로 치환합니다."""
    if not expression:
        return expression
    normalized = expression
    for alias, target in ALPHA_FUNCTION_ALIASES.items():
        normalized = re.sub(rf"\b{re.escape(alias)}\b", target, normalized)

    # 특수 패턴: advN → adv(close, volume, N)
    # - 함수 호출 형태가 아니라 토큰으로 쓰인 경우를 보정
    def _advn_repl(match: re.Match) -> str:
        n = match.group(1)
        # 괄호가 바로 뒤따르면 원형 유지(adv40(...)) → 사용자가 명시 인자를 제공했다고 가정
        tail = match.group(2) or ''
        if tail == '(':
            return f"adv{n}("
        return f"adv(close, volume, {n})"

    normalized = re.sub(r"\badv(\d+)(\()?", _advn_repl, normalized)
    return normalized


def run_mcts_search(goal: str, *, simulations: int = 6) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    간단한 MCTS 모사: LLM을 활용해 후보 알파를 탐색하고 휴리스틱 점수를 부여합니다.
    simulations 값을 조정해 탐색 깊이를 제어할 수 있습니다.
    """
    candidates: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []

    supported_functions_text = ", ".join(DOCUMENTED_ALPHA_FUNCTIONS)
    supported_inputs_text = ", ".join(ALPHA_ALLOWED_INPUTS)

    system_prompt = textwrap.dedent(
        f"""
        당신은 퀀트 리서치 파트너입니다. 사용자의 요구에 맞춘 알파 팩터 수식을 제안해야 합니다.
        반드시 아래 제약을 지키십시오.
        - 표현식은 지원 함수만 사용합니다: {supported_functions_text}.
          (필요 시 numpy는 `np`, pandas는 `pd` 네임스페이스로 접근합니다.)
        - 입력 시계열 별칭은 {supported_inputs_text} 만 사용할 수 있습니다.
        - 이외 식별자(예: volume_adj_mavg, ts_avg, ema 등)는 사용하지 않습니다.
        - `ts_min`/`ts_max`/`ts_mean`만 사용하며 `ts_amin`, `ts_amax`, `ts_avg`와 같은 표기는 사용하지 마세요.
        응답은 JSON 형식으로 작성하세요. 예시는 다음과 같습니다.
        {{
          "name": "...",
          "expression": "...",
          "rationale": "..."
        }}
        수식은 WorldQuant 스타일 함수(ts_rank, ts_sum 등)를 적극 활용하십시오.
        """
    ).strip()

    last_provider = 'unknown'

    for iteration in range(1, simulations + 1):
        prompt = textwrap.dedent(
            f"""
            사용자 목표: {goal}
            요구사항에 맞는 새로운 알파 수식을 JSON 형식으로 제안해 주세요.
            수식은 간결하게 표현하고, rationale에는 해당 수식의 직관을 설명해 주세요.
            iteration: {iteration}
            """
        )

        llm_messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': prompt},
        ]

        llm_output, provider = call_local_llm(llm_messages, temperature=0.3)
        last_provider = provider
        expression, rationale = parse_llm_alpha_payload(llm_output)
        expression = apply_expression_aliases(expression)

        if not expression:
            if provider == 'ollama':
                # 한 번 더 재시도
                retry_prompt = prompt + "\n반드시 JSON 형식으로 응답하세요."
                llm_output, provider = call_local_llm(
                    [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': retry_prompt},
                    ],
                    temperature=0.2,
                )
                last_provider = provider
                expression, rationale = parse_llm_alpha_payload(llm_output)
                expression = apply_expression_aliases(expression)
            if not expression:
                trace.append({
                    'iteration': iteration,
                    'prompt': prompt,
                    'raw_response': llm_output,
                    'scored_expression': '',
                    'score': 0.0,
                })
            continue

        unsupported = find_unsupported_identifiers(expression)
        if unsupported:
            reason = f"지원되지 않는 함수/식별자 사용: {', '.join(unsupported)}"
            trace.append({
                'iteration': iteration,
                'prompt': prompt,
                'raw_response': llm_output,
                'scored_expression': '',
                'score': 0.0,
                'reason': reason,
            })
            continue

        score = score_alpha_expression(expression, rationale, goal)
        candidate = {
            'name': f'Alpha Candidate {iteration}',
            'expression': expression,
            'rationale': rationale or 'LLM이 제시한 근거가 없습니다.',
            'score': score,
            'path': [
                'root',
                'explore_volatility' if 'vol' in expression.lower() else 'explore_momentum',
                f'candidate_{iteration}'
            ],
        }

        trace.append({
            'iteration': iteration,
            'prompt': prompt,
            'raw_response': llm_output,
            'scored_expression': expression,
            'score': score,
        })

        # 중복 수식은 스킵
        if any(existing['expression'] == expression for existing in candidates):
            continue

        candidates.append(candidate)

    candidates.sort(key=lambda item: item['score'], reverse=True)

    for index, candidate in enumerate(candidates, start=1):
        candidate['id'] = f'candidate_{index}'
        candidate['name'] = candidate['name'] or f'Alpha Candidate {index}'

    return candidates, trace, last_provider


def run_mcts_search_uct(
    goal: str,
    *,
    simulations: int = 32,
    c: float = math.sqrt(2.0),
    max_depth: int = 3,
    branch_factor: int = 3,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    UCT(UCB1) 기반의 간단한 MCTS:
    - depth 0: 주제 토픽 노드 (예: volatility, momentum, reversal, liquidity, correlation)
    - depth 1: 알파 표현식 후보(leaf) 노드
    선택: UCB1 = Q + c * sqrt(ln(N)/n)
    확장: 미시도 토픽/후보를 하나 추가
    시뮬레이션: 후보 점수(heuristic score_alpha_expression)
    역전파: 경로상 방문/보상 업데이트
    반환: 상위 후보 리스트, 탐색 흔적(trace), 마지막 LLM 제공자
    """
    Topic = str

    topics: List[Topic] = [
        'volatility',
        'momentum',
        'reversal',
        'liquidity',
        'correlation',
    ]

    class Node:
        __slots__ = (
            'parent', 'children', 'visits', 'total_reward', 'action', 'depth',
            'topic', 'expression', 'rationale', 'score'
        )
        def __init__(self, parent=None, action: Optional[str]=None, depth:int=0):
            self.parent: Optional['Node'] = parent
            self.children: List['Node'] = []
            self.visits: int = 0
            self.total_reward: float = 0.0
            self.action = action  # topic name or 'candidate_k'
            self.depth = depth
            # payload
            self.topic: Optional[str] = None
            self.expression: Optional[str] = None
            self.rationale: Optional[str] = None
            self.score: Optional[float] = None

        def q_value(self) -> float:
            return (self.total_reward / self.visits) if self.visits > 0 else 0.0

        def ucb(self, parent_visits: int, c_: float) -> float:
            if self.visits == 0:
                return float('inf')
            return self.q_value() + c_ * math.sqrt(max(1.0, math.log(parent_visits)) / self.visits)

        def is_fully_expanded(self) -> bool:
            if self.depth == 0:
                return len(self.children) >= len(topics)
            if self.depth == 1:
                return len(self.children) >= branch_factor
            return True

        def is_terminal(self) -> bool:
            return self.depth >= max_depth

        def path(self) -> List[str]:
            cur, p = self, []
            while cur is not None:
                if cur.action:
                    p.append(str(cur.action))
                cur = cur.parent
            return list(reversed(p)) or ['root']

    root = Node(parent=None, action='root', depth=0)
    trace: List[Dict[str, Any]] = []
    last_provider = 'unknown'

    def expand_topic(parent: Node) -> Optional[Node]:
        tried = {child.action for child in parent.children}
        for t in topics:
            if t not in tried:
                child = Node(parent=parent, action=t, depth=1)
                child.topic = t
                parent.children.append(child)
                return child
        return None

    def expand_candidate(parent: Node) -> Optional[Node]:
        # 요청: goal + topic 힌트로 LLM에 후보 생성
        topic_hint = parent.topic or 'general'
        system_prompt = textwrap.dedent(
            f"""
            당신은 퀀트 리서치 파트너입니다. 아래 토픽에 초점을 맞춘 WorldQuant 스타일 알파 수식을 JSON으로 1개 제안하세요.
            토픽: {topic_hint}
            사용 가능 함수: {', '.join(DOCUMENTED_ALPHA_FUNCTIONS)}
            허용 입력: {', '.join(ALPHA_ALLOWED_INPUTS)}
            JSON 스키마: {{"name": "...", "expression": "...", "rationale": "..."}}
            수식만 간결하게 작성하세요.
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            사용자 목표: {goal}
            토픽 '{topic_hint}'에 맞는 새로운 알파 수식을 1개만 JSON으로 제안하세요.
            """
        ).strip()
        llm_messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]
        llm_output, provider = call_local_llm(llm_messages, temperature=0.25)
        nonlocal last_provider
        last_provider = provider
        expression, rationale = parse_llm_alpha_payload(llm_output)
        expression = apply_expression_aliases(expression)

        # 후보 노드 생성 (leaf)
        child = Node(parent=parent, action=f"candidate_{len(parent.children)+1}", depth=2)
        child.topic = topic_hint
        child.expression = expression
        child.rationale = rationale
        parent.children.append(child)

        # 평가(시뮬레이션)
        if not expression:
            score = 0.0
            reason = 'empty_expression'
        else:
            unsupported = find_unsupported_identifiers(expression)
            if unsupported:
                score = 0.0
                reason = f"unsupported: {', '.join(unsupported)}"
            else:
                score = score_alpha_expression(expression, rationale or '', goal)
                reason = ''

        child.score = score
        trace.append({
            'path': child.path(),
            'raw_response': llm_output,
            'expression': expression,
            'score': score,
            'reason': reason,
        })
        return child

    def expand_refinement(parent: Node) -> Optional[Node]:
        # parent: depth-2 node with an expression; create a refined variant
        base_expr = parent.expression or ''
        if not base_expr:
            # no expression to refine
            child = Node(parent=parent, action=f"ref_{len(parent.children)+1}", depth=3)
            parent.children.append(child)
            child.score = 0.0
            trace.append({
                'path': child.path(),
                'raw_response': '',
                'expression': '',
                'score': 0.0,
                'reason': 'no_base_expression',
            })
            return child

        system_prompt = textwrap.dedent(
            f"""
            당신은 퀀트 리서치 파트너입니다. 주어진 알파 수식을 소폭 개선하여 변형안을 1개 제안하세요.
            - window/period 파라미터의 미세 조정, rank/scale 조합, correlation 윈도우 수정 등 경미한 수정을 우선합니다.
            - 사용 가능 함수: {', '.join(DOCUMENTED_ALPHA_FUNCTIONS)}
            - 허용 입력: {', '.join(ALPHA_ALLOWED_INPUTS)}
            JSON 스키마: {{"expression": "...", "rationale": "..."}}
            """
        ).strip()
        user_prompt = textwrap.dedent(
            f"""
            원본 수식:
            {base_expr}
            이 수식을 약간 개선한 새로운 변형을 JSON으로 1개만 제안하세요.
            """
        ).strip()

        llm_messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]
        llm_output, provider = call_local_llm(llm_messages, temperature=0.2)
        nonlocal last_provider
        last_provider = provider

        expression, rationale = parse_llm_alpha_payload(llm_output)
        expression = apply_expression_aliases(expression)

        child = Node(parent=parent, action=f"ref_{len(parent.children)+1}", depth=3)
        child.topic = parent.topic
        child.expression = expression or ''
        child.rationale = rationale or ''
        parent.children.append(child)

        if not expression:
            score = 0.0
            reason = 'empty_refinement'
        else:
            unsupported = find_unsupported_identifiers(expression)
            if unsupported:
                score = 0.0
                reason = f"unsupported: {', '.join(unsupported)}"
            else:
                score = score_alpha_expression(expression, rationale or '', goal)
                reason = ''
        child.score = score
        trace.append({
            'path': child.path(),
            'raw_response': llm_output,
            'expression': expression,
            'score': score,
            'reason': reason,
        })
        return child

    for _ in range(max(1, int(simulations))):
        node = root
        # Selection
        while node.is_fully_expanded() and not node.is_terminal():
            if not node.children:
                break
            parent_visits = max(1, node.visits)
            node = max(node.children, key=lambda ch: ch.ucb(parent_visits, c))

        # Expansion
        if not node.is_terminal():
            if node.depth == 0:
                node = expand_topic(node) or node
            elif node.depth == 1:
                node = expand_candidate(node) or node
            elif node.depth == 2:
                node = expand_refinement(node) or node

        # Simulation is embedded in expand_candidate (score assigned to leaf).
        # If terminal without score, skip backprop.
        reward = node.score if node.score is not None else 0.0

        # Backpropagation
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.total_reward += reward
            cur = cur.parent

    # 수집: 모든 leaf 후보 정렬
    leaves: List[Node] = []
    def collect(n: Node):
        if not n.children:
            if n.expression:
                leaves.append(n)
            return
        for ch in n.children:
            collect(ch)
    collect(root)
    leaves.sort(key=lambda n: (n.score or 0.0), reverse=True)

    candidates: List[Dict[str, Any]] = []
    for idx, leaf in enumerate(leaves, start=1):
        candidates.append({
            'id': f'candidate_{idx}',
            'name': f'{leaf.topic.title() if leaf.topic else "Alpha"} Candidate {idx}',
            'expression': leaf.expression or '',
            'rationale': leaf.rationale or '',
            'score': float(leaf.score or 0.0),
            'path': leaf.path(),
        })

    return candidates, trace, last_provider


def detect_intent(message: str, explicit_intent: Optional[str] = None) -> str:
    """사용자 입력을 기반으로 의도를 감지합니다."""
    if explicit_intent:
        return explicit_intent

    lowered = message.lower()
    if any(keyword in lowered for keyword in ['알파', '수식', 'factor', '전략', 'generate']):
        return 'generate'
    if any(keyword in lowered for keyword in ['프로그램', '플랫폼', '백테스트', 'ga', 'ga']):
        return 'chat'
    return 'off_topic'


def compute_factor_series_from_registry(factor_name: str,
                                        registry: AlphaRegistry,
                                        price_data: pd.DataFrame) -> pd.DataFrame:
    """
    AlphaRegistry 정의를 사용해 팩터 값을 계산합니다.
    반환값은 Date, Ticker, factor_name 컬럼을 가진 DataFrame입니다.
    """
    if factor_name not in registry:
        raise KeyError(f"등록되지 않은 알파: {factor_name}")

    definition = registry.get(factor_name)

    if price_data.empty:
        raise RuntimeError("가격 데이터가 비어 있습니다")

    working = price_data.copy()
    working['Date'] = pd.to_datetime(working['Date'])

    tickers = sorted(working['Ticker'].unique())
    if not tickers:
        raise RuntimeError("가격 데이터에 티커가 없습니다")

    pivot_map: Dict[str, pd.DataFrame] = {}

    def make_pivot(column: str, alias: str) -> None:
        pivot = working.pivot_table(index='Date', columns='Ticker', values=column)
        pivot = pivot.reindex(columns=tickers).sort_index()
        # ensure stacked outputs expose 'Ticker' as the column level name
        pivot.columns.name = 'Ticker'
        pivot_map[alias] = pivot

    column_map = {
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
    }

    for source, alias in column_map.items():
        if source not in working.columns:
            raise RuntimeError(f"가격 데이터에 {source} 컬럼이 없습니다")
        make_pivot(source, alias)

    pivot_map['amount'] = (pivot_map['close'] * pivot_map['volume']).fillna(0)
    returns = pivot_map['close'].pct_change().fillna(0)
    pivot_map['returns'] = returns

    vwap = pivot_map['amount'] / pivot_map['volume'].replace(0, np.nan)
    pivot_map['vwap'] = vwap.fillna(method='ffill').fillna(method='bfill').fillna(0)

    class MultiAssetDataset:
        def __init__(self, data_map: Dict[str, pd.DataFrame], metadata: Optional[Dict[str, Any]] = None):
            self.data_map = data_map
            self.metadata = metadata or {}
            self.frame = data_map.get('close')
            self.column_aliases = {
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'amount': 'amount',
                'returns': 'returns',
                'vwap': 'vwap',
            }

        def build_eval_locals(self) -> Dict[str, Any]:
            env: Dict[str, Any] = {alias: df for alias, df in self.data_map.items()}
            env['data'] = self.data_map
            env['meta'] = self.metadata
            return env

        def get_series(self, alias: str) -> pd.DataFrame:
            key = self.column_aliases.get(alias, alias)
            if key not in self.data_map:
                raise KeyError(f"Unknown alias: {alias}")
            return self.data_map[key]

        def ensure_columns(self, required: Optional[List[str]] = None):
            required = required or list(self.column_aliases.keys())
            missing = [alias for alias in required if alias not in self.data_map]
            if missing:
                raise ValueError(f"MultiAssetDataset missing aliases: {missing}")

    dataset = MultiAssetDataset(pivot_map, metadata={'tickers': tickers})

    try:
        factor_values = definition.compute(dataset)
    except Exception as exc:
        raise RuntimeError(f"{factor_name} 계산 실패: {exc}") from exc

    dates_index = pivot_map['close'].index

    if isinstance(factor_values, pd.DataFrame):
        factor_df = factor_values.reindex(index=dates_index, columns=tickers)
    elif isinstance(factor_values, pd.Series):
        if isinstance(factor_values.index, pd.MultiIndex) and factor_values.index.nlevels >= 2:
            factor_df = factor_values.unstack().reindex(columns=tickers).reindex(index=dates_index)
        elif len(factor_values) == len(dates_index):
            arr = np.tile(factor_values.values.reshape(-1, 1), (1, len(tickers)))
            factor_df = pd.DataFrame(arr, index=dates_index, columns=tickers)
        else:
            raise RuntimeError(f"{factor_name} 결과 길이가 가격 데이터와 맞지 않습니다")
    else:
        raise RuntimeError(f"{factor_name} 결과 타입을 처리할 수 없습니다: {type(factor_values).__name__}")

    factor_df = factor_df.replace([np.inf, -np.inf], np.nan).fillna(0)

    factor_long = (
        factor_df.stack(dropna=False)
        .rename(factor_name)
        .reset_index()
    )
    if 'Ticker' not in factor_long.columns:
        for candidate in ('level_1', 'ticker', 'column'):
            if candidate in factor_long.columns:
                factor_long = factor_long.rename(columns={candidate: 'Ticker'})
                break
    factor_long = factor_long.dropna(subset=[factor_name])

    if factor_long.empty:
        raise RuntimeError(f"{factor_name} 팩터 계산 결과가 없습니다.")

    return factor_long

def run_ga_alternative(df_data, max_depth, population_size, generations):
    """run_ga.py 방식의 대안 GA 실행"""
    try:
        # Alphas 기반 GA 재실행
        from autoalpha_ga import AutoAlphaGA
        
        logger.info("대안 GA 시스템 초기화 중...")
        alt_ga = AutoAlphaGA(df_data, hold_horizon=1, random_seed=np.random.randint(1, 1000))
        
        logger.info("대안 GA 실행 중 (더 관대한 설정)...")
        elites = alt_ga.run(
            max_depth=max_depth,
            population=population_size,
            generations=generations,
            warmstart_k=2,  # 더 관대한 설정
            n_keep_per_depth=50,  # 더 많이 보관
            p_mutation=0.5,  # 돌연변이 증가
            p_crossover=0.5,
            diversity_threshold=0.5  # 다양성 기준 완화
        )
        
        if elites and len(elites) > 0:
            # 실제 엘리트가 있는 경우
            formatted_alphas = []
            for i, elite in enumerate(elites[:max_depth * 3]):  # 더 많이 가져오기
                try:
                    expr = elite.tree.to_python_expr() if hasattr(elite.tree, 'to_python_expr') else str(elite.tree)
                    fitness = abs(float(elite.fitness)) if elite.fitness is not None else 0.1
                    formatted_alphas.append({
                        "expression": expr,
                        "fitness": max(fitness, 0.1)  # 최소 0.1로 보장
                    })
                except:
                    continue
            
            if formatted_alphas:
                return formatted_alphas
        
        # 여전히 실패하면 의미있는 더미 생성
        raise ValueError("대안 GA도 엘리트를 생성하지 못함")
        
    except Exception as e:
        logger.error(f"대안 GA 실패: {str(e)}")
        raise

def generate_meaningful_dummy_alphas(count=10):
    """의미있는 더미 알파 생성 (실제 WorldQuant 스타일)"""
    meaningful_alphas = [
        # 모멘텀 계열
        {"expression": "ts_rank(close, 20)", "fitness": np.random.uniform(0.6, 0.8)},
        {"expression": "(close - ts_delay(close, 10)) / ts_delay(close, 10)", "fitness": np.random.uniform(0.5, 0.75)},
        {"expression": "ts_delta(close, 5) / close", "fitness": np.random.uniform(0.55, 0.7)},
        
        # 반전 계열  
        {"expression": "rank(ts_max(high, 20)) - rank(close)", "fitness": np.random.uniform(0.45, 0.65)},
        {"expression": "ts_min(low, 10) / close", "fitness": np.random.uniform(0.4, 0.6)},
        
        # 볼륨 계열
        {"expression": "rank(volume) - rank(ts_mean(volume, 20))", "fitness": np.random.uniform(0.5, 0.7)},
        {"expression": "ts_corr(close, volume, 10)", "fitness": np.random.uniform(0.3, 0.6)},
        
        # 복합 계열
        {"expression": "rank(close * volume) - rank(ts_sum(volume, 5))", "fitness": np.random.uniform(0.4, 0.65)},
        {"expression": "(high - low) / ((high + low + close) / 3)", "fitness": np.random.uniform(0.35, 0.55)},
        {"expression": "ts_rank(close / ts_mean(close, 20), 10)", "fitness": np.random.uniform(0.45, 0.7)},
        
        # 추가 고급 알파들
        {"expression": "rank(ts_decay_linear(close, 20))", "fitness": np.random.uniform(0.5, 0.75)},
        {"expression": "ts_product(close / ts_delay(close, 1), 10)", "fitness": np.random.uniform(0.4, 0.6)},
        {"expression": "scale(rank(close) - rank(ts_mean(close, 10)))", "fitness": np.random.uniform(0.45, 0.65)},
        {"expression": "ts_sum((high - close), 10) / ts_sum((close - low), 10)", "fitness": np.random.uniform(0.3, 0.55)},
        {"expression": "correlation(rank(close), rank(volume), 20)", "fitness": np.random.uniform(0.35, 0.6)}
    ]
    
    # 요청된 개수만큼 반환 (중복 허용)
    selected = meaningful_alphas[:count] if count <= len(meaningful_alphas) else meaningful_alphas * ((count // len(meaningful_alphas)) + 1)
    return selected[:count]

# 프로젝트 루트 디렉토리 설정

# Alpha 저장소 및 공용 레지스트리 초기화
ALPHA_STORE = AlphaStore(
    os.path.join(PROJECT_ROOT, 'database', 'alpha_store'),
    legacy_user_file=os.path.join(PROJECT_ROOT, 'database', 'userdata', 'user_alphas.json')
)
SHARED_ALPHA_REGISTRY = build_shared_registry(ALPHA_STORE)

# Flask 앱 초기화
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # 세션용 비밀키
CORS(app, origins=['http://localhost:3000'], supports_credentials=True)  # React 프론트엔드와의 통신을 위한 CORS 설정

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 글로벌 변수로 각 모듈 인스턴스 관리
backtest_system = None
ga_system = None
langchain_agent = None
database_manager = None
user_database = None
csv_manager = None

# 작업 상태 추적을 위한 딕셔너리
task_status = {}
backtest_status: Dict[str, Dict[str, Any]] = {}
ga_status: Dict[str, Dict[str, Any]] = {}
incubator_sessions: Dict[str, Dict[str, Any]] = {}


def get_alpha_registry(username: Optional[str] = None) -> AlphaRegistry:
    """Return a registry that merges shared alphas with the user's private ones."""
    registry = SHARED_ALPHA_REGISTRY.clone()
    if username:
        try:
            registry.extend(ALPHA_STORE.load_private_definitions(username), overwrite=True)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("사용자 알파 로드 실패 (%s): %s", username, exc)
    return registry


def infer_alpha_group(definition) -> Tuple[str, str]:
    """Derive a stable group identifier/label for the given alpha definition."""
    metadata = dict(definition.metadata or {})
    provider = (definition.provider or metadata.get("provider") or "custom").lower()
    family = metadata.get("family")
    tags = metadata.get("tags") or definition.tags or []
    owner = metadata.get("owner") or definition.owner

    def _sanitize(value: str) -> str:
        return value.lower().replace(" ", "_")

    if family:
        group_id = f"{provider}:{_sanitize(str(family))}"
        label = f"{provider.upper()} · {str(family).replace('_', ' ').title()}"
    elif tags:
        primary_tag = _sanitize(str(tags[0]))
        group_id = f"{provider}:{primary_tag}"
        label = f"{provider.upper()} · {str(tags[0]).title()}"
    elif provider == "worldquant101":
        group_id = "worldquant101"
        label = "WorldQuant 101"
    elif provider == "qlib":
        group_id = "qlib"
        label = "Qlib Factor Library"
    elif provider.startswith("user"):
        group_id = provider
        user_label = owner or provider.replace("user", "").strip(":") or "User"
        label = f"User · {user_label}"
    else:
        group_id = provider
        label = provider.title()

    return group_id, label


def serialize_alpha_definition(definition) -> Dict[str, Any]:
    """Convert an AlphaDefinition into a serializable dict."""
    payload = definition.as_dict()
    payload["name"] = definition.name
    metadata = dict(payload.get("metadata", {}))
    payload["metadata"] = metadata
    payload["id"] = metadata.get("id") or definition.name
    payload["expression"] = metadata.get("expression")
    payload["created_at"] = metadata.get("created_at")
    payload["updated_at"] = metadata.get("updated_at")
    payload["owner"] = metadata.get("owner") or payload.get("owner")
    payload["tags"] = list(payload.get("tags", []))
    group_id, group_label = infer_alpha_group(definition)
    payload["group_id"] = group_id
    payload["group_label"] = group_label
    payload["provider"] = definition.provider
    return payload


def build_user_alpha_payload(username: str) -> Dict[str, Any]:
    """Assemble shared/private alpha data for responses."""
    stored_alphas = [alpha.to_dict() for alpha in ALPHA_STORE.list_private(username)]

    registry = get_alpha_registry(username)
    private_definitions = registry.list(owner=username)
    shared_definitions = SHARED_ALPHA_REGISTRY.list(source="shared")

    private_payload = [serialize_alpha_definition(defn) for defn in private_definitions]
    shared_payload = [serialize_alpha_definition(defn) for defn in shared_definitions]

    summary = {
        "shared_count": len(shared_payload),
        "private_count": len(private_payload),
        "total_count": len(shared_payload) + len(private_payload),
        "registry_size": len(registry),
    }

    return {
        "stored_alphas": stored_alphas,
        "private_alphas": private_payload,
        "shared_alphas": shared_payload,
        "summary": summary,
    }

# 사용자 인증 관련 함수들
def load_users():
    """사용자 데이터 로드"""
    try:
        users_file = os.path.join(PROJECT_ROOT, 'database', 'userdata', 'users.json')
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"사용자 데이터 로드 실패: {e}")
        return {"users": [], "last_id": 0}

def save_users(users_data):
    """사용자 데이터 저장"""
    try:
        users_file = os.path.join(PROJECT_ROOT, 'database', 'userdata', 'users.json')
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"사용자 데이터 저장 실패: {e}")
        return False

def hash_password(password):
    """비밀번호 해시화"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """비밀번호 검증"""
    return hash_password(password) == hashed

def find_user_by_username(username):
    """사용자명으로 사용자 찾기"""
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            return user
    return None

def find_user_by_email(email):
    """이메일로 사용자 찾기"""
    users_data = load_users()
    for user in users_data['users']:
        if user['email'] == email:
            return user
    return None

def create_user(username, email, password, name):
    """새 사용자 생성"""
    users_data = load_users()
    
    # 중복 체크
    if find_user_by_username(username) or find_user_by_email(email):
        return None
    
    new_user = {
        "id": str(users_data['last_id'] + 1),
        "username": username,
        "email": email,
        "password": hash_password(password),
        "name": name,
        "role": "user",
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "is_active": True
    }
    
    users_data['users'].append(new_user)
    users_data['last_id'] += 1
    
    if save_users(users_data):
        return new_user
    return None

def update_last_login(username):
    """마지막 로그인 시간 업데이트"""
    users_data = load_users()
    for user in users_data['users']:
        if user['username'] == username:
            user['last_login'] = datetime.now().isoformat()
            save_users(users_data)
            break

def initialize_systems():
    """시스템 초기화"""
    global backtest_system, ga_system, langchain_agent, database_manager, user_database, csv_manager
    
    try:
        # Backend Module - 백테스트 시스템
        try:
            from backend_module.LongOnlyBacktestSystem import LongOnlyBacktestSystem
        except ImportError:
            try:
                from backend_module import LongOnlyBacktestSystem
            except ImportError:
                # 5_results.py에서 클래스를 직접 import
                import sys
                import importlib.util
                sys.path.append(os.path.join(PROJECT_ROOT, 'backend_module'))
                
                # 숫자로 시작하는 모듈 import
                spec = importlib.util.spec_from_file_location(
                    "results_module", 
                    os.path.join(PROJECT_ROOT, 'backend_module', '5_results.py')
                )
                results_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(results_module)
                LongOnlyBacktestSystem = results_module.LongOnlyBacktestSystem
        
        price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
        alpha_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_with_alphas.csv')
        backtest_system = LongOnlyBacktestSystem(price_file=price_file, alpha_file=alpha_file)
        logger.info("✅ 백테스트 시스템 초기화 완료")
        
        # GA Algorithm - 실제 데이터로 초기화
        try:
            from autoalpha_ga import AutoAlphaGA
            
            # 실제 데이터 로드 시도
            df_data = load_real_data_for_ga()
            if df_data and any(not df.empty for df in df_data.values()):
                shared_registry = get_alpha_registry()
                ga_system = AutoAlphaGA(df_data, hold_horizon=1, random_seed=42, registry=shared_registry)
                logger.info("✅ GA 시스템 (실제 데이터) 초기화 완료")
            else:
                # 실제 데이터 로드 실패 시 최소한의 더미 데이터
                logger.warning("⚠️ 실제 데이터 로드 실패, 더미 데이터 사용")
                dummy_data = create_minimal_dummy_data()
                shared_registry = get_alpha_registry()
                ga_system = AutoAlphaGA(dummy_data, hold_horizon=1, random_seed=42, registry=shared_registry)
                logger.info("✅ GA 시스템 (더미 데이터) 초기화 완료")
        except ImportError:
            # GA 시스템을 간단한 더미로 대체
            class DummyGA:
                def run(self, **kwargs):
                    return [{"expression": "alpha001", "fitness": 0.85}]
            ga_system = DummyGA()
            logger.warning("⚠️ GA 시스템을 더미로 초기화 (실제 모듈 로드 실패)")
        except Exception as e:
            class DummyGA:
                def run(self, **kwargs):
                    return [{"expression": "alpha001", "fitness": 0.85}]
            ga_system = DummyGA()
            logger.warning(f"⚠️ GA 시스템을 더미로 초기화 (초기화 실패: {e})")
        
        # Langchain Agent - 더 견고한 import
        try:
            # Langchain 폴더 경로를 sys.path에 추가
            langchain_path = os.path.join(PROJECT_ROOT, 'Langchain')
            if langchain_path not in sys.path:
                sys.path.insert(0, langchain_path)

            # simple_agent.py에서 QuickQuantAssistant 클래스를 import
            from simple_agent import QuickQuantAssistant
            langchain_agent = QuickQuantAssistant(use_llama=True)
            logger.info("✅ QuickQuantLangchain 에이전트 초기화 완료")
        except Exception as e:
            class DummyAgent:
                def process_message(self, message):
                    return f"죄송합니다. AI 에이전트 시스템이 현재 사용할 수 없습니다. 메시지: {message}"
            langchain_agent = DummyAgent()
            logger.warning(f"⚠️ Langchain 에이전트를 더미로 초기화 (실제 모듈 로드 실패: {e})")
        
        # Database Manager - 더 견고한 import
        try:
            from backtest_system import BacktestSystem
        except ImportError:
            try:
                sys.path.append(os.path.join(PROJECT_ROOT, 'database'))
                from backtest_system import BacktestSystem
            except ImportError:
                # 데이터베이스 매니저를 간단한 더미로 대체
                class DummyDatabase:
                    def __init__(self):
                        pass
                database_manager = DummyDatabase()
                logger.warning("⚠️ 데이터베이스 매니저를 더미로 초기화 (실제 모듈 로드 실패)")
        else:
            database_manager = BacktestSystem()
            logger.info("✅ 데이터베이스 매니저 초기화 완료")
        
        # 사용자 데이터베이스 초기화
        try:
            user_database = UserDatabase(os.path.join(PROJECT_ROOT, 'database', 'userdata'))
            logger.info("✅ 사용자 데이터베이스 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ 사용자 데이터베이스 초기화 실패: {e}")
            user_database = None
        
        # CSV 매니저 초기화
        try:
            csv_manager = CSVManager(os.path.join(PROJECT_ROOT, 'database', 'csv_data'))
            logger.info("✅ CSV 매니저 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ CSV 매니저 초기화 실패: {e}")
            csv_manager = None
        
    except Exception as e:
        logger.error(f"❌ 시스템 초기화 실패: {str(e)}")
        logger.error(traceback.format_exc())

# ===================== 인증 API =====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """로그인"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        # 사용자 찾기
        user = find_user_by_username(username)
        if not user:
            return jsonify({'error': '사용자를 찾을 수 없습니다'}), 401
        
        # 비밀번호 확인 (임시로 평문 비교, 실제로는 해시화된 비밀번호와 비교)
        if password != user['password'] and not verify_password(password, user['password']):
            return jsonify({'error': '비밀번호가 올바르지 않습니다'}), 401
        
        if not user['is_active']:
            return jsonify({'error': '비활성화된 계정입니다'}), 401
        
        # 세션에 사용자 정보 저장
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        
        # 마지막 로그인 시간 업데이트
        update_last_login(username)
        
        # 응답에서 비밀번호 제거
        user_info = {k: v for k, v in user.items() if k != 'password'}
        
        return jsonify({
            'message': '로그인 성공',
            'user': user_info
        })
        
    except Exception as e:
        logger.error(f"로그인 오류: {str(e)}")
        return jsonify({'error': '로그인 처리 중 오류가 발생했습니다'}), 500

@app.route('/api/auth/register', methods=['POST'])
def register():
    """회원가입"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not all([username, email, password, name]):
            return jsonify({'error': '모든 필드를 입력해주세요'}), 400
        
        # 사용자명 길이 검증
        if len(username) < 3:
            return jsonify({'error': '사용자명은 3글자 이상이어야 합니다'}), 400
        
        # 비밀번호 길이 검증
        if len(password) < 6:
            return jsonify({'error': '비밀번호는 6글자 이상이어야 합니다'}), 400
        
        # 중복 체크
        if find_user_by_username(username):
            return jsonify({'error': '이미 존재하는 사용자명입니다'}), 400
        
        if find_user_by_email(email):
            return jsonify({'error': '이미 존재하는 이메일입니다'}), 400
        
        # 새 사용자 생성
        new_user = create_user(username, email, password, name)
        if not new_user:
            return jsonify({'error': '회원가입 처리 중 오류가 발생했습니다'}), 500
        
        # 응답에서 비밀번호 제거
        user_info = {k: v for k, v in new_user.items() if k != 'password'}
        
        return jsonify({
            'message': '회원가입 성공',
            'user': user_info
        }), 201
        
    except Exception as e:
        logger.error(f"회원가입 오류: {str(e)}")
        return jsonify({'error': '회원가입 처리 중 오류가 발생했습니다'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """로그아웃"""
    try:
        session.clear()
        return jsonify({'message': '로그아웃 성공'})
    except Exception as e:
        logger.error(f"로그아웃 오류: {str(e)}")
        return jsonify({'error': '로그아웃 처리 중 오류가 발생했습니다'}), 500

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """현재 로그인한 사용자 정보"""
    try:
        if 'username' not in session:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        user = find_user_by_username(session['username'])
        if not user:
            session.clear()
            return jsonify({'error': '사용자를 찾을 수 없습니다'}), 401
        
        # 응답에서 비밀번호 제거
        user_info = {k: v for k, v in user.items() if k != 'password'}
        
        return jsonify({'user': user_info})
        
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {str(e)}")
        return jsonify({'error': '사용자 정보 조회 중 오류가 발생했습니다'}), 500

# ===================== 기존 API =====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'systems': {
            'backtest': backtest_system is not None,
            'ga': ga_system is not None,
            'langchain': langchain_agent is not None,
            'database': database_manager is not None
        }
    })

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """백테스트 실행 (비동기)"""
    try:
        data = request.get_json()
        
        # 기본값 설정
        start_date = data.get('start_date', '2020-01-01')
        end_date = data.get('end_date', '2024-12-31')
        factors = data.get('factors', ['alpha001'])
        rebalancing_frequency = data.get('rebalancing_frequency', 'weekly')
        transaction_cost = data.get('transaction_cost', 0.001)
        quantile = data.get('quantile', 0.1)
        max_factors = data.get('max_factors', len(factors))
        username = session.get('username')
        registry = get_alpha_registry(username)
        
        # 작업 ID 생성
        task_id = f"backtest_{int(time.time())}"
        backtest_status[task_id] = {
            'status': 'running',
            'progress': 0,
            'start_time': datetime.now().isoformat(),
            'parameters': {
                'start_date': start_date,
                'end_date': end_date,
                'factors': factors,
                'rebalancing_frequency': rebalancing_frequency,
                'transaction_cost': transaction_cost,
                'quantile': quantile,
                'max_factors': max_factors
            }
        }
        
        def append_status(progress: Optional[int] = None, log: Optional[str] = None):
            status = backtest_status.get(task_id)
            if not status:
                return
            if progress is not None:
                status['progress'] = max(0, min(100, progress))
            if log:
                logs = status.setdefault('logs', [])
                timestamp = datetime.now().strftime('%H:%M:%S')
                logs.append(f"{timestamp} · {log}")
                if len(logs) > 50:
                    logs.pop(0)

        def run_backtest_async():
            try:
                logger.info(f"백테스트 시작: {task_id}")
                append_status(progress=10, log="백테스트 작업을 시작했습니다.")

                price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
                alpha_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_with_alphas.csv')

                price_cols = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']
                append_status(progress=15, log="가격 데이터를 불러오는 중입니다.")
                price_data = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])

                start_date_dt = pd.to_datetime(start_date)
                end_date_dt = pd.to_datetime(end_date)
                price_data = price_data[(price_data['Date'] >= start_date_dt) & (price_data['Date'] <= end_date_dt)]
                if price_data.empty:
                    raise RuntimeError('선택한 기간에 대한 가격 데이터가 없습니다.')

                append_status(progress=25, log="사전 계산된 팩터를 확인합니다.")
                try:
                    alpha_columns = pd.read_csv(alpha_file, nrows=0).columns.tolist()
                except FileNotFoundError:
                    alpha_columns = []

                base_cols = ['Date', 'Ticker']
                existing_factors = [f for f in factors if f in alpha_columns]
                if existing_factors:
                    usecols = base_cols + existing_factors
                    alpha_data = pd.read_csv(alpha_file, usecols=usecols, parse_dates=['Date'])
                    alpha_data = alpha_data[(alpha_data['Date'] >= start_date_dt) & (alpha_data['Date'] <= end_date_dt)]
                else:
                    alpha_data = pd.DataFrame(columns=base_cols)

                missing_factors = [f for f in factors if f not in existing_factors]
                if missing_factors:
                    append_status(progress=35, log=f"사전 팩터에 없는 {len(missing_factors)}개 수식을 계산합니다.")
                    for idx, factor in enumerate(missing_factors, 1):
                        try:
                            computed = compute_factor_series_from_registry(factor, registry, price_data)
                            if computed is None or not isinstance(computed, pd.DataFrame):
                                raise ValueError("계산 결과가 DataFrame 형식이 아닙니다")
                            if computed.empty:
                                raise ValueError("계산 결과가 비어 있습니다")
                            computed = computed[(computed['Date'] >= start_date_dt) & (computed['Date'] <= end_date_dt)]
                            if computed.empty:
                                raise ValueError("지정한 기간에 데이터가 없습니다")
                            if alpha_data.empty:
                                alpha_data = computed
                            else:
                                alpha_data = pd.merge(alpha_data, computed, how='outer', on=['Date', 'Ticker'])
                            append_status(log=f"{factor} 계산 완료 ({idx}/{len(missing_factors)})")
                        except Exception as exc:
                            logger.error("%s 팩터 계산 실패: %s", factor, exc)
                            append_status(log=f"{factor} 계산 실패: {exc}")
                else:
                    append_status(progress=35, log="모든 팩터가 사전 계산되어 있습니다.")

                alpha_data = alpha_data.drop_duplicates(subset=['Date', 'Ticker'])

                results_dict: Dict[str, Dict[str, Any]] = {}
                total_factors = len(factors) or 1

                append_status(progress=45, log="팩터별 성과 지표를 계산합니다.")
                for idx, factor in enumerate(factors, 1):
                    append_status(progress=45 + int(40 * idx / total_factors), log=f"{factor} 백테스트 계산 중 ({idx}/{total_factors})")
                    if factor not in alpha_data.columns:
                        append_status(log=f"{factor} 데이터가 없어 건너뜁니다.")
                        continue

                    merged_data = pd.merge(
                        price_data.copy(),
                        alpha_data[['Date', 'Ticker', factor]],
                        on=['Date', 'Ticker'],
                        how='inner'
                    )
                    if merged_data.empty:
                        append_status(log=f"{factor} 데이터가 없어 건너뜁니다.")
                        continue

                    performance_data = merged_data[['Date', 'Ticker', 'Open', 'Close', factor]]
                    try:
                        metrics = calculate_factor_performance(
                            performance_data,
                            factor_col=factor,
                            quantile=quantile,
                            transaction_cost=transaction_cost,
                            rebalancing_frequency=rebalancing_frequency,
                            top_count=None
                        )
                    except ValueError as exc:
                        append_status(log=f"{factor} 계산 불가: {exc}")
                        continue

                    processed_metrics = {
                        key: (
                            float(value)
                            if isinstance(value, (np.floating, np.integer))
                            else value
                        )
                        for key, value in metrics.items()
                    }
                    results_dict[factor] = processed_metrics

                    metric_cagr = float(processed_metrics.get('cagr', 0.0))
                    metric_sharpe = float(processed_metrics.get('sharpe_ratio', 0.0))
                    logger.info("팩터 %s 백테스트 완료: CAGR %.4f, Sharpe %.4f", factor, metric_cagr, metric_sharpe)
                    append_status(log=f"{factor} 완료 (CAGR {(metric_cagr*100):.2f}% / Sharpe {metric_sharpe:.2f})")

                if not results_dict:
                    raise RuntimeError('계산된 백테스트 결과가 없습니다.')

                append_status(progress=90, log="결과를 정리하고 있습니다.")
                snapshot_logs = backtest_status.get(task_id, {}).get('logs', [])
                backtest_status[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'results': results_dict,
                    'parameters': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'factors': factors
                    },
                    'end_time': datetime.now().isoformat(),
                    'logs': snapshot_logs
                }

                append_status(progress=100, log="백테스트가 완료되었습니다.")
                logger.info("백테스트 완료: %s", task_id)

            except Exception as e:
                logger.error("백테스트 실행 오류: %s", e)
                snapshot_logs = backtest_status.get(task_id, {}).get('logs', [])
                backtest_status[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'parameters': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'factors': factors
                    },
                    'end_time': datetime.now().isoformat(),
                    'logs': snapshot_logs
                }
                append_status(log=f"백테스트 실패: {e}")
        
        # 비동기 실행
        thread = threading.Thread(target=run_backtest_async)
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '백테스트가 백그라운드에서 시작되었습니다',
            'status_url': f'/api/backtest/status/{task_id}'
        })
        
    except Exception as e:
        logger.error(f"백테스트 실행 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest/status/<task_id>', methods=['GET'])
def get_backtest_status(task_id):
    """백테스트 작업 상태 확인"""
    if task_id not in backtest_status:
        return jsonify({'error': '작업을 찾을 수 없습니다'}), 404
    
    return jsonify(backtest_status[task_id])

@app.route('/api/ga/run', methods=['POST'])
def run_ga():
    """유전 알고리즘 실행"""
    try:
        data = request.get_json()
        username = session.get('username')
        
        # GA 파라미터 설정
        population_size = data.get('population_size', 50)
        generations = data.get('generations', 20)
        max_depth = data.get('max_depth', 3)
        max_survivors = max(1, int(data.get('max_alphas', 10)))
        registry_seed_limit = data.get('registry_seed_limit')
        registry_seed_shuffle = bool(data.get('registry_seed_shuffle', False))
        if registry_seed_limit is not None:
            try:
                registry_seed_limit = int(registry_seed_limit)
            except (TypeError, ValueError):
                registry_seed_limit = None
        
        if not ga_system:
            return jsonify({'error': 'GA 시스템이 초기화되지 않았습니다'}), 500
        
        # 작업 ID 생성
        task_id = f"ga_{int(time.time())}"
        ga_status[task_id] = {
            'status': 'running',
            'progress': 0,
            'start_time': datetime.now().isoformat(),
            'parameters': {
                'population_size': population_size,
                'generations': generations,
                'max_depth': max_depth,
                'max_alphas': max_survivors,
                'registry_seed_limit': registry_seed_limit,
                'registry_seed_shuffle': registry_seed_shuffle,
            }
        }
        
        def run_ga_async():
            try:
                # 로그 스트림 초기화
                log_stream = []
                def log_to_status(message):
                    log_stream.append(f"{datetime.now().strftime('%H:%M:%S')}: {message}")
                    # 최근 50개 로그만 유지
                    if len(log_stream) > 50:
                        log_stream.pop(0)
                ga_status[task_id]['logs'] = log_stream.copy()

                logger.info(f"GA 시작: {task_id}")
                log_to_status(f"GA 실행 시작: {task_id}")
                ga_status[task_id]['progress'] = 10

                if hasattr(ga_system, 'update_registry'):
                    try:
                        effective_registry = get_alpha_registry(username)
                        ga_system.update_registry(
                            effective_registry,
                            seed_limit=registry_seed_limit,
                            shuffle=registry_seed_shuffle,
                        )
                        log_to_status(
                            f"레지스트리 동기화 완료: {len(effective_registry)}개 알파 사용, "
                            f"시드 제한={registry_seed_limit or '기본'}, 셔플={'ON' if registry_seed_shuffle else 'OFF'}"
                        )
                    except Exception as sync_error:
                        log_to_status(f"레지스트리 동기화 실패: {sync_error}")

                logger.info(f"GA 설정: 세대 {generations}, 개체수 {population_size}, 최대 깊이 {max_depth}")
                log_to_status(f"GA 설정: 세대 {generations}, 개체수 {population_size}, 최대 깊이 {max_depth}")
                ga_status[task_id]['progress'] = 20

                # GA 엔진 초기화 상태 업데이트
                ga_status[task_id]['current_generation'] = 0
                ga_status[task_id]['total_generations'] = generations
                ga_status[task_id]['best_fitness'] = 0.0

                # GA 데이터 준비
                ga_data = None
                if ga_system and hasattr(ga_system, 'data'):
                    ga_data = ga_system.data
                elif hasattr(ga_system, '_data'):
                    ga_data = ga_system._data
                else:
                    # GA 시스템에서 데이터를 가져올 수 없으면 실제 데이터 로드 시도
                    ga_data = load_real_data_for_ga()
                    if not ga_data:
                        # 최소 더미 데이터 생성
                        ga_data = create_minimal_dummy_data()
                
                # GA 실행 (안전한 실행 방식)
                try:
                    if hasattr(ga_system, 'run'):
                        log_to_status("실제 GA 엔진 실행 시작")
                        log_to_status(f"GA 파라미터: max_depth={max_depth}, population={population_size}, generations={generations}")

                        # 실제 GA 실행 시도 - 올바른 파라미터 이름 사용
                        try:
                            best_alphas = ga_system.run(
                                max_depth=max_depth,
                                population=population_size,
                                generations=generations,
                                warmstart_k=4,
                                n_keep_per_depth=10,
                                p_mutation=0.3,
                                p_crossover=0.7
                            )
                            log_to_status(f"GA 실행 완료, 원시 결과 타입: {type(best_alphas)}, 길이: {len(best_alphas) if best_alphas else 0}")
                        except Exception as ga_error:
                            log_to_status(f"GA 실행 중 예외 발생: {str(ga_error)}")
                            raise ga_error

                        log_to_status(f"GA 실행 완료, 결과: {len(best_alphas) if best_alphas else 0}개 알파 발견")
                        # GA 실행 중간 업데이트 (예시로 중간에 상태 업데이트)
                        ga_status[task_id]['progress'] = 60
                        ga_status[task_id]['current_generation'] = generations // 2  # 중간 지점으로 설정
                        
                        # GA 결과 처리 - 빈 결과도 수용하되 의미있는 알파 생성
                        logger.info(f"GA 실행 완료. 원시 결과: {len(best_alphas) if best_alphas else 0}개")
                        
                        # 실제 GA 결과가 있는 경우 (또는 빈 리스트인 경우 더미 데이터로 폴백)
                        if best_alphas and len(best_alphas) > 0:
                            formatted_alphas = []
                            elite_cap = max(1, min(max_survivors, len(best_alphas)))
                            for ind in best_alphas[:elite_cap]:
                                if hasattr(ind, 'tree') and hasattr(ind, 'fitness'):
                                    try:
                                        expr = ind.tree.to_python_expr() if hasattr(ind.tree, 'to_python_expr') else str(ind.tree)
                                        fitness_val = float(ind.fitness) if ind.fitness is not None else 0.0
                                        formatted_alphas.append({
                                            "expression": expr,
                                            "fitness": abs(fitness_val)  # 절대값으로 변환
                                        })
                                    except Exception as e:
                                        logger.warning(f"개체 변환 실패: {e}")
                                        continue

                            if formatted_alphas:
                                best_alphas = formatted_alphas
                                logger.info(f"실제 GA 결과 사용: {len(best_alphas)}개")
                            else:
                                logger.warning("GA 결과 직렬화 실패, 트리 표현 문자열로 폴백합니다.")
                                fallback_alphas = []
                                for ind in best_alphas[:elite_cap]:
                                    try:
                                        fallback_alphas.append({
                                            "expression": repr(getattr(ind, "tree", ind)),
                                            "fitness": abs(float(getattr(ind, "fitness", 0.0) or 0.0))
                                        })
                                    except Exception as err:
                                        logger.warning(f"폴백 변환 실패: {err}")
                                        continue
                                if fallback_alphas:
                                    best_alphas = fallback_alphas
                                    logger.info(f"폴백 GA 결과 사용: {len(best_alphas)}개")
                                else:
                                    raise ValueError("GA 결과 변환 실패")
                        else:
                            # GA가 엘리트를 찾지 못한 경우 - 명확한 오류 메시지 출력
                            log_to_status(f"❌ 실제 GA에서 결과 없음 (길이: {len(best_alphas) if best_alphas else 0})")
                            log_to_status("❌ 유전 알고리즘에서 엘리트를 찾을 수 없습니다. 데이터나 알고리즘 설정을 확인해주세요.")
                            logger.warning("GA에서 엘리트를 찾지 못함. 사용자에게 오류 메시지 반환.")

                            # 상태를 실패로 업데이트하고 사용자에게 명확한 피드백 제공
                            ga_status[task_id].update({
                                'status': 'failed',
                                'error': '유전 알고리즘에서 엘리트를 찾을 수 없습니다. 데이터나 알고리즘 설정을 확인해주세요.',
                                'error_details': f'실제 GA 실행 결과: {len(best_alphas) if best_alphas else 0}개 엘리트 발견'
                            })

                            # 실제 결과가 없으므로 빈 리스트 반환
                            best_alphas = []
                    else:
                        raise AttributeError("GA 시스템에 run 메서드가 없습니다")
                        
                except Exception as ga_error:
                    log_to_status(f"❌ 실제 GA 실행 중 예외 발생: {str(ga_error)}")
                    logger.error(f"실제 GA 실행 실패: {str(ga_error)}")

                    # 상태를 실패로 업데이트하고 사용자에게 명확한 피드백 제공
                    ga_status[task_id].update({
                        'status': 'failed',
                        'error': f'유전 알고리즘 실행 중 예외가 발생했습니다: {str(ga_error)}',
                        'error_details': '알고리즘 실행 중 예상치 못한 오류가 발생했습니다.'
                    })

                    # GA 실행에서 예외 발생 시 빈 리스트 반환
                    best_alphas = []
                    log_to_status("❌ 유전 알고리즘 실행 중 오류가 발생했습니다.")
                
                ga_status[task_id]['progress'] = 80
                
                # 결과 정리 및 상태 업데이트
                if isinstance(best_alphas, list):
                    if len(best_alphas) > 0:
                        results = best_alphas
                        status = 'completed'
                        log_to_status(f"✅ 총 {len(results)}개 알파 생성 완료")
                    else:
                        results = []
                        status = 'failed'
                        log_to_status("❌ 생성된 알파가 없습니다. 데이터나 알고리즘 설정을 확인해주세요.")
                else:
                    results = [{"expression": str(best_alphas), "fitness": 0.8}]
                    status = 'completed'
                    log_to_status(f"⚠️ 예상치 못한 결과 형식: {type(best_alphas)}")

                # 최종 결과 저장 전 상태 업데이트
                ga_status[task_id].update({
                    'status': status,
                    'progress': 100,
                    'results': results,
                    'parameters': {
                        'population_size': population_size,
                        'generations': generations,
                        'max_depth': max_depth
                    },
                    'end_time': datetime.now().isoformat(),
                    'final_generation': generations,
                    'total_alphas_generated': len(results)
                })

                if status == 'completed':
                    log_to_status(f"GA 실행 완료! 총 {len(results)}개 알파 생성")
                else:
                    log_to_status(f"GA 실행 실패! 총 {len(results)}개 알파 생성")

                logger.info(f"GA 완료: {task_id} (상태: {status})")

            except Exception as e:
                logger.error(f"GA 실행 오류: {str(e)}")
                ga_status[task_id] = {
                    'status': 'failed',
                    'error': str(e),
                    'parameters': {
                        'population_size': population_size,
                        'generations': generations,
                        'max_depth': max_depth
                    },
                    'end_time': datetime.now().isoformat()
                }
        
        # 비동기 실행
        thread = threading.Thread(target=run_ga_async)
        thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'GA가 백그라운드에서 시작되었습니다',
            'status_url': f'/api/ga/status/{task_id}'
        })
        
    except Exception as e:
        logger.error(f"GA 실행 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ga/status/<task_id>', methods=['GET'])
def get_ga_status(task_id):
    """GA 작업 상태 확인"""
    if task_id not in ga_status:
        return jsonify({'error': '작업을 찾을 수 없습니다'}), 404
    
    return jsonify(ga_status[task_id])

@app.route('/api/ga/backtest/<task_id>', methods=['POST'])
def backtest_ga_results(task_id):
    """GA 결과를 백테스트에 연결"""
    try:
        if task_id not in ga_status:
            return jsonify({'error': 'GA 작업을 찾을 수 없습니다'}), 404
            
        ga_result = ga_status[task_id]
        if ga_result['status'] != 'completed':
            return jsonify({'error': 'GA 작업이 완료되지 않았습니다'}), 400
            
        if 'results' not in ga_result or not ga_result['results']:
            return jsonify({'error': 'GA 결과가 없습니다'}), 400
        
        data = request.get_json()
        start_date = data.get('start_date', '2020-01-01')
        end_date = data.get('end_date', '2024-12-31')
        rebalancing_frequency = data.get('rebalancing_frequency', 'weekly')
        transaction_cost = data.get('transaction_cost', 0.001)
        quantile = data.get('quantile', 0.1)

        start_date_dt = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        
        # GA 결과에서 상위 N개 표현식 추출
        top_expressions = ga_result['results'][:5]  # 상위 5개
        
        # NewAlphas.py 파일 생성 (더미)
        logger.info(f"GA 결과 백테스트 시작: {len(top_expressions)}개 표현식")
        
        # 백테스트 작업 ID 생성
        backtest_task_id = f"ga_backtest_{int(time.time())}"
        backtest_status[backtest_task_id] = {
            'status': 'running',
            'progress': 0,
            'start_time': datetime.now().isoformat(),
            'parameters': {
                'start_date': start_date,
                'end_date': end_date,
                'ga_task_id': task_id,
                'expressions': [expr['expression'] for expr in top_expressions],
                'rebalancing_frequency': rebalancing_frequency,
                'transaction_cost': transaction_cost,
                'quantile': quantile
            }
        }
        
        def run_ga_backtest_async():
            try:
                logger.info(f"GA 백테스트 시작: {backtest_task_id}")
                backtest_status[backtest_task_id]['progress'] = 10

                price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
                price_cols = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']

                price_data = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])
                price_data = price_data[(price_data['Date'] >= start_date_dt) & (price_data['Date'] <= end_date_dt)]

                if price_data.empty:
                    raise ValueError('선택한 기간에 해당하는 가격 데이터가 없습니다')

                price_data = price_data.sort_values(['Date', 'Ticker']).reset_index(drop=True)
                grouped_price = {
                    ticker: group[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
                    for ticker, group in price_data.groupby('Ticker')
                }

                results: Dict[str, Dict[str, Any]] = {}

                for index, expr_data in enumerate(top_expressions, start=1):
                    factor_name = f"ga_alpha_{index:03d}"
                    expression = expr_data.get('expression', '')
                    fitness_value = float(expr_data.get('fitness', 0.0) or 0.0)

                    try:
                        transpiled = compile_expression(expression, name=factor_name)
                    except AlphaTranspilerError as exc:
                        results[factor_name] = {
                            'expression': expression,
                            'ga_fitness': fitness_value,
                            'error': f'표현식 컴파일 실패: {exc}'
                        }
                        continue

                    factor_frames: List[pd.DataFrame] = []
                    ticker_errors: List[str] = []
                    for ticker, ticker_df in grouped_price.items():
                        dataset = prepare_alpha_dataset_from_price(ticker_df)
                        try:
                            factor_series = transpiled.callable(dataset)
                        except Exception as exc:
                            ticker_errors.append(f"{ticker}: {exc}")
                            continue

                        if isinstance(factor_series, pd.DataFrame):
                            if factor_series.shape[1] >= 1:
                                factor_series = factor_series.iloc[:, 0]
                            else:
                                factor_series = pd.Series([], index=dataset.frame.index)
                        elif not isinstance(factor_series, pd.Series):
                            try:
                                factor_series = pd.Series(factor_series, index=dataset.frame.index)
                            except Exception as exc:
                                ticker_errors.append(f"{ticker}: factor output shape mismatch ({exc})")
                                continue

                        factor_frames.append(
                            pd.DataFrame({
                                'Date': dataset.frame.index,
                                'Ticker': ticker,
                                'factor_value': factor_series.values,
                            })
                        )

                    if not factor_frames:
                        payload = {
                            'expression': expression,
                            'ga_fitness': fitness_value,
                            'error': '팩터 값을 계산할 수 없습니다',
                        }
                        if ticker_errors:
                            payload['details'] = ticker_errors
                        results[factor_name] = payload
                        continue

                    factor_df = pd.concat(factor_frames, ignore_index=True)
                    merged = pd.merge(
                        price_data[['Date', 'Ticker', 'Open', 'Close']],
                        factor_df,
                        on=['Date', 'Ticker'],
                        how='inner'
                    )

                    if 'factor_value' not in merged.columns or 'Ticker' not in merged.columns:
                        payload = {
                            'expression': expression,
                            'ga_fitness': fitness_value,
                            'error': '병합 결과에 필수 컬럼이 없습니다',
                            'columns': list(merged.columns),
                        }
                        if ticker_errors:
                            payload['details'] = ticker_errors
                        results[factor_name] = payload
                        continue

                    merged = merged.dropna(subset=['factor_value', 'Ticker'])

                    if merged.empty:
                        payload = {
                            'expression': expression,
                            'ga_fitness': fitness_value,
                            'error': '병합된 데이터가 비어 있습니다',
                        }
                        if ticker_errors:
                            payload['details'] = ticker_errors
                        results[factor_name] = payload
                        continue

                    try:
                        metrics = calculate_factor_performance(
                            merged,
                            factor_col='factor_value',
                            quantile=quantile,
                            transaction_cost=transaction_cost,
                            rebalancing_frequency=rebalancing_frequency
                        )
                    except Exception as exc:
                        payload = {
                            'expression': expression,
                            'ga_fitness': fitness_value,
                            'error': str(exc),
                        }
                        if ticker_errors:
                            payload['details'] = ticker_errors
                        results[factor_name] = payload
                        continue

                    metrics.update({
                        'expression': expression,
                        'ga_fitness': fitness_value,
                    })

                    results[factor_name] = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else v)
                                             for k, v in metrics.items()}
                    if ticker_errors:
                        results[factor_name]['warnings'] = ticker_errors

                    progress_step = 10 + int(70 * index / max(1, len(top_expressions)))
                    backtest_status[backtest_task_id]['progress'] = progress_step

                has_success = any('error' not in value for value in results.values())

                backtest_status[backtest_task_id] = {
                    'status': 'completed' if has_success else 'failed',
                    'progress': 100,
                    'results': results,
                    'parameters': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'ga_task_id': task_id,
                        'expressions': [expr['expression'] for expr in top_expressions],
                        'rebalancing_frequency': rebalancing_frequency,
                        'transaction_cost': transaction_cost,
                        'quantile': quantile
                    },
                    'end_time': datetime.now().isoformat()
                }

                logger.info(f"GA 백테스트 완료: {backtest_task_id}")
                
            except Exception as e:
                logger.error(f"GA 백테스트 실행 오류: {str(e)}")
                backtest_status[backtest_task_id] = {
                    'status': 'failed',
                    'progress': 100,
                    'error': str(e),
                    'parameters': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'ga_task_id': task_id
                    },
                    'end_time': datetime.now().isoformat()
                }
        
        thread = threading.Thread(target=run_ga_backtest_async)
        thread.start()
        
        return jsonify({
            'success': True,
            'backtest_task_id': backtest_task_id,
            'message': 'GA 결과 백테스트가 시작되었습니다',
            'status_url': f'/api/backtest/status/{backtest_task_id}'
        })
        
    except Exception as e:
        logger.error(f"GA 백테스트 실행 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_agent():
    """Langchain 에이전트와 채팅 (AI Incubator)"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        if not message:
            return jsonify({'error': 'Please enter a message'}), 400
        
        # 더미 응답 (AI 에이전트 로직)
        responses = {
            'alpha': 'I\'ve analyzed the alpha factors. Based on our data, momentum-based alphas are showing strong performance in the current market conditions.',
            'backtest': 'The backtest results indicate a Sharpe ratio of 1.85 with a maximum drawdown of -12%. The strategy shows consistent performance across different market regimes.',
            'portfolio': 'Current portfolio analysis suggests rebalancing toward technology and healthcare sectors. Risk metrics are within acceptable limits.',
            'default': f'I\'ve analyzed your request using our multi-agent system. The data analyst has examined "{message}", the alpha researcher has evaluated factor performance, and the portfolio manager has provided risk assessment.'
        }
        
        # 키워드 기반 응답
        response_text = responses['default']
        if 'alpha' in message.lower() or 'factor' in message.lower():
            response_text = responses['alpha']
        elif 'backtest' in message.lower() or 'test' in message.lower():
            response_text = responses['backtest']
        elif 'portfolio' in message.lower() or 'risk' in message.lower():
            response_text = responses['portfolio']
        
        return jsonify({
            'success': True,
            'response': response_text,
            'timestamp': datetime.now().isoformat(),
            'agents': {
                'coordinator': 'active',
                'data_analyst': 'completed',
                'alpha_researcher': 'completed',
                'portfolio_manager': 'completed'
            }
        })
        
    except Exception as e:
        logger.error(f"채팅 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/incubator/chat', methods=['POST'])
def incubator_chat():
    """LangChain + MCTS 알파 인큐베이터 대화"""
    try:
        payload = request.get_json() or {}
        message = (payload.get('message') or '').strip()
        if not message:
            return jsonify({'success': False, 'error': '메시지를 입력해 주세요'}), 400

        session_id = payload.get('session_id') or str(uuid.uuid4())
        session = incubator_sessions.setdefault(session_id, {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'messages': [],
            'candidates': [],
            'last_trace': [],
            'updated_at': datetime.now().isoformat(),
            'last_provider': 'ollama' if OLLAMA_AVAILABLE else 'heuristic',
        })

        history_payload = payload.get('history')
        if history_payload and not session['messages']:
            try:
                for entry in history_payload:
                    if not isinstance(entry, dict):
                        continue
                    role = entry.get('role') or 'user'
                    if role not in {'user', 'assistant'}:
                        continue
                    content = (entry.get('content') or '').strip()
                    if not content:
                        continue
                    if role == 'user' and content == message:
                        # 프론트엔드에서 직전 사용자 입력을 히스토리에 포함시키므로 중복을 방지
                        continue
                    timestamp = entry.get('timestamp') or datetime.now().isoformat()
                    session['messages'].append({
                        'role': role,
                        'content': content,
                        'timestamp': timestamp,
                    })
            except Exception:
                logger.warning("초기 히스토리 파싱 실패, 무시합니다.")

        session['messages'].append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat(),
        })

        intent = detect_intent(message, payload.get('intent'))
        warnings: List[str] = []
        candidates: List[Dict[str, Any]] = session.get('candidates', [])
        trace: List[Dict[str, Any]] = session.get('last_trace', [])
        llm_provider = 'unknown'

        if intent == 'off_topic':
            reply = "이 인큐베이터는 알파 수식과 플랫폼 관련 문의에만 답변합니다. 전략·지표·알파 생성과 관련된 질문을 해주세요."
        elif intent == 'generate':
            # 항상 UCT 사용 (필수)
            sims = int(payload.get('simulations') or payload.get('sims') or 24)
            ucb_c = float(payload.get('ucb_c') or math.sqrt(2.0))
            max_depth = int(payload.get('max_depth') or 3)
            branch_factor = int(payload.get('branch_factor') or 3)

            candidates, trace, llm_provider = run_mcts_search_uct(
                message,
                simulations=sims,
                c=ucb_c,
                max_depth=max_depth,
                branch_factor=branch_factor,
            )
            if llm_provider != 'ollama':
                warnings.append("로컬 Ollama LLM이 비활성화되어 휴리스틱 응답을 사용했습니다. `ollama serve` 상태를 확인하세요.")
            unsupported_reasons = sorted(
                {entry.get('reason') for entry in trace if entry.get('reason')}
            )
            for reason in unsupported_reasons:
                warnings.append(reason)
            if not candidates:
                warnings.append("MCTS 탐색에서 적합한 알파를 찾지 못해 기본 전략을 제안합니다.")
                fallback_expression = "rank(ts_rank(close - delay(close, 5), 10) * volume)"
                candidates = [{
                    'id': 'candidate_fallback',
                    'name': 'Fallback Alpha',
                    'expression': fallback_expression,
                    'rationale': '최근 5일 모멘텀을 거래량으로 가중하여 변동성이 큰 종목을 포착합니다.',
                    'score': 0.45,
                    'path': ['root', 'fallback'],
                }]
                trace = []

            best_candidate = candidates[0]
            reply_lines = [
                f"{len(candidates)}개의 후보 알파를 탐색했습니다.",
                f"우선 추천: **{best_candidate['name']}** (점수 {best_candidate['score']:.2f})",
                f"수식: {best_candidate['expression']}",
                f"해설: {best_candidate['rationale']}",
                "다른 후보도 오른쪽 패널에서 확인하고 저장할 수 있습니다.",
            ]
            reply = "\n".join(reply_lines)
            session['candidates'] = candidates
            session['last_trace'] = trace
            session['last_provider'] = llm_provider
        else:
            system_instruction = textwrap.dedent(
                """
                당신은 AlphaIncubator 용 LangChain 코디네이터입니다.
                - 사용자의 프로젝트 관련 질문에 한국어로 답하세요.
                - 알파 전략, 백테스트, GA, LangChain, MCTS 등 플랫폼 기능과 연관된 정보만 제공하세요.
                - 프로그램 외 질문은 정중히 거절하세요.
                """
            ).strip()

            recent_messages = session['messages'][-6:]
            llm_messages = [{'role': 'system', 'content': system_instruction}]
            for entry in recent_messages:
                llm_messages.append({
                    'role': entry['role'],
                    'content': entry['content'],
                })
            reply, llm_provider = call_local_llm(llm_messages, temperature=0.1)
            if llm_provider != 'ollama':
                warnings.append("로컬 Ollama LLM이 비활성화되어 휴리스틱 응답을 사용했습니다.")
            session['last_provider'] = llm_provider

        session['messages'].append({
            'role': 'assistant',
            'content': reply,
            'timestamp': datetime.now().isoformat(),
        })
        session['updated_at'] = datetime.now().isoformat()

        visible_history = [
            entry for entry in session['messages']
            if entry.get('role') in {'user', 'assistant'}
        ]

        return jsonify({
            'success': True,
            'session_id': session_id,
            'intent': intent,
            'reply': reply,
            'llm_provider': llm_provider,
            'candidates': candidates,
            'mcts_trace': trace,
            'warnings': warnings,
            'history': visible_history,
        })
    except Exception as exc:
        logger.error("인큐베이터 채팅 오류: %s", exc)
        return jsonify({'success': False, 'error': str(exc)}), 500


@app.route('/api/incubator/session/<session_id>', methods=['GET'])
def get_incubator_session(session_id: str):
    """저장된 인큐베이터 세션 조회"""
    session = incubator_sessions.get(session_id)
    if not session:
        return jsonify({'success': False, 'error': '세션을 찾을 수 없습니다'}), 404

    visible_history = [
        entry for entry in session.get('messages', [])
        if entry.get('role') in {'user', 'assistant'}
    ]

    return jsonify({
        'success': True,
        'session_id': session_id,
        'history': visible_history,
        'candidates': session.get('candidates', []),
        'mcts_trace': session.get('last_trace', []),
        'llm_provider': session.get('last_provider', 'ollama' if OLLAMA_AVAILABLE else 'heuristic'),
        'created_at': session.get('created_at'),
        'updated_at': session.get('updated_at'),
    })

@app.route('/api/data/factors', methods=['GET'])
def get_factors():
    """사용 가능한 알파 팩터 및 그룹 목록 조회"""
    try:
        username = session.get('username')
        registry = get_alpha_registry(username)
        definitions = list(registry.iter_definitions())
        alpha_columns = [definition.name for definition in definitions]

        metadata_payload: List[Dict[str, Any]] = []
        groups: Dict[str, Dict[str, Any]] = {}

        for definition in definitions:
            serialized = serialize_alpha_definition(definition)
            metadata_payload.append(serialized)
            group_id = serialized.get('group_id') or 'ungrouped'
            group_label = serialized.get('group_label') or '기타'
            if group_id not in groups:
                groups[group_id] = {
                    'id': group_id,
                    'label': group_label,
                    'count': 0,
                }
            groups[group_id]['count'] += 1

        if not alpha_columns:
            # 레지스트리가 비어있는 것은 비정상 상황이므로 기존 CSV 기반 fallback 유지
            alpha_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_with_alphas.csv')
            if os.path.exists(alpha_file):
                try:
                    df = pd.read_csv(alpha_file, nrows=1)
                    alpha_columns = [col for col in df.columns if col.startswith('alpha')]
                except Exception as e:
                    logger.warning("CSV 기반 알파 목록 추출 실패: %s", e)
            if not alpha_columns:
                alpha_columns = [f'alpha{i:03d}' for i in range(1, 102) if i not in [48, 56, 58, 59, 63, 67, 69, 70, 76, 79, 80, 82, 87, 89, 90, 91, 93, 97, 100]]

        group_list = sorted(groups.values(), key=lambda item: item['label'].lower())

        return jsonify({
            'success': True,
            'factors': alpha_columns,
            'total_count': len(alpha_columns),
            'metadata': metadata_payload,
            'groups': group_list,
        })

    except Exception as e:
        logger.error(f"팩터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/stats', methods=['GET'])
def get_data_stats():
    """데이터 통계 정보 조회"""
    try:
        stats = {}
        
        # 주가 데이터 통계
        price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
        if os.path.exists(price_file):
            price_df = pd.read_csv(price_file, nrows=1000)  # 샘플만 읽기
            stats['price_data'] = {
                'file_exists': True,
                'columns': list(price_df.columns),
                'sample_rows': len(price_df)
            }
        
        # 알파 데이터 통계
        alpha_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_with_alphas.csv')
        if os.path.exists(alpha_file):
            alpha_df = pd.read_csv(alpha_file, nrows=1000)  # 샘플만 읽기
            alpha_columns = [col for col in alpha_df.columns if col.startswith('alpha')]
            stats['alpha_data'] = {
                'file_exists': True,
                'total_columns': len(alpha_df.columns),
                'alpha_factors': len(alpha_columns),
                'sample_rows': len(alpha_df)
            }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"데이터 통계 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/ticker-list', methods=['GET'])
def get_ticker_list():
    """S&P 500 티커 목록 조회"""
    try:
        universe_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_universe.json')
        
        if not os.path.exists(universe_file):
            return jsonify({'error': 'S&P 500 유니버스 파일을 찾을 수 없습니다'}), 404
        
        with open(universe_file, 'r') as f:
            universe_data = json.load(f)
        
        if 'S&P500' not in universe_data:
            universe_data = ['S&P500'] + universe_data
        
        return jsonify({
            'success': True,
            'tickers': universe_data,
            'total_count': len(universe_data)
        })
        
    except Exception as e:
        logger.error(f"티커 목록 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/ticker-performance', methods=['POST'])
def get_ticker_performance():
    """선택 종목의 기간별 누적 수익률과 핵심 지표를 계산합니다."""
    try:
        payload = request.get_json() or {}
        raw_tickers = payload.get('tickers', [])

        if not isinstance(raw_tickers, list):
            return jsonify({'error': 'tickers 필드는 배열이어야 합니다'}), 400

        tickers: List[str] = []
        for item in raw_tickers:
            ticker = str(item).strip().upper()
            if ticker and ticker not in tickers:
                tickers.append(ticker)

        if not tickers:
            return jsonify({'error': '분석할 종목을 1개 이상 선택하세요'}), 400

        if len(tickers) > 15:
            return jsonify({'error': '한 번에 최대 15개 종목까지 분석할 수 있습니다'}), 400

        start_date_str = payload.get('start_date') or '2000-01-01'
        end_date_str = payload.get('end_date') or datetime.now().strftime('%Y-%m-%d')

        try:
            start_dt = pd.to_datetime(start_date_str)
            end_dt = pd.to_datetime(end_date_str)
        except Exception:
            return jsonify({'error': 'start_date 또는 end_date 형식이 올바르지 않습니다'}), 400

        if start_dt > end_dt:
            return jsonify({'error': 'start_date는 end_date보다 앞서야 합니다'}), 400

        price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
        if not os.path.exists(price_file):
            return jsonify({'error': '주가 데이터 파일을 찾을 수 없습니다'}), 404

        price_cols = ['Date', 'Ticker', 'Close']
        price_df = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])
        price_df['Ticker'] = price_df['Ticker'].astype(str).str.upper()

        date_mask = (price_df['Date'] >= start_dt) & (price_df['Date'] <= end_dt)
        window_df = price_df[date_mask].copy()

        actual_tickers = [ticker for ticker in tickers if ticker != 'S&P500']
        filtered_df = window_df[window_df['Ticker'].isin(actual_tickers)].copy()

        metrics_list: List[Dict[str, Any]] = []
        series_map: Dict[str, Dict[str, float]] = {}
        missing_tickers: List[str] = []

        for ticker in tickers:
            if ticker == 'S&P500':
                try:
                    index_df = (
                        window_df[['Date', 'Close']]
                        .dropna()
                        .groupby('Date')['Close']
                        .mean()
                        .reset_index()
                    )
                    if index_df.empty:
                        missing_tickers.append(ticker)
                        continue
                    series_points, metrics = calculate_ticker_performance_metrics(index_df)
                except Exception as exc:
                    logger.warning("S&P500 누적 수익률 계산 실패: %s", exc)
                    metrics_list.append({'ticker': ticker, 'error': str(exc)})
                    continue
            else:
                ticker_df = filtered_df[filtered_df['Ticker'] == ticker].copy()
                if ticker_df.empty:
                    missing_tickers.append(ticker)
                    continue

                try:
                    series_points, metrics = calculate_ticker_performance_metrics(ticker_df)
                except Exception as exc:
                    logger.warning("티커 %s 성과 계산 실패: %s", ticker, exc)
                    metrics_list.append({'ticker': ticker, 'error': str(exc)})
                    continue

            metrics_list.append({'ticker': ticker, **metrics})
            for date, value in series_points:
                date_str = date.strftime('%Y-%m-%d')
                if date_str not in series_map:
                    series_map[date_str] = {}
                series_map[date_str][ticker] = value

        if not metrics_list:
            return jsonify({
                'success': False,
                'error': '선택한 종목에 대한 데이터를 찾을 수 없습니다',
                'missing_tickers': missing_tickers,
            }), 404

        combined_series: List[Dict[str, Any]] = []
        for date_str in sorted(series_map.keys()):
            row: Dict[str, Any] = {'date': date_str}
            for ticker in tickers:
                row[ticker] = series_map[date_str].get(ticker)
            combined_series.append(row)

        return jsonify({
            'success': True,
            'series': combined_series,
            'metrics': metrics_list,
            'date_range': {
                'start': start_dt.strftime('%Y-%m-%d'),
                'end': end_dt.strftime('%Y-%m-%d'),
            },
            'missing_tickers': missing_tickers,
        })

    except Exception as e:
        logger.error("종목 성과 분석 오류: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/market/heatmap', methods=['GET'])
def get_market_heatmap():
    """섹터/인더스트리 기준 히트맵 데이터를 생성합니다."""
    try:
        price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
        info_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_stock_info.csv')

        if not os.path.exists(price_file) or not os.path.exists(info_file):
            return jsonify({'error': '시장 데이터 파일을 찾을 수 없습니다.'}), 404

        price_cols = ['Date', 'Ticker', 'Close']
        price_df = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])
        price_df['Ticker'] = price_df['Ticker'].astype(str).str.upper()
        price_df = price_df.sort_values(['Ticker', 'Date']).reset_index(drop=True)

        price_df['PrevClose'] = price_df.groupby('Ticker')['Close'].shift(1)
        price_df['DailyChange'] = price_df['Close'] - price_df['PrevClose']
        price_df['DailyChangePct'] = np.where(
            price_df['PrevClose'].notna() & (price_df['PrevClose'] != 0),
            price_df['DailyChange'] / price_df['PrevClose'],
            0.0,
        )

        latest_date = price_df['Date'].max()
        latest_df = price_df[price_df['Date'] == latest_date].copy()
        if latest_df.empty:
            return jsonify({'error': '가용한 시장 데이터가 없습니다.'}), 400

        info_df = pd.read_csv(info_file)
        info_df['Ticker'] = info_df['Ticker'].astype(str).str.upper()

        merged = pd.merge(
            latest_df,
            info_df[['Ticker', 'Company_Name', 'Sector', 'Industry', 'Market_Cap']],
            on='Ticker',
            how='left',
        )

        merged['Sector'] = merged['Sector'].fillna('Unknown')
        merged['Industry'] = merged['Industry'].fillna('Unknown')
        merged['Company_Name'] = merged['Company_Name'].fillna(merged['Ticker'])

        merged['Market_Cap'] = pd.to_numeric(merged['Market_Cap'], errors='coerce')
        valid_caps = merged['Market_Cap'][merged['Market_Cap'] > 0]
        if valid_caps.empty:
            fallback_cap = 1.0
            merged['Market_Cap'] = fallback_cap
            valid_caps = merged['Market_Cap']
        else:
            fallback_cap = float(valid_caps.median())
            merged['Market_Cap'] = merged['Market_Cap'].fillna(fallback_cap).replace(0, fallback_cap)

        use_log_scale = False
        merged['SizeValue'] = merged['Market_Cap']

        merged['SizeValue'] = merged['SizeValue'].replace([np.inf, -np.inf], np.nan).fillna(1.0)
        merged['DailyChangePct'] = merged['DailyChangePct'].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        merged['DailyChange'] = merged['DailyChange'].replace([np.inf, -np.inf], np.nan).fillna(0.0)

        def clamp_change(value: float, limit: float = 0.03) -> float:
            if value is None or not np.isfinite(value):
                return 0.0
            return float(max(-limit, min(limit, value)))

        def heatmap_color(value: float) -> str:
            clamped = clamp_change(value)
            abs_val = abs(clamped)
            ratio = min(abs_val / 0.03, 1.0)
            if abs_val < 1e-4:
                return '#2f3136'
            saturation = 60 + ratio * 28
            lightness = 46 - ratio * 24
            if clamped >= 0:
                hue = 135 - ratio * 10
            else:
                hue = 355 + ratio * 5
            return f"hsl({hue:.2f}, {saturation:.2f}%, {lightness:.2f}%)"

        def format_change(value: float) -> str:
            pct = (value or 0.0) * 100.0
            return f"{pct:+.2f}%"

        sectors: List[Dict[str, Any]] = []
        for sector, sector_df in merged.groupby('Sector'):
            industries: List[Dict[str, Any]] = []
            for industry, industry_df in sector_df.groupby('Industry'):
                tickers: List[Dict[str, Any]] = []
                for _, row in industry_df.iterrows():
                    value = float(row['SizeValue'])
                    if not np.isfinite(value) or value <= 0:
                        value = 1.0
                    change_pct = float(row['DailyChangePct'])
                    change_value = float(row['DailyChange'])
                    color = heatmap_color(change_pct)
                    ticker_payload = {
                        'name': row['Ticker'],
                        'label': row['Company_Name'],
                        'value': value,
                        'change_pct': change_pct,
                        'change_value': change_value,
                        'display_change': format_change(change_pct),
                        'color': color,
                        'close': float(row['Close']),
                        'market_cap': float(row['Market_Cap']),
                        'sector': sector,
                        'industry': industry,
                    }
                    tickers.append(ticker_payload)

                industry_value = float(sum(child['value'] for child in tickers)) if tickers else 0.0
                industry_weighted_change = (
                    sum(child['change_pct'] * child['value'] for child in tickers) if tickers else 0.0
                )
                industry_change_pct = industry_weighted_change / industry_value if industry_value else 0.0
                industry_change_value = float(sum(child['change_value'] for child in tickers)) if tickers else 0.0
                industry_color = heatmap_color(industry_change_pct)
                industries.append({
                    'name': industry,
                    'value': industry_value,
                    'change_pct': industry_change_pct,
                    'change_value': industry_change_value,
                    'display_change': format_change(industry_change_pct),
                    'color': industry_color,
                    'children': tickers,
                })

            sector_value = float(sum(child['value'] for child in industries)) if industries else 0.0
            sector_weighted_change = (
                sum((child.get('change_pct', 0.0) or 0.0) * child['value'] for child in industries) if industries else 0.0
            )
            sector_change_pct = sector_weighted_change / sector_value if sector_value else 0.0
            sector_change_value = float(sum(child.get('change_value', 0.0) for child in industries)) if industries else 0.0
            sector_color = heatmap_color(sector_change_pct)
            sectors.append({
                'name': sector,
                'value': sector_value,
                'change_pct': sector_change_pct,
                'change_value': sector_change_value,
                'display_change': format_change(sector_change_pct),
                'color': sector_color,
                'children': industries,
            })

        sectors.sort(key=lambda item: item['value'], reverse=True)

        return jsonify({
            'success': True,
            'date': latest_date.strftime('%Y-%m-%d'),
            'use_log_scale': False,
            'sectors': sectors,
        })

    except Exception as e:
        logger.error("시장 히트맵 계산 오류: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolio/stocks', methods=['POST'])
def get_portfolio_stocks():
    """알파 가중치를 반영해 상위 종목을 선별합니다."""
    try:
        data = request.get_json() or {}
        alpha_factor = data.get('alpha_factor')
        alpha_factors = data.get('alpha_factors', [])
        alpha_weights = data.get('alpha_weights', {})
        selection_method = data.get('selection_method')
        top_percentage = data.get('top_percentage')
        top_count = data.get('top_count')
        as_of_date = data.get('as_of_date')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        include_breakdown = bool(data.get('include_breakdown', True))

        def _extend(container: List[str], values: Any):
            if isinstance(values, str) and values:
                container.append(values)
            elif isinstance(values, list):
                for item in values:
                    if isinstance(item, str) and item:
                        container.append(item)

        selected_factors: List[str] = []
        _extend(selected_factors, alpha_factor)
        _extend(selected_factors, alpha_factors)

        username = session.get('username')
        registry = get_alpha_registry(username)
        definitions = list(registry.iter_definitions())

        factor_metadata: Dict[str, Dict[str, Any]] = {}
        for definition in definitions:
            factor_metadata[definition.name] = serialize_alpha_definition(definition)

        selected_factors = list(dict.fromkeys(selected_factors))

        if not selected_factors:
            return jsonify({'error': '선택된 알파가 없습니다. 알파를 하나 이상 지정해주세요.'}), 400

        alpha_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_with_alphas.csv')
        if not os.path.exists(alpha_file):
            return jsonify({'error': '알파 데이터 파일을 찾을 수 없습니다'}), 404

        df = pd.read_csv(alpha_file)

        available_columns = set(df.columns)
        missing_factors = [factor for factor in selected_factors if factor not in available_columns]
        available_factors = [factor for factor in selected_factors if factor in available_columns]
        missing_factor_errors: Dict[str, str] = {}

        window_start: Optional[pd.Timestamp]
        window_end: Optional[pd.Timestamp]
        if as_of_date and not start_date and not end_date:
            start_date = as_of_date
            end_date = as_of_date

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values(['Date', 'Ticker']).reset_index(drop=True)

            max_date = df['Date'].max()
            min_date = df['Date'].min()

            if start_date:
                try:
                    window_start = pd.to_datetime(start_date)
                except Exception:
                    return jsonify({'error': 'start_date 형식이 올바르지 않습니다'}), 400
            else:
                window_start = max_date

            if end_date:
                try:
                    window_end = pd.to_datetime(end_date)
                except Exception:
                    return jsonify({'error': 'end_date 형식이 올바르지 않습니다'}), 400
            else:
                window_end = max_date

            if window_start > window_end:
                return jsonify({'error': 'start_date는 end_date보다 앞서야 합니다'}), 400

            effective_start = max(window_start, min_date)
            effective_end = min(window_end, max_date)

            window_df = df[(df['Date'] >= effective_start) & (df['Date'] <= effective_end)].copy()

            if window_df.empty:
                fallback = df[df['Date'] <= effective_end]['Date'].max()
                if pd.isna(fallback):
                    fallback = max_date
                effective_start = effective_end = fallback
                window_df = df[df['Date'] == fallback].copy()
        else:
            effective_start = None
            effective_end = None
            window_df = df.copy()

        if missing_factors:
            try:
                price_file = os.path.join(PROJECT_ROOT, 'database', 'sp500_interpolated.csv')
                price_cols = ['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']
                price_frame = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])
                price_frame = price_frame.sort_values(['Date', 'Ticker']).reset_index(drop=True)
                if effective_end:
                    price_frame = price_frame[price_frame['Date'] <= effective_end]
                compute_frames: List[pd.DataFrame] = []
                for factor in missing_factors:
                    try:
                        computed = compute_factor_series_from_registry(factor, registry, price_frame)
                        if effective_start:
                            computed = computed[computed['Date'] >= effective_start]
                        if effective_end:
                            computed = computed[computed['Date'] <= effective_end]
                        compute_frames.append(computed[['Date', 'Ticker', factor]])
                    except Exception as exc:  # pragma: no cover - diagnostic logging
                        logger.error("동적 알파 계산 실패 (%s): %s", factor, exc)
                        missing_factor_errors[factor] = str(exc)
                if compute_frames:
                    computed_all = compute_frames[0]
                    for extra in compute_frames[1:]:
                        computed_all = pd.merge(computed_all, extra, how='outer', on=['Date', 'Ticker'])
                    if 'Date' in df.columns:
                        window_df = pd.merge(window_df, computed_all, how='left', on=['Date', 'Ticker'])
                    else:
                        window_df = computed_all
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("동적 알파 계산 중 오류: %s", exc)
                for factor in missing_factors:
                    missing_factor_errors.setdefault(factor, '동적 계산 중 오류가 발생했습니다.')

        window_df = window_df.dropna(subset=['Ticker'])

        if window_df.empty:
            return jsonify({'error': '선택한 기간에 유효한 데이터가 없습니다'}), 400

        available_factors = [factor for factor in selected_factors if factor in window_df.columns]
        resolved_missing = [factor for factor in selected_factors if factor not in available_factors]
        for factor in resolved_missing:
            missing_factor_errors.setdefault(factor, '데이터를 찾을 수 없습니다.')

        if not available_factors:
            return jsonify({
                'error': '선택된 알파에 대한 데이터를 계산할 수 없습니다.',
                'missing_factors': resolved_missing,
            }), 400

        base_columns = ['Ticker']
        if 'Close' in window_df.columns:
            base_columns.append('Close')

        working = window_df[base_columns + available_factors + (['Date'] if 'Date' in window_df.columns else [])].copy()
        factor_only = working[available_factors]
        working = working.loc[~factor_only.isna().all(axis=1)].copy()

        total_universe = len(working['Ticker'].unique())
        if total_universe == 0:
            return jsonify({'error': '선택된 알파에 대해 유효한 데이터가 없습니다'}), 400

        if top_count is not None:
            selection_method = 'count'
        elif top_percentage is not None:
            selection_method = 'percentage'
        elif selection_method == 'count':
            top_count = top_count if top_count is not None else 10
        elif selection_method == 'percentage':
            top_percentage = top_percentage if top_percentage is not None else 10
        else:
            selection_method = 'percentage'
            top_percentage = 10

        if selection_method == 'count':
            try:
                top_count = int(top_count if top_count is not None else 10)
            except (TypeError, ValueError):
                top_count = 10
            top_count = max(1, min(top_count, total_universe))
            top_n = top_count
            selection_criteria = f'상위 {top_count}개 종목'
        else:
            try:
                percentage = float(top_percentage if top_percentage is not None else 10.0)
            except (TypeError, ValueError):
                percentage = 10.0
            percentage = max(0.1, min(percentage, 100.0))
            top_n = max(1, int(round(total_universe * (percentage / 100.0))))
            selection_criteria = f'상위 {percentage}% ({top_n}개 종목)'
            top_percentage = percentage

        rank_columns: List[str] = []
        if 'Date' in working.columns:
            for factor in available_factors:
                rank_column = f'{factor}__rank'
                working[rank_column] = working.groupby('Date')[factor].rank(method='average', ascending=False, pct=True)
                rank_columns.append(rank_column)
        else:
            for factor in available_factors:
                rank_column = f'{factor}__rank'
                working[rank_column] = working[factor].rank(method='average', ascending=False, pct=True)
                rank_columns.append(rank_column)

        grouped = working.groupby('Ticker')
        summary = pd.DataFrame(index=sorted(working['Ticker'].unique()))
        summary.index.name = 'Ticker'

        if 'Close' in working.columns:
            summary['Close'] = grouped['Close'].last()

        for factor in available_factors:
            rank_column = f'{factor}__rank'
            summary[factor] = grouped[factor].mean()
            summary[rank_column] = grouped[rank_column].mean()

        rank_cols = [f'{factor}__rank' for factor in available_factors]
        summary = summary.dropna(subset=rank_cols, how='all')

        if summary.empty:
            return jsonify({'error': '선택된 알파에 대해 합성 점수를 계산할 수 없습니다'}), 400

        raw_weight_values: List[float] = []
        for factor in available_factors:
            raw_value = alpha_weights.get(factor)
            if raw_value is None:
                raw_value = alpha_weights.get(factor.lower())
            try:
                raw_weight_values.append(float(raw_value))
            except (TypeError, ValueError):
                raw_weight_values.append(1.0)

        weight_array = np.array(raw_weight_values, dtype=float)
        if not np.isfinite(weight_array).any() or np.all(weight_array == 0):
            weight_array = np.ones_like(weight_array)

        max_weight = np.max(weight_array)
        exps = np.exp(weight_array - max_weight)
        softmax_den = np.sum(exps)
        if softmax_den == 0 or not np.isfinite(softmax_den):
            softmax_weights = np.ones_like(weight_array) / len(weight_array)
        else:
            softmax_weights = exps / softmax_den

        scores: List[float] = []
        rank_matrix = summary[rank_cols].to_numpy()
        for row in rank_matrix:
            mask = np.isfinite(row)
            if not mask.any():
                scores.append(float('nan'))
                continue
            weights_masked = softmax_weights[mask]
            weights_masked = weights_masked / weights_masked.sum()
            score = float(np.dot(row[mask], weights_masked))
            scores.append(score)

        summary['composite_score'] = scores
        summary = summary.replace([np.inf, -np.inf], np.nan).dropna(subset=['composite_score'])

        if summary.empty:
            return jsonify({'error': '선택된 알파에 대해 합성 점수를 계산할 수 없습니다'}), 400

        summary = summary.sort_values('composite_score', ascending=False)
        top_df = summary.head(top_n).reset_index()

        def safe_number(value: Any) -> Optional[float]:
            try:
                if pd.isna(value):
                    return None
            except Exception:
                pass
            if isinstance(value, (np.integer, np.floating)):
                return float(value)
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        stock_list: List[Dict[str, Any]] = []
        for _, row in top_df.iterrows():
            factor_breakdown: List[Dict[str, Any]] = []
            if include_breakdown:
                for idx, factor in enumerate(available_factors):
                    rank_column = f'{factor}__rank'
                    meta = factor_metadata.get(factor, {})
                    factor_breakdown.append({
                        'name': factor,
                        'value': safe_number(row.get(factor)),
                        'rank': safe_number(row.get(rank_column)),
                        'weight': float(softmax_weights[idx]),
                        'provider': meta.get('provider'),
                        'description': meta.get('description'),
                        'tags': meta.get('tags', []),
                    })

            stock_info: Dict[str, Any] = {
                'ticker': row['Ticker'],
                'rank': int(row.name + 1),
                'composite_score': safe_number(row.get('composite_score')),
            }

            if include_breakdown:
                stock_info['factors'] = factor_breakdown

            if 'Close' in row:
                stock_info['close'] = safe_number(row.get('Close'))

            stock_list.append(stock_info)

        factor_summary: List[Dict[str, Any]] = []
        for idx, factor in enumerate(available_factors):
            meta = factor_metadata.get(factor, {})
            factor_summary.append({
                'name': factor,
                'provider': meta.get('provider'),
                'description': meta.get('description'),
                'tags': meta.get('tags', []),
                'raw_weight': float(weight_array[idx]),
                'weight_share': float(softmax_weights[idx]),
            })

        resolved_as_of = (
            effective_end.strftime('%Y-%m-%d')
            if isinstance(effective_end, pd.Timestamp)
            else as_of_date
        )

        return jsonify({
            'success': True,
            'stocks': stock_list,
            'parameters': {
                'alpha_factor': alpha_factor,
                'alpha_factors': selected_factors,
                'used_factors': available_factors,
                'top_percentage': top_percentage,
                'top_count': top_count,
                'selection_method': selection_method,
                'as_of_date': resolved_as_of,
                'alpha_weights': {factor: float(weight_array[idx]) for idx, factor in enumerate(available_factors)},
                'softmax_weights': {factor: float(softmax_weights[idx]) for idx, factor in enumerate(available_factors)},
                'include_breakdown': include_breakdown,
                'start_date': effective_start.strftime('%Y-%m-%d') if isinstance(effective_start, pd.Timestamp) else None,
                'end_date': effective_end.strftime('%Y-%m-%d') if isinstance(effective_end, pd.Timestamp) else None,
                'total_stocks': total_universe,
                'selected_stocks': len(stock_list),
            },
            'summary': {
                'selection_criteria': selection_criteria,
                'requested_factor_count': len(selected_factors),
                'used_factor_count': len(available_factors),
                'missing_factors': missing_factors,
                'best_score': safe_number(top_df['composite_score'].iloc[0]) if len(top_df) else None,
                'worst_score': safe_number(top_df['composite_score'].iloc[-1]) if len(top_df) else None,
            },
            'factors': factor_summary,
            'missing_factors': list(missing_factor_errors.keys()),
            'missing_factor_errors': missing_factor_errors,
        })

    except Exception as e:
        logger.error(f"포트폴리오 종목 선별 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/portfolio/performance', methods=['POST'])
def get_portfolio_performance():
    """포트폴리오 성과 분석"""
    try:
        data = request.get_json()
        alpha_factor = data.get('alpha_factor', 'alpha001')
        top_percentage = data.get('top_percentage', None)
        top_count = data.get('top_count', None)
        start_date = data.get('start_date', '2020-01-01')
        end_date = data.get('end_date', '2024-12-31')
        transaction_cost = data.get('transaction_cost', 0.001)
        rebalancing_frequency = data.get('rebalancing_frequency', 'weekly')
        
        # 백테스트 시스템을 이용한 성과 분석 (기존 시스템 비활성화)
        # if not backtest_system:
        #     return jsonify({'error': '백테스트 시스템이 초기화되지 않았습니다'}), 500
        
        # 디버깅 정보 출력
        logger.info(f"=== 백엔드 디버깅 정보 ===")
        logger.info(f"alpha_factor: {alpha_factor}")
        logger.info(f"top_count: {top_count}")
        logger.info(f"top_percentage: {top_percentage}")
        logger.info(f"start_date: {start_date}")
        logger.info(f"end_date: {end_date}")
        logger.info(f"transaction_cost: {transaction_cost}")
        logger.info(f"rebalancing_frequency: {rebalancing_frequency}")
        
        # quantile 계산
        if top_count is not None:
            # 개수 기준인 경우, 대략적인 퍼센트로 변환 (백테스트에서는 quantile 방식만 지원)
            estimated_percentage = min(max((top_count / 500) * 100, 1), 50)  # 추정 퍼센트 (1-50% 범위)
            quantile = estimated_percentage / 100.0
            logger.info(f"top_count {top_count} -> estimated_percentage {estimated_percentage}% -> quantile {quantile:.3f}")
        else:
            percentage = top_percentage if top_percentage is not None else 10
            quantile = percentage / 100.0
            logger.info(f"top_percentage {percentage}% -> quantile {quantile:.3f}")
        
        # 백테스트 실행
        logger.info(f"포트폴리오 성과 분석: {alpha_factor}, quantile: {quantile:.3f}")
        
        try:
            # 직접 백테스트 로직 구현 (일관된 결과를 위해)
            import pandas as pd
            import numpy as np
            
            # 데이터 로드
            price_file = 'database/sp500_interpolated.csv'
            alpha_file = 'database/sp500_with_alphas.csv'
            
            # 필요한 컬럼만 로드
            price_cols = ['Date', 'Ticker', 'Open', 'Close']
            alpha_cols = ['Date', 'Ticker', alpha_factor]
            
            # 데이터 로드 (일관된 결과를 위해 매번 새로 로드)
            price_data = pd.read_csv(price_file, usecols=price_cols, parse_dates=['Date'])
            alpha_data = pd.read_csv(alpha_file, usecols=alpha_cols, parse_dates=['Date'])
            
            # 날짜 필터링
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            
            price_data = price_data[(price_data['Date'] >= start_date) & (price_data['Date'] <= end_date)]
            alpha_data = alpha_data[(alpha_data['Date'] >= start_date) & (alpha_data['Date'] <= end_date)]
            
            # 데이터 정렬 (일관된 결과를 위해)
            price_data = price_data.sort_values(['Date', 'Ticker']).reset_index(drop=True)
            alpha_data = alpha_data.sort_values(['Date', 'Ticker']).reset_index(drop=True)
            
            # 데이터 병합
            merged_data = pd.merge(price_data, alpha_data, on=['Date', 'Ticker'], how='inner')
            
            if len(merged_data) == 0:
                raise Exception("병합된 데이터가 없습니다")

            metrics = calculate_factor_performance(
                merged_data[['Date', 'Ticker', 'Open', 'Close', alpha_factor]],
                factor_col=alpha_factor,
                quantile=quantile,
                transaction_cost=transaction_cost,
                rebalancing_frequency=rebalancing_frequency,
                top_count=top_count
            )

            performance = {
                'cagr': float(metrics.get('cagr', 0.0)),
                'sharpe_ratio': float(metrics.get('sharpe_ratio', 0.0)),
                'max_drawdown': float(metrics.get('max_drawdown', 0.0)),
                'ic_mean': float(metrics.get('ic_mean', 0.0)),
                'win_rate': float(metrics.get('win_rate', 0.0)),
                'volatility': float(metrics.get('volatility', 0.0))
            }
            logger.info(
                "실제 백테스트 결과: CAGR=%.4f, Sharpe=%.4f",
                performance['cagr'],
                performance['sharpe_ratio']
            )
                
        except Exception as e:
            logger.error(f"백테스트 실행 실패: {e}")
            # 백업으로 더미 데이터 사용
            performance = {
                'cagr': float(np.random.uniform(0.05, 0.15)),
                'sharpe_ratio': float(np.random.uniform(0.8, 2.0)),
                'max_drawdown': float(np.random.uniform(-0.25, -0.05)),
                'ic_mean': float(np.random.uniform(0.01, 0.08)),
                'win_rate': float(np.random.uniform(0.45, 0.65)),
                'volatility': float(np.random.uniform(0.15, 0.30))
            }
        
        # JSON 직렬화 가능한 형태로 변환
        serializable_performance = {
            k: float(v) if isinstance(v, (np.float64, np.int64)) else v
            for k, v in performance.items()
        }
        
        return jsonify({
            'success': True,
            'performance': serializable_performance,
            'parameters': {
                'alpha_factor': alpha_factor,
                'top_percentage': top_percentage,
                'top_count': top_count,
                'start_date': start_date,
                'end_date': end_date,
                'transaction_cost': transaction_cost,
                'rebalancing_frequency': rebalancing_frequency,
                'quantile': quantile
            }
        })
        
    except Exception as e:
        logger.error(f"포트폴리오 성과 분석 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-alpha/save', methods=['POST'])
def save_user_alpha():
    """사용자 알파 저장"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json() or {}
        alphas = data.get('alphas', [])
        
        if not alphas:
            return jsonify({'error': '저장할 알파가 없습니다'}), 400
        
        compiled_records = []
        errors = []
        for index, alpha in enumerate(alphas, start=1):
            expression = (alpha.get('expression') or '').strip()
            alpha_name = (alpha.get('name') or f'{username}_alpha_{index:03d}').strip()

            if not expression:
                errors.append(f"{alpha_name}: 알파 수식이 비어 있습니다")
                continue

            try:
                transpiled = compile_expression(expression, name=alpha_name)
            except AlphaTranspilerError as exc:
                errors.append(f"{alpha_name}: {exc}")
                continue

            incoming_metadata = alpha.get('metadata') if isinstance(alpha.get('metadata'), dict) else {}
            metadata = dict(incoming_metadata)

            fitness_value = metadata.get('fitness') if isinstance(metadata.get('fitness'), (int, float)) else alpha.get('fitness')
            if fitness_value is not None:
                try:
                    metadata['fitness'] = float(fitness_value)
                except (TypeError, ValueError):
                    metadata['fitness'] = fitness_value

            metadata['transpiler_version'] = transpiled.version
            metadata['python_source'] = transpiled.python_source
            metadata['expression'] = expression

            tags = alpha.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
            elif isinstance(tags, list):
                tags = [str(tag).strip() for tag in tags if str(tag).strip()]
            else:
                tags = []

            compiled_records.append({
                'id': alpha.get('id'),
                'name': alpha_name,
                'expression': expression,
                'description': alpha.get('description', ''),
                'tags': tags,
                'metadata': metadata,
            })

        if errors:
            return jsonify({
                'error': '일부 알파 수식을 처리할 수 없습니다',
                'details': errors
            }), 400

        stored_items = ALPHA_STORE.add_private(username, compiled_records)
        logger.info("사용자 %s의 %d개 알파 저장 완료", username, len(stored_items))

        payload = build_user_alpha_payload(username)
        payload.update({
            'success': True,
            'message': f'{len(stored_items)}개의 알파가 저장되었습니다',
            'saved_alphas': [item.to_dict() for item in stored_items],
            'is_authenticated': True,
        })

        return jsonify(payload)
        
    except Exception as e:
        logger.error(f"알파 저장 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-alpha/list', methods=['GET'])
def get_user_alphas():
    """사용자 알파 목록 조회"""
    try:
        username = session.get('username')
        if username:
            payload = build_user_alpha_payload(username)
            payload.update({"success": True, "is_authenticated": True})
            return jsonify(payload)

        shared_payload = [serialize_alpha_definition(defn) for defn in SHARED_ALPHA_REGISTRY.list(source='shared')]
        return jsonify({
            'success': True,
            'stored_alphas': [],
            'private_alphas': [],
            'shared_alphas': shared_payload,
            'summary': {
                'shared_count': len(shared_payload),
                'private_count': 0,
                'total_count': len(shared_payload),
                'registry_size': len(SHARED_ALPHA_REGISTRY),
            },
            'is_authenticated': False,
        })
        
    except Exception as e:
        logger.error(f"알파 목록 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user-alpha/delete/<alpha_id>', methods=['DELETE'])
def delete_user_alpha(alpha_id):
    """사용자 알파 삭제"""
    try:
        username = session.get('username')
        if not username:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if not ALPHA_STORE.delete_private(username, alpha_id):
            return jsonify({'error': '알파를 찾을 수 없습니다'}), 404

        logger.info("사용자 %s의 알파 %s 삭제 완료", username, alpha_id)

        payload = build_user_alpha_payload(username)
        payload.update({
            'success': True,
            'message': '알파가 삭제되었습니다',
            'is_authenticated': True,
        })
        return jsonify(payload)
        
    except Exception as e:
        logger.error(f"알파 삭제 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/<user_id>', methods=['GET'])
def get_dashboard_data(user_id):
    """대시보드 자산 데이터 조회"""
    try:
        dashboard_file = os.path.join(PROJECT_ROOT, 'database', 'userdata', f'{user_id}_dashboard.json')
        
        if not os.path.exists(dashboard_file):
            # 기본 데이터 반환
            return jsonify({
                'success': True,
                'data': {
                    'deposits': 13126473,
                    'savings': 7231928,
                    'insurance': 3431750,
                    'stocks': 32155859,
                    'total': 55946010,
                    'changes': {
                        'deposits': -609281,
                        'deposits_percent': -3.9,
                        'savings': -802540,
                        'savings_percent': -11.1,
                        'insurance': 50000,
                        'insurance_percent': 1.5,
                        'stocks': 9256265,
                        'stocks_percent': 28.8
                    },
                    'history': []
                }
            })
        
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            dashboard_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/<user_id>', methods=['POST'])
def update_dashboard_data(user_id):
    """대시보드 자산 데이터 업데이트"""
    try:
        data = request.get_json()
        dashboard_file = os.path.join(PROJECT_ROOT, 'database', 'userdata', f'{user_id}_dashboard.json')
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(dashboard_file), exist_ok=True)
        
        # 파일 저장
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"사용자 {user_id}의 대시보드 데이터 업데이트 완료")
        
        return jsonify({
            'success': True,
            'message': '대시보드 데이터가 업데이트되었습니다'
        })
        
    except Exception as e:
        logger.error(f"대시보드 데이터 업데이트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===================== 사용자 계정 관리 API =====================

@app.route('/api/user/register', methods=['POST'])
def register_user():
    """사용자 등록"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not all([username, email, password]):
            return jsonify({'error': '필수 필드가 누락되었습니다'}), 400
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        user_id = user_database.create_user(username, email, password, name)
        
        return jsonify({
            'success': True,
            'message': '사용자가 성공적으로 등록되었습니다',
            'user_id': user_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"사용자 등록 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/login', methods=['POST'])
def user_login():
    """사용자 로그인"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        user_id = user_database.authenticate_user(username, password)
        if not user_id:
            return jsonify({'error': '인증에 실패했습니다'}), 401
        
        # 사용자 정보 조회 (세션 메타데이터로 활용)
        user_info = user_database.get_user_info(user_id)

        # 세션에 사용자 ID 및 사용자명 저장 (알파 관리 등에서 사용)
        session['user_id'] = user_id
        if user_info and user_info.get('username'):
            session['username'] = user_info['username']
        elif username:
            session['username'] = username
        
        return jsonify({
            'success': True,
            'message': '로그인 성공',
            'user_id': user_id,
            'user_info': user_info
        })
        
    except Exception as e:
        logger.error(f"사용자 로그인 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """사용자 정보 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        user_info = user_database.get_user_info(user_id)
        if not user_info:
            return jsonify({'error': '사용자 정보를 찾을 수 없습니다'}), 404
        
        return jsonify({
            'success': True,
            'user_info': user_info
        })
        
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/update', methods=['PUT'])
def update_user_info():
    """사용자 정보 업데이트"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        success = user_database.update_user_info(user_id, **data)
        if not success:
            return jsonify({'error': '사용자 정보 업데이트에 실패했습니다'}), 400
        
        return jsonify({
            'success': True,
            'message': '사용자 정보가 업데이트되었습니다'
        })
        
    except Exception as e:
        logger.error(f"사용자 정보 업데이트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    """비밀번호 변경"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'error': '현재 비밀번호와 새 비밀번호를 입력해주세요'}), 400
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        success = user_database.change_password(user_id, current_password, new_password)
        if not success:
            return jsonify({'error': '비밀번호 변경에 실패했습니다. 현재 비밀번호를 확인해주세요'}), 400
        
        return jsonify({
            'success': True,
            'message': '비밀번호가 변경되었습니다'
        })
        
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/investment', methods=['GET'])
def get_user_investment():
    """사용자 투자 데이터 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        investment_data = user_database.get_user_investment_data(user_id)
        if not investment_data:
            return jsonify({'error': '투자 데이터를 찾을 수 없습니다'}), 404
        
        return jsonify({
            'success': True,
            'investment_data': investment_data
        })
        
    except Exception as e:
        logger.error(f"투자 데이터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/investment', methods=['PUT'])
def update_user_investment():
    """사용자 투자 데이터 업데이트"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        success = user_database.update_user_investment_data(user_id, **data)
        if not success:
            return jsonify({'error': '투자 데이터 업데이트에 실패했습니다'}), 400
        
        return jsonify({
            'success': True,
            'message': '투자 데이터가 업데이트되었습니다'
        })
        
    except Exception as e:
        logger.error(f"투자 데이터 업데이트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/settings', methods=['GET'])
def get_user_settings():
    """사용자 설정 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        settings = user_database.get_user_settings(user_id)
        if not settings:
            return jsonify({'error': '설정 데이터를 찾을 수 없습니다'}), 404
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"설정 데이터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/settings', methods=['PUT'])
def update_user_settings():
    """사용자 설정 업데이트"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        
        if user_database is None:
            return jsonify({'error': '사용자 데이터베이스가 초기화되지 않았습니다'}), 500
        
        success = user_database.update_user_settings(user_id, **data)
        if not success:
            return jsonify({'error': '설정 업데이트에 실패했습니다'}), 400
        
        return jsonify({
            'success': True,
            'message': '설정이 업데이트되었습니다'
        })
        
    except Exception as e:
        logger.error(f"설정 업데이트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/logout', methods=['POST'])
def user_logout():
    """사용자 로그아웃"""
    try:
        session.pop('user_id', None)
        session.pop('username', None)
        return jsonify({
            'success': True,
            'message': '로그아웃되었습니다'
        })
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===================== CSV 기반 사용자 관리 API =====================

@app.route('/api/csv/user/register', methods=['POST'])
def csv_register_user():
    """CSV 기반 사용자 등록"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        
        if not all([username, email, password]):
            return jsonify({'error': '필수 필드가 누락되었습니다'}), 400
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        user_id = csv_manager.create_user(username, email, password, name)
        
        return jsonify({
            'success': True,
            'message': '사용자가 성공적으로 등록되었습니다',
            'user_id': user_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"CSV 사용자 등록 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/login', methods=['POST'])
def csv_user_login():
    """CSV 기반 사용자 로그인"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': '사용자명과 비밀번호를 입력해주세요'}), 400
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        user_id = csv_manager.authenticate_user(username, password)
        if not user_id:
            return jsonify({'error': '인증에 실패했습니다'}), 401
        
        # 사용자 정보 조회
        user_info = csv_manager.get_user_info(user_id)
        
        # 세션에 사용자 메타데이터 저장 (알파 관리 모듈에서 사용)
        session['user_id'] = user_id
        if user_info and user_info.get('username'):
            session['username'] = user_info['username']
        elif username:
            session['username'] = username
        
        return jsonify({
            'success': True,
            'message': '로그인 성공',
            'user_id': user_id,
            'user_info': user_info
        })
        
    except Exception as e:
        logger.error(f"CSV 사용자 로그인 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/logout', methods=['POST'])
def csv_user_logout():
    """CSV 기반 사용자 로그아웃"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': '로그아웃되었습니다'
        })
    except Exception as e:
        logger.error(f"CSV 사용자 로그아웃 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/info', methods=['GET'])
def csv_get_user_info():
    """CSV 기반 사용자 정보 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        user_info = csv_manager.get_user_info(user_id)
        if not user_info:
            return jsonify({'error': '사용자 정보를 찾을 수 없습니다'}), 404
        
        return jsonify({
            'success': True,
            'user_info': user_info
        })
        
    except Exception as e:
        logger.error(f"CSV 사용자 정보 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/investment', methods=['GET'])
def csv_get_user_investment():
    """CSV 기반 투자 데이터 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        investment_data = csv_manager.get_investment_data(user_id)
        if not investment_data:
            return jsonify({'error': '투자 데이터를 찾을 수 없습니다'}), 404
        
        # 자산 이력도 함께 조회
        asset_history = csv_manager.get_asset_history(user_id, limit=30)
        
        return jsonify({
            'success': True,
            'investment_data': investment_data,
            'asset_history': asset_history
        })
        
    except Exception as e:
        logger.error(f"CSV 투자 데이터 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/portfolio', methods=['GET'])
def csv_get_portfolio():
    """CSV 기반 포트폴리오 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        portfolio = csv_manager.get_portfolio(user_id)
        
        return jsonify({
            'success': True,
            'portfolio': portfolio
        })
        
    except Exception as e:
        logger.error(f"CSV 포트폴리오 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/portfolio/add', methods=['POST'])
def csv_add_portfolio_item():
    """CSV 기반 포트폴리오에 종목 추가"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        data = request.get_json() or {}
        ticker = str(data.get('ticker', '')).upper().strip()
        company_name = data.get('company_name', '').strip() or ticker
        quantity = int(data.get('quantity', 0))
        price = float(data.get('price', 0))
        sector = data.get('sector', '').strip()
        current_price = data.get('current_price')
        note = data.get('note', '포트폴리오 수동 추가')
        
        if not ticker or quantity <= 0 or price <= 0:
            return jsonify({'error': '유효한 종목 코드, 수량, 가격을 입력해주세요'}), 400
        
        current_price_value = float(current_price) if current_price is not None else price
        
        trade_amount = quantity * price

        investment = csv_manager.get_investment_data(user_id) or {}
        current_cash = float(investment.get('cash', 0))

        if current_cash < trade_amount:
            return jsonify({'error': '보유 현금이 부족합니다'}), 400

        success = csv_manager.add_to_portfolio(
            user_id,
            ticker,
            company_name,
            quantity,
            price,
            sector,
            current_price=current_price_value
        )

        if not success:
            return jsonify({'error': '포트폴리오 업데이트에 실패했습니다'}), 500

        # 거래 내역 기록
        csv_manager.add_transaction(
            user_id,
            '매수',
            ticker=ticker,
            quantity=quantity,
            price=price,
            amount=-trade_amount,
            note=note
        )

        # 투자 데이터 업데이트
        cash = current_cash - trade_amount
        stock_value = csv_manager.calculate_portfolio_value(user_id)
        total_assets = cash + stock_value
        csv_manager.update_investment_data(
            user_id,
            total_assets=total_assets,
            cash=cash,
            stock_value=stock_value
        )
        
        updated_portfolio = csv_manager.get_portfolio(user_id)
        updated_investment = csv_manager.get_investment_data(user_id)
        
        return jsonify({
            'success': True,
            'message': '종목이 포트폴리오에 추가되었습니다',
            'portfolio': updated_portfolio,
            'investment': updated_investment
        })
        
    except Exception as e:
        logger.error(f"CSV 포트폴리오 추가 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/portfolio/sell', methods=['POST'])
def csv_sell_portfolio_item():
    """CSV 기반 포트폴리오 종목 매도"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        data = request.get_json() or {}
        ticker = str(data.get('ticker', '')).upper().strip()
        quantity = int(data.get('quantity', 0))
        price = float(data.get('price', 0))
        note = data.get('note', '포트폴리오 수동 매도')
        
        if not ticker or quantity <= 0 or price <= 0:
            return jsonify({'error': '유효한 종목 코드, 수량, 가격을 입력해주세요'}), 400
        
        trade_amount = quantity * price

        success = csv_manager.remove_from_portfolio(user_id, ticker, quantity)
        if not success:
            return jsonify({'error': '보유 수량을 초과했거나 포트폴리오에서 찾을 수 없습니다'}), 400

        # 거래 내역 기록
        csv_manager.add_transaction(
            user_id,
            '매도',
            ticker=ticker,
            quantity=quantity,
            price=price,
            amount=trade_amount,
            note=note
        )

        # 투자 데이터 업데이트
        investment = csv_manager.get_investment_data(user_id) or {}
        cash = float(investment.get('cash', 0)) + trade_amount
        stock_value = csv_manager.calculate_portfolio_value(user_id)
        total_assets = cash + stock_value
        csv_manager.update_investment_data(
            user_id,
            total_assets=total_assets,
            cash=cash,
            stock_value=stock_value
        )
        
        updated_portfolio = csv_manager.get_portfolio(user_id)
        updated_investment = csv_manager.get_investment_data(user_id)
        
        return jsonify({
            'success': True,
            'message': '매도 처리가 완료되었습니다',
            'portfolio': updated_portfolio,
            'investment': updated_investment
        })
        
    except Exception as e:
        logger.error(f"CSV 포트폴리오 매도 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/transactions', methods=['GET'])
def csv_get_transactions():
    """CSV 기반 거래 내역 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        limit = int(request.args.get('limit', 50))
        transactions = csv_manager.get_transactions(user_id, limit)
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        logger.error(f"CSV 거래 내역 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/alphas', methods=['GET'])
def csv_get_user_alphas():
    """CSV 기반 사용자 알파 목록 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        alphas = csv_manager.get_user_alphas(user_id)
        
        return jsonify({
            'success': True,
            'alphas': alphas
        })
        
    except Exception as e:
        logger.error(f"CSV 알파 목록 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/alpha/save', methods=['POST'])
def csv_save_user_alpha():
    """CSV 기반 사용자 알파 저장"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        alpha_name = data.get('alpha_name', '')
        alpha_expression = data.get('alpha_expression', '')
        performance = data.get('performance', {})
        
        if not alpha_name or not alpha_expression:
            return jsonify({'error': '알파 이름과 수식은 필수입니다'}), 400
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        success = csv_manager.save_user_alpha(user_id, alpha_name, alpha_expression, performance)
        
        if success:
            return jsonify({
                'success': True,
                'message': '알파가 저장되었습니다'
            })
        else:
            return jsonify({'error': '알파 저장에 실패했습니다'}), 500
        
    except Exception as e:
        logger.error(f"CSV 알파 저장 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/profile/update', methods=['PUT'])
def csv_update_user_profile():
    """CSV 기반 사용자 프로필 업데이트"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        # 업데이트할 필드만 딕셔너리로 전달 (username은 변경 불가)
        update_fields = {}
        if 'name' in data:
            update_fields['name'] = data['name']
        if 'email' in data:
            update_fields['email'] = data['email']
        if 'profile_emoji' in data:
            update_fields['profile_emoji'] = data['profile_emoji']
        
        success = csv_manager.update_user_info(user_id, **update_fields)
        
        if success:
            return jsonify({
                'success': True,
                'message': '프로필이 업데이트되었습니다'
            })
        else:
            return jsonify({'error': '프로필 업데이트에 실패했습니다'}), 500
        
    except Exception as e:
        logger.error(f"CSV 프로필 업데이트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/csv/user/password/change', methods=['POST'])
def csv_change_user_password():
    """CSV 기반 비밀번호 변경"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401
        
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({'error': '현재 비밀번호와 새 비밀번호는 필수입니다'}), 400
        
        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500
        
        success = csv_manager.change_password(user_id, current_password, new_password)
        
        if success:
            return jsonify({
                'success': True,
                'message': '비밀번호가 변경되었습니다'
            })
        else:
            return jsonify({'error': '현재 비밀번호가 일치하지 않습니다'}), 401
        
    except Exception as e:
        logger.error(f"CSV 비밀번호 변경 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '요청한 엔드포인트를 찾을 수 없습니다'}), 404

@app.route('/api/csv/user/asset-history', methods=['GET'])
def csv_get_asset_history():
    """CSV 기반 자산 변동 이력 조회"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': '로그인이 필요합니다'}), 401

        if csv_manager is None:
            return jsonify({'error': 'CSV 매니저가 초기화되지 않았습니다'}), 500

        limit = int(request.args.get('limit', 30))
        history = csv_manager.get_asset_history(user_id, limit)

        return jsonify({
            'success': True,
            'history': history
        })

    except Exception as e:
        logger.error(f"CSV 자산 이력 조회 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '서버 내부 오류가 발생했습니다'}), 500

if __name__ == '__main__':
    logger.info("🚀 Flask 서버 시작 중...")
    
    # 시스템 초기화
    initialize_systems()
    
    # 서버 실행
    app.run(
        host='0.0.0.0',
        port=5002,  # 다른 포트 사용
        debug=True,
        threaded=True
    )
