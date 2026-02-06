import streamlit as st

from sidebar import render_sidebar
from sides.asset_dashboard import render_asset_dashboard
from sides.correlation_analysis import render_correlation_analysis
from sides.sentiment_news import render_sentiment_news
from sides.stock_value_converter import render_stock_value_converter

st.set_page_config(page_title="Market Intelligence Dashboard", layout="wide")

menu = render_sidebar()

if menu == "시장 현황":
    render_asset_dashboard()

elif menu == "자산 상관 분석":
    render_correlation_analysis()

elif menu == "뉴스·심리 분석":
    render_sentiment_news()

elif menu == "현실 손익 환산기":
    render_stock_value_converter()
