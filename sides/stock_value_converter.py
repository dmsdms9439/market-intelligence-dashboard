import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta

# 1. 단위 데이터 설정 (공통 사용)
# 가격은 대략적인 현재 시세 기준
UNIT_DATA = [
    {"name": "제네시스", "price": 80000000, "icon": "🚘"},
    {"name": "그랜저", "price": 40000000, "icon": "🚙"},
    {"name": "소나타", "price": 30000000, "icon": "🚕"},
    {"name": "아반떼", "price": 25000000, "icon": "🚗"},
    {"name": "트라이폴드", "price": 3500000, "icon": "📱"},
    {"name": "아이폰프맥", "price": 1900000, "icon": "📲"},  # 아이폰 16 프로맥스 기준
    {"name": "에어팟맥스", "price": 760000, "icon": "🎧"},
    {"name": "에어팟", "price": 250000, "icon": "🎵"},
    {"name": "치킨", "price": 25000, "icon": "🍗"},
    {"name": "두쫀쿠", "price": 7000, "icon": "🍪"},
]


# 2. 유틸리티 함수들
def get_best_unit(amount):
    """금액에 맞는 가장 적절한 단위 하나 찾기"""
    abs_amount = abs(amount)

    # 금액에 맞는 가장 큰 단위 찾기 (비싼 순서대로 체크)
    for unit in UNIT_DATA:
        if abs_amount >= unit["price"]:
            return unit

    # 금액이 너무 작으면 가장 작은 단위(두쫀쿠) 반환
    return UNIT_DATA[-1]


@st.cache_data
def get_stock_list():
    try:
        df_kospi = fdr.StockListing("KOSPI")
        df_kospi = df_kospi.head(50)  # 상위 50개

        df_kosdaq = fdr.StockListing("KOSDAQ")
        df_kosdaq = df_kosdaq.head(50)  # 상위 50개

        df_kospi["Symbol"] = df_kospi["Code"] + ".KS"
        df_kosdaq["Symbol"] = df_kosdaq["Code"] + ".KQ"

        df_kospi["DisplayName"] = df_kospi["Name"] + " (" + df_kospi["Code"] + ")"
        df_kosdaq["DisplayName"] = df_kosdaq["Name"] + " (" + df_kosdaq["Code"] + ")"

        df_kr = pd.concat(
            [df_kospi[["DisplayName", "Symbol"]], df_kosdaq[["DisplayName", "Symbol"]]]
        )
        stock_map = dict(zip(df_kr["DisplayName"], df_kr["Symbol"]))

    except Exception as e:
        stock_map = {}

    # 미국 주식 및 기타 종목 추가
    custom_stocks = {
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
        "금양 (001570)": "001570.KS",
        "나라소프트 (384500)": "384500.KS",
    }
    stock_map.update(custom_stocks)

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


# 3. 메인 화면 렌더링 함수
def render_stock_value_converter():
    st.title("🧮 주식 수익/손실 환산기")
    st.markdown('##### "내 돈... 대체 뭘 한 거지?"')

    with st.spinner("종목 리스트 불러오는 중..."):
        STOCK_MAP = get_stock_list()

    st.divider()

    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader("📝 입력")

        stock_options = list(STOCK_MAP.keys())
        default_index = 0
        for idx, name in enumerate(stock_options):
            if "삼성전자" in name and "005930" in name:
                default_index = idx
                break

        target_name = st.selectbox(
            "종목 선택",
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
            10000000000,
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

                        # 계산 로직: (현재 평가금액) - (투자 원금)
                        total_value = (invest_money / start_p) * curr_p
                        net_profit = total_value - invest_money
                        rate = (curr_p - start_p) / start_p

                        abs_profit = abs(net_profit)

                        # 1. 수치 출력
                        st.success(f"**{target_name}**")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("수익률", f"{rate*100:.2f}%")
                        c2.metric("총 평가액", f"{format_korean_currency(total_value)}")
                        c3.metric("순수익", f"{net_profit:,.0f}원")

                        st.divider()

                        # 2. 아이템 비교 로직 (공통 UNIT_DATA 사용)
                        best_unit = get_best_unit(net_profit)
                        unit_name = best_unit["name"]
                        unit_price = best_unit["price"]
                        count = abs_profit / unit_price
                        # (A) 수익일 때 멘트
                        if net_profit > 0:
                            st.balloons()
                            st.markdown(
                                f"### 🎉 **{unit_name} {count:,.1f}개** 벌었습니다!"
                            )

                            if unit_name == "제네시스":
                                st.write(
                                    f"와우.. **G80 {count:,.1f}대** 출고 가능합니다! 회장님!"
                                )
                            elif unit_name == "그랜저":
                                st.write(
                                    f"성공의 상징 **그랜저가 {count:,.1f}대**! 부자되셨네요."
                                )
                            elif unit_name == "소나타":
                                st.write(
                                    f"국민 세단 **소나타 {count:,.1f}대** 값입니다. 든든하네요."
                                )
                            elif unit_name == "아반떼":
                                st.write(
                                    f"사회초년생의 드림카 **아반떼 {count:,.1f}대** 획득!"
                                )
                            elif unit_name == "트라이폴드":
                                st.write(
                                    f"세 번 접는 폰 **트라이폴드 {count:,.1f}개** 살 수 있어요!"
                                )
                            elif unit_name == "아이폰프맥":
                                st.write(
                                    f"최신형 **아이폰 프맥 {count:,.1f}개** 겟! 카메라가 몇 개야?"
                                )
                            elif unit_name == "에어팟맥스":
                                st.write(
                                    f"귀에 얹는 사치 **에어팟 맥스 {count:,.1f}개** 가능!"
                                )
                            elif unit_name == "에어팟":
                                st.write(
                                    f"**에어팟 {count:,.1f}개**! 귀는 두 개뿐인데.. 선물하시죠!"
                                )
                            elif unit_name == "치킨":
                                st.write(
                                    f"오늘 골든벨 울립시다! **치킨 {count:,.1f}마리** 파티!"
                                )
                            else:  # 두쫀쿠
                                st.write(
                                    f"소소하지만 확실한 행복.. **두쫀쿠 {count:,.1f}개** 냠냠!"
                                )

                        # 손실일 때 멘트
                        elif net_profit < 0:
                            st.snow()
                            st.markdown(
                                f"### 😭 **{unit_name} {count:,.1f}개** 날렸습니다..."
                            )

                            if unit_name == "제네시스":
                                st.error(
                                    f"주주님 덕분에 대주주가 **제네시스 {count:,.1f}대** 새로 뽑으셨답니다.."
                                )
                            elif unit_name == "그랜저":
                                st.error(
                                    f"방금 길에 지나가는 **그랜저 {count:,.1f}대**.. 그거 님 돈입니다.."
                                )
                            elif unit_name == "소나타":
                                st.error(
                                    f"택시 탈 때마다 생각나겠네요. 내 **소나타 {count:,.1f}대**.."
                                )
                            elif unit_name == "아반떼":
                                st.error(
                                    f"사회초년생 차 **아반떼 {count:,.1f}대**를 그냥 공중분해 시키셨군요.."
                                )
                            elif unit_name == "트라이폴드":
                                st.error(
                                    f"폰은 접어도 되지만 계좌는 접으면 안 되는데.. **트라이폴드 {count:,.1f}개** 증발.."
                                )
                            elif unit_name == "아이폰프맥":
                                st.error(
                                    f"사과 농장에 기부하셨습니다. **아이폰 프맥 {count:,.1f}개** 안녕.."
                                )
                            elif unit_name == "에어팟맥스":
                                st.error(
                                    f"노이즈 캔슬링이 필요해요. 잔소리 안 들리게.. **에어팟 맥스 {count:,.1f}개**.."
                                )
                            elif unit_name == "에어팟":
                                st.error(
                                    f"길가다 하수구에 **에어팟 {count:,.1f}개** 빠뜨린 기분.."
                                )
                            elif unit_name == "치킨":
                                st.error(
                                    f"전 직원 야근 간식 **치킨 {count:,.1f}마리** 화끈하게 쏘셨습니다."
                                )
                            else:  # 두쫀쿠
                                st.error(
                                    f"편의점 갈 때마다 눈물 날 듯.. **두쫀쿠 {count:,.1f}개** 떨어뜨림.."
                                )

                        else:
                            st.info("본전입니다. 잃지 않은 것에 감사합시다! 🙏")

                    else:
                        st.warning("데이터가 없습니다. (상장 전이거나 휴일)")
                except Exception as e:
                    st.error(f"계산 중 오류 발생: {e}")
