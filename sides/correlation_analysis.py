import streamlit as st
import yfinance as yf
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import date, timedelta

# -----------------------------
# 자산 분류
# -----------------------------
ASSETS = ["BTC-USD", "^GSPC", "QQQ", "GLD", "TLT", "DX-Y.NYB"]


@st.cache_data(ttl=3600)
def load_price_data(tickers, start, end):
    df = yf.download(tickers, start=start, end=end)

    # 1️⃣ Adj Close가 있으면 사용
    if "Adj Close" in df.columns.get_level_values(0):
        price = df["Adj Close"]

    # 2️⃣ 없으면 Close 사용
    else:
        price = df["Close"]

    return price.dropna(how="all")


def calculate_daily_returns(price_df):
    """일간 수익률 계산"""
    return price_df.pct_change().dropna()


def interpret_corr(v):
    if v <= -0.3:
        return "강한 음의 상관 → 분산/헤지 효과 우수"
    elif -0.3 < v <= -0.1:
        return "약한 음의 상관 → 제한적 분산 효과"
    elif -0.1 < v < 0.1:
        return "거의 무상관 → 독립적 움직임"
    elif 0.1 <= v < 0.3:
        return "약한 양의 상관 → 동조화 가능성"
    else:
        return "강한 양의 상관 → 분산 효과 약화"


def render_correlation_analysis():
    st.title("🔗 위험자산–안전자산 상관관계 분석")

    st.markdown(
        """
        **일간 수익률 기반 상관관계 분석**
        - 위험자산과 안전자산 간의 분산 효과 확인
        - 시장 스트레스 국면에서의 관계 파악
        """
    )

    # -----------------------------
    # 기간 선택
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("시작일", value=date.today() - timedelta(days=365))

    with col2:
        end_date = st.date_input("종료일", value=date.today())

    # -----------------------------
    # 자산 선택
    # -----------------------------
    st.subheader("📌 자산 선택")

    risk_assets = st.multiselect("위험자산", options=ASSETS, default=ASSETS)

    safe_assets = st.multiselect("안전자산", options=ASSETS, default=ASSETS)

    tickers = risk_assets + safe_assets

    if len(tickers) < 2:
        st.warning("자산을 2개 이상 선택하세요.")
        return

    # -----------------------------
    # 데이터 로드 & 수익률 계산
    # -----------------------------
    price_df = load_price_data(tickers, start_date, end_date)

    if price_df.empty:
        st.error("데이터를 불러오지 못했습니다.")
        return

    returns = calculate_daily_returns(price_df)

    st.subheader("📈 선택 자산 일간 수익률")
    st.dataframe(returns.tail(10).style.format("{:.4%}"))

    # -----------------------------
    # 상관관계 계산
    # -----------------------------
    corr = returns.corr()

    # 위험자산 vs 안전자산만 추출
    corr_rs = corr.loc[risk_assets, safe_assets]

    # -----------------------------
    # 히트맵 시각화
    # -----------------------------
    st.subheader("🔥 위험자산–안전자산 상관관계 히트맵")

    x_order = corr_rs.abs().mean(axis=0).sort_values(ascending=True).index

    y_order = corr_rs.abs().mean(axis=1).sort_values(ascending=False).index

    corr_sorted = corr_rs.loc[y_order, x_order]

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        corr_sorted, annot=True, fmt=".2f", cmap="RdBu", center=0, linewidths=0.5, ax=ax
    )
    st.pyplot(fig)

    # -----------------------------
    # 히트맵 해석 요약
    # -----------------------------
    with st.expander("🧠 해석 가이드"):
        st.caption("※ 상관계수는 최근 일간 수익률 기준으로 계산됨")

        st.markdown(
            """
            - **상관계수 < 0** : 분산 효과 (헤지 가능)
            - **상관계수 ≈ 0** : 독립적 움직임
            - **상관계수 > 0** : 동조화 (리스크 증가)
            - 위기 국면에서는 상관관계가 급변할 수 있음
            """
        )

        "---"

        st.subheader("📌 시장 국면 핵심 상관관계")

        btc_gold = corr.loc["BTC-USD", "GLD"]
        eq_bond = corr.loc["^GSPC", "TLT"]
        usd_eq = corr.loc["DX-Y.NYB", "^GSPC"]
        col1, col2, col3 = st.columns(3)

        # BTC vs 금 → 디지털 금 논쟁
        with col1:
            st.metric(
                label="비트코인 ↔ 금 상관계수",
                value=f"{btc_gold:.2f}",
                help="비트코인이 금과 유사한 헤지 자산(디지털 금)으로 작동하는지 판단하는 지표",
            )

        # 주식 vs 채권 → 전통적 분산 구조 붕괴 여부
        with col2:
            st.metric(
                label="주식 ↔ 채권 상관계수",
                value=f"{eq_bond:.2f}",
                delta=(
                    "주식·채권 동반 하락 가능성"
                    if eq_bond > 0
                    else "상호 보완적 움직임"
                ),
                help="주식–채권 간 분산 투자 구조(60/40)가 정상적으로 작동하는지 판단",
            )

        # 달러 인덱스 vs 위험자산 → 리스크 오프 신호
        with col3:
            st.metric(
                label="달러 지수 ↔ 주식 상관계수",
                value=f"{usd_eq:.2f}",
                help="달러 강세 시 위험자산 회피(Risk-Off) 여부를 판단하는 지표",
            )

        st.caption(
            """
            **헤지 자산(Hedge Asset)**이란  
            보유 자산의 손실을 줄이거나 상쇄하는 역할을 하는 자산

            **일반적인 특징**
            - 위험자산과 상관관계가 낮거나 음(-)
            - 시장 위기 시 가치 유지 또는 상승
            - 충분한 유동성 보유
            """
        )

        interpretations = {
            "BTC vs Gold": {
                "value": btc_gold,
                "meaning": interpret_corr(btc_gold),
                "macro": (
                    "비트코인이 금과 동조 → 위험자산 성격 강화"
                    if btc_gold > 0.3
                    else "비트코인은 금과 독립적 → 디지털 금 논쟁 지속"
                ),
            },
            "Equity vs Bond": {
                "value": eq_bond,
                "meaning": interpret_corr(eq_bond),
                "macro": (
                    "주식–채권 분산 구조 붕괴 신호"
                    if eq_bond > 0
                    else "전통적 주식–채권 분산 구조 유지"
                ),
            },
            "USD Index vs Equity": {
                "value": usd_eq,
                "meaning": interpret_corr(usd_eq),
                "macro": (
                    "달러 강세 = Risk-Off 국면"
                    if usd_eq < -0.3
                    else "달러–주식 관계 중립"
                ),
            },
        }
        st.subheader("📌 상관관계 기반 해석")

        for k, v in interpretations.items():
            st.markdown(
                f"""
                **{k}**  
                - 상관계수: `{v['value']:.2f}`  
                - 해석: {v['meaning']}  
                - 시사점: **{v['macro']}**
                """
                "---"
            )

        ""
        "---"
        ""

        st.subheader("📌 시장 요약")

        summary = []

        if eq_bond > 0:
            summary.append("• 주식–채권 동조화로 전통적 분산 효과가 약화되고 있음")
        if usd_eq < -0.3:
            summary.append("• 달러 강세가 나타나며 위험회피 심리가 우세")
        if btc_gold < 0.1:
            summary.append(
                "• 비트코인은 금과 독립적으로 움직이며 디지털 금 성격은 제한적"
            )

        st.markdown("\n".join(summary))

    # -----------------------------
    # 산점도
    # -----------------------------
    with st.expander("📌 위험자산 vs 안전자산 산점도"):
        r = st.selectbox("위험자산 선택", risk_assets)
        s = st.selectbox("안전자산 선택", safe_assets)

        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.scatter(returns[r], returns[s], alpha=0.5)
        ax2.set_xlabel(f"{r} Daily Return")
        ax2.set_ylabel(f"{s} Daily Return")
        ax2.axhline(0, color="gray", linewidth=0.5)
        ax2.axvline(0, color="gray", linewidth=0.5)
        ax2.set_title(f"{r} vs {s}")

        st.pyplot(fig2)
