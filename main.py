import streamlit as st

from sidebar import render_sidebar
from pages.asset_dashboard import render_asset_dashboard
from pages.correlation_analysis import render_correlation_analysis
from pages.sentiment_news import render_sentiment_news

st.set_page_config(
    page_title="자산 데이터 분석 대시보드",
    layout="wide"
)

menu = render_sidebar()

if menu == "① 주요 자산 현황 대시보드":
    render_asset_dashboard()

elif menu == "② 위험자산–안전자산 상관관계 분석":
    render_correlation_analysis()

elif menu == "③ 시장 심리 및 뉴스 분석":
    render_sentiment_news()