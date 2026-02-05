from __future__ import annotations

import streamlit as st
import pandas as pd
import yfinance as yf

_PERIOD_MAP: dict[str, str] = {
    '1W':'5d',
    '1M':'1mo',
    '3M':'3mo',
    '6M':'6mo',
    '1Y':'1y'
}

# yfinance에서 종가(Close) 로드해서 index=DatetimeIndex, colums=ticker 형태로 변환

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: list[str], period: str) -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    
    yf_period = _PERIOD_MAP.get(period,'3mo')
        
    try:
        df = yf.download(
            tickers=tickers,
            period=yf_period,
            auto_adjust=False,
            progress=False,
            group_by='column',
            threads=True
        )

    except Exception as e:
        st.warning(f'데이터 로딩 실패: {e}')
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()
    
    try:
        if isinstance(df.columns, pd.MultiIndex):
            prices = df['Close'].copy()
        else:
            close = df['Close']
            prices = close.to_frame(name=tickers[0])

    except Exception:
        return pd.DataFrame()
    
    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()
    prices = prices.ffill().dropna(how='all')

    return prices


# 전일 종가 대비 수익률
def calc_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    return prices.pct_change().dropna(how="all")


# 누적 수익률
def calc_period_returns(prices: pd.DataFrame) -> pd.Series:
    """기간 수익률(%) = (마지막/처음 - 1) * 100"""
    if prices is None or prices.empty or len(prices) < 2:
        return pd.Series(dtype="float64")
    first = prices.iloc[0]
    last = prices.iloc[-1]
    out = (last / first - 1.0) * 100.0
    out.name = "period_return_pct"
    return out