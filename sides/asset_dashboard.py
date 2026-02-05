from __future__ import annotations

import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# =============================================================================
# 설정
# =============================================================================

ASSETS = {
    "S&P 500": "^GSPC",
    "Gold": "GLD",
    "US Bond": "TLT",
    "Dollar Index": "DX-Y.NYB",
    "Bitcoin": "BTC-USD",
    "QQQ": "QQQ",
}

TICKER_TO_NAME = {v: k for k, v in ASSETS.items()}

# yfinance period 문자열을 그대로 사용
YF_PERIODS = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]

# =============================================================================
# 데이터 로딩 & 계산
# =============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(tickers: list[str], yf_period: str) -> pd.DataFrame:
    """
    yfinance에서 종가(Close)만 로드해서
    index=DatetimeIndex, columns=ticker 형태로 반환
    """
    if not tickers:
        return pd.DataFrame()

    try:
        df = yf.download(
            tickers=tickers,
            period=yf_period,   # ✅ 매핑 없이 그대로 사용
            auto_adjust=False,
            progress=False,
            group_by="column",
            threads=True,
        )
    except Exception as e:
        st.warning(f"데이터 로딩 실패: {e}")
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    try:
        if isinstance(df.columns, pd.MultiIndex):
            prices = df["Close"].copy()
        else:
            # 단일 티커인 경우
            close = df["Close"]
            prices = close.to_frame(name=tickers[0])
    except Exception:
        return pd.DataFrame()

    prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()
    prices = prices.ffill().dropna(how="all")
    return prices


def calc_daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    if prices is None or prices.empty:
        return pd.DataFrame()
    return prices.pct_change().dropna(how="all")


def calc_period_returns(prices: pd.DataFrame) -> pd.Series:
    if prices is None or prices.empty or len(prices) < 2:
        return pd.Series(dtype="float64")

    first = prices.iloc[0]
    last = prices.iloc[-1]
    out = (last / first - 1.0) * 100.0
    out.name = "period_return_pct"
    return out


# =============================================================================
# 차트
# =============================================================================

def plot_price_line(
    prices: pd.DataFrame,
    label_map: dict[str, str],
    normalize: bool = True,
) -> None:
    if prices is None or prices.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    df = prices.copy()
    if normalize:
        df = df / df.iloc[0] * 100.0

    fig, ax = plt.subplots(figsize=(10, 4))

    for ticker in df.columns:
        label = label_map.get(ticker, ticker)
        ax.plot(df.index, df[ticker], label=label, linewidth=1.8)

    ax.set_title("자산별 종가 추이")
    ax.set_ylabel("Index (Start=100)" if normalize else "Price")
    ax.grid(alpha=0.25)

    ax.legend(
        loc="upper left",
        ncols=3,
        fontsize=9,
        frameon=False,
    )

    ax.tick_params(axis="x", labelsize=8)
    ax.tick_params(axis="y", labelsize=9)

    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)


def plot_period_return_bar(
    period_returns: pd.Series,
    label_map: dict[str, str],
    color_mode: str = "기본",
) -> None:
    if period_returns is None or period_returns.empty:
        st.info("표시할 수익률 데이터가 없습니다.")
        return

    # ---- 색상 결정 ----
    if color_mode == "수익률 +/-":
        colors = [
            "#2ca02c" if v >= 0 else "#d62728"
            for v in period_returns.values
        ]

    elif color_mode == "자산별":
        ASSET_COLORS = {
            "S&P 500": "#4C72B0",
            "Gold": "#DD8452",
            "US Bond": "#55A868",
            "Dollar Index": "#C44E52",
            "Bitcoin": "#8172B3",
        }
        colors = [
            ASSET_COLORS.get(label_map.get(ticker, ""), "#4C72B0")
            for ticker in period_returns.index
        ]

    else:  # 기본
        colors = "#4C72B0"

    # ---- 차트 ----
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(period_returns.index, period_returns.values, color=colors)

    ax.set_title("기간 수익률 (%)")
    ax.set_ylabel("%")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.3)

    ax.tick_params(axis="x", labelrotation=0, labelsize=9)
    ax.tick_params(axis="y", labelsize=9)

    fig.tight_layout()
    st.pyplot(fig, clear_figure=True)


# =============================================================================
# 페이지 렌더링
# =============================================================================

def render_asset_dashboard():
    st.title("① 주요 자산 현황")
    st.caption("선택한 자산들의 가격 흐름과 기간 수익률을 비교합니다.")

    # ---------------- UI ----------------
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        with col1:
            selected_assets = st.multiselect(
                "자산",
                options=list(ASSETS.keys()),
                default=["S&P 500","Gold"],
            )

        with col2:
            yf_period = st.selectbox(
                "기간",
                YF_PERIODS,
                index=1,  # "1mo"
            )

        with col3:
            normalize = st.checkbox(
                "정규화 (시작=100)",
                value=True,
            )
        with col4:
            bar_color_mode = st.selectbox(
                "수익률 색상",
                options=["기본", "수익률 +/-", "자산별"],
                index=1,
        )
            
    selected_tickers = [ASSETS[a] for a in selected_assets] if selected_assets else []
    if not selected_tickers:
        st.info("자산을 1개 이상 선택해 주세요.")
        return

    # ticker → 자산명 (범례/표시용)
    label_map = {ASSETS[a]: a for a in selected_assets}

    # ---------------- 데이터 로딩 ----------------
    with st.spinner("가격 데이터를 불러오는 중..."):
        prices = load_prices(selected_tickers, yf_period)

    if prices is None or prices.empty:
        st.warning("선택한 자산/기간에 대한 데이터가 없습니다.")
        return

    # ---------------- 계산 ----------------
    daily_returns = calc_daily_returns(prices)

    # ticker index
    period_returns = calc_period_returns(prices)

    # ✅ 표시용: 자산명 index로 변환 + 정렬
    period_returns_named = (
        period_returns.rename(index=label_map)
        .sort_values(ascending=False)
    )

    # ---------------- KPI ----------------
    st.subheader("요약 지표")

    last_prices = prices.iloc[-1]
    volatility = (daily_returns.std() * 100) if not daily_returns.empty else pd.Series(dtype="float64")

    # ✅ 정합성 있게 하나로 모아서, 자산명으로 rename
    kpi = pd.DataFrame({
        "Last Close": last_prices,
        "Period Return (%)": period_returns,
        "Volatility (%)": volatility,
    })

    # 자산명 인덱스로 변환
    kpi.index = kpi.index.map(lambda t: label_map.get(t, t))

    # 보기 좋게 Period Return 기준 정렬
    if "Period Return (%)" in kpi.columns:
        kpi = kpi.sort_values("Period Return (%)", ascending=False)

    # 여러 자산도 보기 좋게 "4개씩 줄바꿈"으로 metric 표시
    items = list(kpi.iterrows())
    chunk = 4
    for start in range(0, len(items), chunk):
        row_items = items[start:start + chunk]
        cols = st.columns(len(row_items))
        for col, (name, row) in zip(cols, row_items):
            pr = row.get("Period Return (%)")
            vol = row.get("Volatility (%)")
            col.metric(
                label=name,
                value=f"{pr:.2f}%" if pd.notna(pr) else "N/A",
                delta=f"{vol:.2f}% vol" if pd.notna(vol) else None,
            )

    # ---------------- 차트 ----------------
    st.divider()
    st.subheader("종가 추이")
    plot_price_line(prices, label_map=label_map, normalize=normalize)

    st.divider()
    st.subheader("기간 수익률 (%)")
    plot_period_return_bar(period_returns, label_map=label_map, color_mode=bar_color_mode,)

    # ---------------- 데이터 확인 ----------------
    with st.expander("데이터 미리보기"):
        st.caption("Prices (Close)")
        st.dataframe(prices.tail(10))
        st.caption("Daily Returns")
        st.dataframe(daily_returns.tail(10))
        st.caption("Period Returns (%)")
        st.dataframe(period_returns_named.to_frame("Period Return (%)"))
