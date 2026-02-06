import streamlit as st

from sidebar import render_sidebar
from sides.asset_dashboard import render_asset_dashboard
from sides.correlation_analysis import render_correlation_analysis
from sides.sentiment_news import render_sentiment_news
from sides.stock_value_converter import render_stock_value_converter

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")

menu = render_sidebar()

if menu == "거시경제 주요 지표 현황":
    render_asset_dashboard()

elif menu == "자산별 상관관계 분석":
    render_correlation_analysis()

elif menu == "시장 심리 및 뉴스 분석":
    render_sentiment_news()

elif menu == "주식 환산 계산기":
    render_stock_value_converter()
