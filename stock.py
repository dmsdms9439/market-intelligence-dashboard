import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 1. 페이지 설정 (제목, 아이콘 등)
st.set_page_config(page_title="주식 대시보드", page_icon="📈")

st.title("📈 실시간 주식 데이터 대시보드")
st.write("관심 있는 미국 주식(티커)을 입력하면 실시간 차트를 보여줍니다.")

# 2. 사이드바: 사용자 입력 받기
st.sidebar.header("검색 옵션")
ticker = st.sidebar.text_input("종목 코드 입력 (예: AAPL, TSLA, MSFT)", value="AAPL")
period = st.sidebar.selectbox("조회 기간", ["5d", "1mo", "6mo", "1y"])


# 3. 데이터 가져오기 함수 (API 연동)
# @st.cache_data는 데이터를 캐싱해서 속도를 높여줍니다.
def get_stock_data(ticker, period):
    try:
        # yfinance API를 통해 데이터 다운로드 (Pandas DataFrame 반환)
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        return df, stock.info
    except:
        return None, None


# 4. 버튼을 누르면 데이터 조회 시작
if st.button("주가 확인하기"):
    with st.spinner("데이터를 불러오는 중..."):
        # 함수 호출
        df, info = get_stock_data(ticker, period)
        print(df.head(10))

    # 데이터가 정상적으로 있다면 화면 그리기
    if df is not None and not df.empty:
        # (1) 현재가 및 등락폭 표시 (Metric)
        current_price = df["Close"].iloc[-1]  # 가장 최근 종가
        prev_price = df["Close"].iloc[-2]  # 전일 종가
        diff = current_price - prev_price  # 변동액
        diff_pct = (diff / prev_price) * 100  # 변동률

        col1, col2 = st.columns(2)
        with col1:
            st.subheader(f"{info.get('shortName', ticker)}")
        with col2:
            st.metric(
                label="현재가 (USD)",
                value=f"${current_price:.2f}",
                delta=f"{diff:.2f} ({diff_pct:.2f}%)",
            )

        # (2) 차트 그리기 (Line Chart)
        st.subheader("📊 주가 변동 차트")
        st.line_chart(df["Close"])

        # (3) 데이터 표로 보기 (Pandas DataFrame)
        with st.expander("상세 데이터(DataFrame) 보기"):
            st.write("API에서 받아온 원본 데이터입니다.")
            st.dataframe(df.sort_index(ascending=False))

        # (4) 간단한 통계 보여주기
        st.info(
            f"선택한 기간 동안의 최고가는 ${df['High'].max():.2f}, 최저가는 ${df['Low'].min():.2f} 입니다."
        )

    else:
        st.error(
            "종목 코드를 확인해주세요! (예: 애플->AAPL, 테슬라->TSLA, 비트코인->BTC-USD)"
        )
