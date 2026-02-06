import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. 단위 데이터 설정 (수익용 / 손실용 분리)
# ==========================================

# 수익일 때 비교할 물건 (비싼 순)
GAIN_DATA = [
    {"name": "트라이폴드", "price": 3590000, "icon": "📱"},
    {"name": "에어팟", "price": 250000, "icon": "🎧"},
    {"name": "치킨", "price": 25000, "icon": "🍗"},
    {"name": "두쫀쿠", "price": 7000, "icon": "🍪"},
]

# 손실일 때 비교할 물건 (비싼 순)
LOSS_DATA = [
    {"name": "기둥", "price": 1000000, "icon": "🏛️"},
    {"name": "창문", "price": 250000, "icon": "🪟"},
    {"name": "치킨", "price": 25000, "icon": "🍗"},
    {"name": "두쫀쿠", "price": 7000, "icon": "🍪"},
]

# ==========================================
# 2. 유틸리티 함수들
# ==========================================


# [핵심] 금액에 맞는 가장 적절한 단위 하나 찾기
def get_best_unit(amount, data_list):
    abs_amount = abs(amount)

    # 금액에 맞는 가장 큰 단위 찾기
    for unit in data_list:
        if abs_amount >= unit["price"]:
            return unit

    # 금액이 너무 작으면 가장 작은 단위(마지막 거) 반환
    return data_list[-1]


@st.cache_data
def get_stock_list():
    try:
        df_kospi = fdr.StockListing("KOSPI")
        df_kosdaq = fdr.StockListing("KOSDAQ")

        df_kospi["Symbol"] = df_kospi["Code"] + ".KS"
        df_kosdaq["Symbol"] = df_kosdaq["Code"] + ".KQ"

        # 검색용 이름 생성: "삼성전자 (005930)"
        df_kospi["DisplayName"] = df_kospi["Name"] + " (" + df_kospi["Code"] + ")"
        df_kosdaq["DisplayName"] = df_kosdaq["Name"] + " (" + df_kosdaq["Code"] + ")"

        df_kr = pd.concat(
            [df_kospi[["DisplayName", "Symbol"]], df_kosdaq[["DisplayName", "Symbol"]]]
        )
        stock_map = dict(zip(df_kr["DisplayName"], df_kr["Symbol"]))

    except Exception as e:
        stock_map = {}

    # 미국 주식 수동 추가
    us_stocks = {
        "엔비디아 (NVDA)": "NVDA",
        "테슬라 (TSLA)": "TSLA",
        "애플 (AAPL)": "AAPL",
        "마이크로소프트 (MSFT)": "MSFT",
        "구글 (GOOGL)": "GOOGL",
        "아마존 (AMZN)": "AMZN",
        "메타 (META)": "META",
        "넷플릭스 (NFLX)": "NFLX",
        "AMD (AMD)": "AMD",
        "TSMC (TSM)": "TSM",
        "스타벅스 (SBUX)": "SBUX",
        "리얼티인컴 (O)": "O",
        "SCHD (ETF)": "SCHD",
        "TQQQ (ETF)": "TQQQ",
        "SOXL (ETF)": "SOXL",
    }
    stock_map.update(us_stocks)
    return stock_map


def format_korean_currency(amount):
    if amount >= 100000000:
        uk = int(amount // 100000000)
        man = int((amount % 100000000) // 10000)
        return f"{uk}억 {man:,}만 원" if man > 0 else f"{uk}억 원"
    elif amount >= 10000:
        return f"{int(amount // 10000):,}만 원"
    else:
        return f"{int(amount):,}원"


def render_stock_value_converter():

    # ==========================================
    # 3. 메인 UI 및 로직
    # ==========================================
    st.set_page_config(page_title="주식 환산 계산기", page_icon="🧮")

    st.title("🧮 주식 수익/손실 환산기")
    st.markdown('##### "내 돈..."')

    # 주식 목록 로드
    with st.spinner("종목 리스트 불러오는 중..."):
        STOCK_MAP = get_stock_list()

    ""
    "---"
    ""

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 입력")

        # 종목 선택 (검색 가능)
        stock_options = list(STOCK_MAP.keys())

        # 기본값 설정 ('삼성전자')
        default_index = 0
        for idx, name in enumerate(stock_options):
            if "삼성전자" in name and "005930" in name:
                default_index = idx
                break

        target_name = st.selectbox(
            "종목 선택 (타이핑해서 검색 가능)",
            stock_options,
            index=default_index,
            placeholder="종목명 입력...",
        )

        buy_date = st.date_input("매수 날짜", datetime.now() - timedelta(days=365))

        st.write("")
        st.markdown("**투자 금액**")
        invest_money = st.number_input(
            "금액",
            10000,
            1000000000,
            1000000,
            100000,
            format="%d",
            label_visibility="collapsed",
        )
        st.caption(f"💰 {format_korean_currency(invest_money)}")

        st.write("")
        btn = st.button("계산하기 🚀", use_container_width=True)

    with col2:
        st.subheader("📊 결과")

        if btn:
            ticker = STOCK_MAP[target_name]

            with st.spinner(f"{target_name} 조회 중..."):
                try:
                    df = yf.download(ticker, start=buy_date, progress=False)

                    if not df.empty:
                        start_p = float(df["Close"].iloc[0])
                        curr_p = float(df["Close"].iloc[-1])

                        # 수익률 계산
                        rate = (curr_p - start_p) / start_p
                        total_profit = invest_money * rate  # 평가손익
                        abs_profit = abs(total_profit)  # 절대값

                        # 1. 기본 정보 출력
                        st.success(f"**{target_name}**")
                        m1, m2 = st.columns(2)
                        m1.metric("수익률", f"{rate*100:.2f}%")
                        m2.metric("평가손익", f"{total_profit:,.0f}원")

                        st.divider()

                        # 2. [핵심] 수익 vs 손실에 따라 다른 리스트 적용
                        if total_profit > 0:
                            # 수익일 때 -> GAIN_DATA 사용
                            best_unit = get_best_unit(total_profit, GAIN_DATA)
                            unit_name = best_unit["name"]
                            unit_price = best_unit["price"]

                            count = abs_profit / unit_price

                            st.balloons()
                            st.markdown(f"### 🎉 **{unit_name} {count:,.1f}개** 이득!")

                            # 수익 멘트
                            if unit_name == "트라이폴드":
                                st.write(
                                    f"와우! **트라이폴드 {count:,.1f}개**를 꽁짜로!"
                                )
                            elif unit_name == "에어팟":
                                st.write(
                                    f"집에 **에어팟 {count:,.1f}개**!! 귀는 두갠데 !!!"
                                )
                            elif unit_name == "치킨":
                                st.write(
                                    f"오늘 저녁 친구들 불러서 **치킨 {count:,.1f}마리** 파티!!!!!!!!!!!"
                                )
                            else:  # 두쫀쿠
                                st.write(
                                    f"달달한 **두쫀쿠 {count:,.1f}개** 사 먹을 수 있네요!"
                                )

                        elif total_profit < 0:
                            # 손실일 때 -> LOSS_DATA 사용
                            best_unit = get_best_unit(total_profit, LOSS_DATA)
                            unit_name = best_unit["name"]
                            unit_price = best_unit["price"]

                            count = abs_profit / unit_price

                            st.snow()
                            st.markdown(
                                f"### 😭 **{unit_name} {count:,.1f}개** 증발..."
                            )

                            # 손실 멘트
                            if unit_name == "기둥":
                                st.error(
                                    f"주주님의 돈으로 회사 건물 **기둥 {count:,.1f}개**를 튼튼하게 세워주셨어요 !!!!!!!!ㅋㅋ"
                                )
                            elif unit_name == "창문":
                                st.error(
                                    f"찬바람 들지 말라고 회사 **창문 {count:,.1f}개**를 교체해 주셨군요..."
                                )
                            elif unit_name == "치킨":
                                st.error(
                                    f"직원들 야근 특식으로 **치킨 {count:,.1f}마리** 쏘셨습니다. 천사네요..."
                                )
                            else:  # 두쫀쿠
                                st.error(
                                    f"길가다 **두쫀쿠 {count:,.1f}개** 떨어뜨린 셈 칩시다..."
                                )

                        else:
                            st.info("본전입니다. 잃지 않은 것에 감사합시다! 🙏")

                    else:
                        st.warning("데이터가 없습니다. (상장 전이거나 휴일)")
                except Exception as e:
                    st.error(f"계산 중 오류 발생: {e}")
