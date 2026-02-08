import streamlit as st
import yfinance as yf
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import date, timedelta

# -----------------------------
# 자산 분류
# -----------------------------
ASSETS = ["Bitcoin", "S&P 500", "QQQ", "Gold", "US Bond", "USD Index"]
TICK = ["BTC-USD", "^GSPC", "QQQ", "GC=F", "TLT", "DX-Y.NYB"]

ASSETS_TO_TICK = {
    "Bitcoin": "BTC-USD",
    "S&P 500": "^GSPC",
    "QQQ": "QQQ",
    "Gold": "GC=F",
    "US Bond": "TLT",
    "USD Index": "DX-Y.NYB",
}

TICK_TO_ASSETS = {
    "BTC-USD": "Bitcoin",
    "^GSPC": "S&P 500",
    "QQQ": "QQQ",
    "GC=F": "Gold",
    "TLT": "US Bond",
    "DX-Y.NYB": "USD Index",
}


@st.cache_data(ttl=3600)
def load_price_data(tickers, start, end):
    df = yf.download(tickers, start=start, end=end, interval="1wk")

    # 1️⃣ Adj Close가 있으면 사용
    if "Adj Close" in df.columns.get_level_values(0):
        price = df["Adj Close"]

    # 2️⃣ 없으면 Close 사용
    else:
        price = df["Close"]

    return price.dropna(how="all")


def calculate_daily_returns(price_df):
    """주간 수익률 계산"""
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

    st.info(
        """
        **주간 수익률 기반 상관관계 분석**
        - 위험자산과 안전자산 간의 분산 효과 확인
        - 시장 스트레스 국면에서의 관계 파악
        """
    )

    # -----------------------------
    # 기간 선택
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("시작일", value=date.today() - timedelta(days=180))

    with col2:
        end_date = st.date_input("종료일", value=date.today())

    # -----------------------------
    # 자산 선택
    # -----------------------------
    st.subheader("📌 자산 선택")

    st.markdown(
        """
            <style>
            .asset-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 16px;
            }
            .asset-table th {
                text-align: left;
                padding: 10px;
                border-bottom: 2px solid #333;
            }
            .asset-table td {
                padding: 12px 10px;
                border-bottom: 1px solid #ddd;
            }
            .risk {
                color: #d62728;
                font-weight: bold;
            }
            .safe {
                color: #1f77b4;
                font-weight: bold;
            }
            </style>

            <table class="asset-table">
                <tr>
                    <th>자산 분류</th>
                    <th>해당 자산</th>
                    <th>특징</th>
                </tr>
                <tr>
                    <td class="risk">위험자산 (Risk-On)</td>
                    <td>Bitcoin, S&P 500, QQQ</td>
                    <td>시장 유동성 및 성장 기대감에 민감하게 반응, 높은 변동성 수반</td>
                </tr>
                <tr>
                    <td class="safe">안전자산 (Risk-Off)</td>
                    <td>Gold, US Bond, USD Index</td>
                    <td>경제 불확실성 확대 시 가치 보존 수단, 위험자산과 반대 경향</td>
                </tr>
            </table>
        """,
        unsafe_allow_html=True,
    )
    assets = st.multiselect(
        "ASSETS",
        options=list(ASSETS_TO_TICK.keys()),
        default=list(ASSETS_TO_TICK.keys()),
    )

    if len(assets) < 2:
        st.warning("자산을 2개 이상 선택하세요.")
        return
    # -----------------------------
    # 데이터 로드 & 수익률 계산
    # -----------------------------
    price_df = load_price_data(TICK, start_date, end_date)

    if price_df.empty:
        st.error("데이터를 불러오지 못했습니다.")
        return

    returns = calculate_daily_returns(price_df).rename(columns=TICK_TO_ASSETS)

    st.subheader("📈 선택 자산 주간 수익률")
    st.dataframe(returns[assets].tail(100).style.format("{:.4%}"))

    # -----------------------------
    # 상관관계 계산
    # -----------------------------
    corr = returns.corr()

    corr_rs = corr.loc[assets, assets]

    # -----------------------------
    # 히트맵 시각화
    # -----------------------------
    st.subheader("🔥 위험자산–안전자산 상관관계 히트맵")

    x_order = corr_rs.abs().mean(axis=0).sort_values(ascending=False).index
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

        st.subheader("📌 시장 요약")

        btc_gold = corr.loc["Bitcoin", "Gold"]
        eq_bond = corr.loc["S&P 500", "US Bond"]
        usd_eq = corr.loc["USD Index", "S&P 500"]
        summary = []

        if eq_bond > 0:
            summary.append("• 주식–채권 동조화로 **분산 효과가 약화**되고 있음")
        if usd_eq < -0.3:
            summary.append(
                "• **달러와 주식간의 자금 이동이 뚜렷**하게 나타나며 **주식 상승 · 달러 약세** 에는 **위험 선호(Risk-on)**, **주식 하락 · 달러 강세** 때는 **위험 회피(Risk-off)**가 예측됨"
            )
        if btc_gold < 0.1:
            summary.append(
                "• **비트코인은 금과 독립적**으로 움직이며 디지털 금 성격은 제한적"
            )
        if not summary:
            summary.append(
                """
                분석 결과 자산 간 관계가 강하게 나타나지 않았습니다. 
                대부분의 자산 쌍은 완전히 같은 방향이나 반대 방향으로 움직이기보다는, 약하거나 독립적인 관계를 보였습니다. 
                """
            )
        st.markdown("\n\n".join(summary))

        st.divider()

        st.subheader("📌 시장 국면 핵심 상관관계")
        col1, col2, col3 = st.columns(3)

        # BTC vs 금 → 디지털 금 논쟁
        with col1:
            st.metric(
                label="1. Bitcoin ↔ Gold 상관계수",
                value=f"{btc_gold:.2f}",
                help="Bitcoin이 Gold과 유사한 디지털 금으로 작동하는지 판단하는 지표",
            )

        # 주식 vs 채권 → 전통적 분산 구조 붕괴 여부
        with col2:
            st.metric(
                label="2. 주식 ↔ 채권 상관계수",
                value=f"{eq_bond:.2f}",
                delta=(
                    "주식·채권 동반 하락 가능성"
                    if eq_bond > 0
                    else "상호 보완적 움직임"
                ),
                help="주식–채권 간 분산 투자 구조가 정상적으로 작동하는지 판단",
            )

        # 달러 인덱스 vs 위험자산 → 리스크 오프 신호
        with col3:
            st.metric(
                label="3. 달러 ↔ 주식 상관계수",
                value=f"{usd_eq:.2f}",
                help="달러 강세 시 위험자산 회피(Risk-Off) 여부를 판단하는 지표",
            )
        ""
        st.caption("※ 상관계수는 최근 주간 수익률 기준으로 계산됨")

        interpretations = {
            "Bitcoin vs Gold": {
                "value": btc_gold,
                "meaning": interpret_corr(btc_gold),
                "macro": (
                    "비트코인이 금과 동조 → ‘디지털 금’으로서의 대체 가능성은 적으며 위험자산 성격 강화"
                    if btc_gold > 0.3
                    else "비트코인은 전통적 안전자산인 금과 뚜렷한 동조 관계를 보이지 않음"
                ),
                "caption": """
                    추가 설명:
                    - 비트코인은 상황에 따라 변동 → 안전자산 대체 기능은 불확실
                    👉 비트코인은 금의 대체재라기보다는 독립적인 위험 자산
                """,
            },
            "주식(S&P 500) vs 채권(US Bond)": {
                "value": eq_bond,
                "meaning": interpret_corr(eq_bond),
                "macro": (
                    "주식–채권 분산 구조 붕괴 신호"
                    if eq_bond > 0
                    else "전통적 주식–채권 분산 구조 유지"
                ),
                "caption": """
                    일반적인 상황:
                    - 주식 ↓ → 채권 ↑
                    👉 자산 분산 효과 (Diversification)
                    \n
                    문제가 되는 상황:
                    - 주식 ↑, 채권 ↑ (또는 둘 다 ↓)
                    👉 분산 구조 붕괴
                """,
            },
            "달러(USD Index) vs 주식(S&P 500)": {
                "value": usd_eq,
                "meaning": interpret_corr(usd_eq),
                "macro": (
                    "달러와 주식 자금 이동이 강화"
                    if usd_eq < -0.3
                    else "달러–주식 관계 중립"
                ),
                "caption": """
                    일반적인 상황:
                    - 시장 불안 → 달러 ↑ / 주식 ↓
                    - 시장 안정 → 달러 ↓ / 주식 ↑
                """,
            },
        }

        st.divider()

        st.subheader("📌 상관관계 기반 해석")

        for k, v in interpretations.items():
            st.markdown(
                f"""
                **{k}**  
                - 상관계수: `{v['value']:.2f}`  
                - 의미: {v['meaning']}  
                - 해석: **{v['macro']}**
                """
            )

            st.caption(f"{v['caption']}")

            st.divider()

        st.markdown(
            """
            - |상관계수| < 0.1 : 독립적 움직임
            - 0.1 ≤ |상관계수| < 0.3 : 약한 의미 관계
            - **상관계수 <= -0.3** : 분산 효과 (hedge, Risk-Off)
            - **상관계수 >= 0.3** : 자산의 동조화 (Risk-On)

            \n\n
            관계위기 국면에서는 상관관계가 급변할 수 있음
            """
        )

        st.divider()

        st.caption(
            """
            헤지(Hedge)는 금융 시장에서 환율, 금리, 주가 등 자산 가격 변동에 따른 위험을 줄이기 위해 반대 방향의 포지션을 취하여 손실을 최소화하는 위험 회피 전략
            """
        )

    # -----------------------------
    # 산점도
    # -----------------------------
    with st.expander("📌 위험자산 vs 안전자산 산점도"):
        r = st.selectbox("첫번째 자산 선택", ASSETS)
        s = st.selectbox("두번째 자산 선택", ASSETS)

        fig2, ax2 = plt.subplots(figsize=(6, 4))
        sns.regplot(
            x=returns[r],
            y=returns[s],
            ci=95,
            scatter_kws={"alpha": 0.6},
            line_kws={"linewidth": 2},
            ax=ax2,
        )
        ax2.set_xlabel(f"{r} 주간 수익률")
        ax2.set_ylabel(f"{s} 주간 수익률")
        ax2.axhline(0, color="gray", linewidth=0.5)
        ax2.axvline(0, color="gray", linewidth=0.5)
        ax2.set_title(f"{r} vs {s}")

        st.pyplot(fig2)

        st.caption(
            """
            **점**은 실제 관측값, **선**은 평균적인 선형 관계,
            **음영 영역*는 해당 관계의 불확실성을 나타냅니다.
            범위가 넓을수록 관계는 예측하기 어렵습니다.
        """
        )
