from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf
import plotly.graph_objects as go


plt.rcParams["font.family"] = "Malgun Gothic"   # Windows
plt.rcParams["axes.unicode_minus"] = False

# =============================================================================
# 설정
# =============================================================================

ASSETS = {
    "S&P 500": "^GSPC",
    "Gold": "GC=F",
    "Gold ETF":"GLD",
    "US Bond": "TLT",
    "Bitcoin": "BTC-USD",
    "QQQ": "QQQ",
}

ASSET_COLORS = {
    "S&P 500": "#243A5E",
    "QQQ": "#2F7F7F",
    "Gold": "#7A8F3B",
    "Gold ETF": "#8B3A3A",
    "US Bond": "#6B5B95",
    "Bitcoin": "#B07A3B",
}

TICKER_TO_NAME = {v: k for k, v in ASSETS.items()}

# yfinance period 문자열을 그대로 사용
YF_PERIODS = ["5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "20y", "40y"]

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
            period=yf_period, 
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
    if prices is None or prices.empty:
        return pd.Series(dtype="float64")

    first = prices.apply(lambda s: s.dropna().iloc[0] if s.dropna().size else np.nan)
    last  = prices.apply(lambda s: s.dropna().iloc[-1] if s.dropna().size else np.nan)

    out = (last / first - 1.0) * 100.0
    out.name = "period_return_pct"
    return out
# =============================================================================
# 차트
# =============================================================================

import plotly.graph_objects as go

def plot_price_line_plotly(prices: pd.DataFrame, label_map: dict[str, str], normalize: bool=True):
    if prices is None or prices.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    df = prices.copy()
    if normalize:
        base = df.apply(lambda s: s.dropna().iloc[0] if s.dropna().size else np.nan)
        df = df.divide(base, axis=1) * 100.0

    fig = go.Figure()

    for ticker in df.columns:
        name = label_map.get(ticker, ticker)
        color = ASSET_COLORS.get(name, None)

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[ticker],
                mode="lines",
                name=name,
                line=dict(width=2, color=color),
                hovertemplate="%{x|%Y-%m-%d}<br><b>%{y:.2f}</b><extra>"+name+"</extra>",
            )
        )

    fig.update_layout(
        title="자산별 종가 추이",
        xaxis_title="Date",
        yaxis_title="Index (Start=100)" if normalize else "Price",
        hovermode="x unified",   # 한 날짜 기준으로 툴팁 묶어서 보여줌
        legend_title_text="자산",
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )

    # range slider(하단 미니 타임라인) 원하면 True
    fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True)

import plotly.express as px

def plot_period_return_bar_plotly(period_returns: pd.Series, label_map: dict[str,str], color_mode: str="기본"):
    if period_returns is None or period_returns.empty:
        st.info("표시할 수익률 데이터가 없습니다.")
        return

    s = period_returns.rename(index=label_map).sort_values(ascending=False)
    df = s.reset_index()
    df.columns = ["Asset", "ReturnPct"]

    # 색상 컬럼 만들기
    if color_mode == "수익률 +/-":
        df["Color"] = np.where(df["ReturnPct"] >= 0, "Up", "Down")
        fig = px.bar(df, x="Asset", y="ReturnPct", color="Color", text="ReturnPct")
    elif color_mode == "자산별":
        df["Color"] = df["Asset"].map(lambda a: ASSET_COLORS.get(a, "#4C72B0"))
        fig = px.bar(df, x="Asset", y="ReturnPct", text="ReturnPct")
        # 자산별 고정 색 적용 (plotly는 discrete 색을 강제하려면 트릭이 필요해서 간단 버전은 아래처럼)
        fig.update_traces(marker_color=df["Color"])
    else:
        fig = px.bar(df, x="Asset", y="ReturnPct", text="ReturnPct")

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y:.2f}%<extra></extra>",
    )

    fig.update_layout(
        title="자산별 기간 수익률",
        yaxis_title="%",
        xaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10),
        height=420,
    )
    fig.add_hline(y=0)

    st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# 페이지 렌더링
# =============================================================================

def render_asset_dashboard():
    st.title("🪙 거시경제 주요 지표 현황")
    st.caption("선택한 자산의 가격 추이와 기간 수익률을 비교합니다.")

    # ---------------- UI ----------------
    with st.container():
        col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

        with col1:
            selected_assets = st.multiselect(
                "자산 선택",
                options=list(ASSETS.keys()),
                default=["S&P 500","US Bond"],
            )

        with col2:
            yf_period = st.selectbox(
                "기간 선택",
                YF_PERIODS,
                index=1,  # "1mo"
            )

        with col3:
            normalize = st.checkbox(
                "지수화 (시작=100)",
                value=True,
                help="모든 자산의 시작 시점을 100으로 맞춰 수익률을 비교합니다."
            )
        with col4:
            bar_color_mode = st.selectbox(
                "수익률 색상 테마",
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
    st.subheader("☞ 현재가")

    last_close = prices.iloc[-1]
    prev_close = prices.shift(1).iloc[-1]          # 전일(전 거래일) 종가
    day_change_pct = (last_close / prev_close - 1) * 100

    # 변동성은 그대로 쓰고 싶으면 유지
    vol = daily_returns.std() * 100 if not daily_returns.empty else pd.Series(dtype="float64")

    # 공통 인덱스 정합
    idx = prices.columns
    last_close = last_close.reindex(idx)
    day_change_pct = day_change_pct.reindex(idx)
    vol = vol.reindex(idx)

    # ✅ 보기 좋게: 전일대비 내림차순 정렬 (원하면 last_close 기준으로 바꿔도 됨)
    order = day_change_pct.sort_values(ascending=False).index

    cols = st.columns(len(order))
    for col, ticker in zip(cols, order):
        name = label_map.get(ticker, ticker)

        lc = last_close.get(ticker)
        dc = day_change_pct.get(ticker)
        v = vol.get(ticker)

        # 숫자 포맷(자산별로 다르게 하고 싶으면 여기서 분기 가능)
        value_str = f"{lc:,.2f}" if pd.notna(lc) else "N/A"
        delta_str = f"{dc:+.2f}%" if pd.notna(dc) else None

        col.metric(
            label=name,
            value=value_str,
            delta=delta_str,
            help=f"변동성(일간 표준편차): {v:.2f}%" if pd.notna(v) else None
        )

    # ---------------- 차트 ----------------
    tabs = st.tabs(["📈 가격 추이(USD)", "📊 기간 수익률(%)"])

    with tabs[0]:
        st.markdown("자산 가격이 시간에 따라 어떻게 변해왔는지(흐름)를 보여줍니다. "
            "☑️지수화(시작=100)를 켜면 자산 간 **상대 성과**를 더 쉽게 비교할 수 있어요."
        )
        
        plot_price_line_plotly(prices, label_map=label_map, normalize=normalize)
        with st.expander("💡 해석 팁\n"):
            st.info(
                "- **기울기**: 성과(상대적으로 더 빠르게 오르거나 내림)\n"
                "- **흔들림(진폭)**: 변동성(체감 위험)\n"
                "- 선이 **같이 움직이면** 동조, **갈라지면** 시장의 선택(리스크 온/오프) 신호일 수 있어요."
            )
    with tabs[1]:
        st.markdown("선택한 기간의 **시작 대비 현재**가 몇 % 변했는지 요약한 결과입니다. "
            "자산별 성과를 한 번에 비교할 때 유용해요."
        )
        
        plot_period_return_bar_plotly(period_returns, label_map=label_map, color_mode=bar_color_mode)
        with st.expander("💡 해석 팁\n"):
            st.info(
                "- 기간 수익률은 **결과 요약**이에요. (과정은 ‘가격 추이’에서 확인)\n"
                "- **수익률 +/-** 모드: 상승/하락 방향을 빠르게 파악\n"
                "- **자산별** 모드: 자산 정체성(색상)을 유지해 비교가 쉬워요."
            )
    # ---------------- 데이터 확인 ----------------
    with st.expander("데이터 미리보기"):
        st.caption("Prices (Close)")
        st.dataframe(prices.tail(10))
        st.caption("Daily Returns")
        st.dataframe(daily_returns.tail(10))
        st.caption("Period Returns (%)")
        st.dataframe(period_returns_named.to_frame("Period Return (%)"))
