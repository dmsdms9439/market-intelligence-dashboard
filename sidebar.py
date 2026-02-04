import streamlit as st


def render_sidebar():
    st.sidebar.title("📊 Market Menu")

    menu = st.sidebar.radio(
        "메뉴 선택",
        [
            "① 주요 자산 현황 대시보드",
            "② 위험자산–안전자산 상관관계 분석",
            "③ 시장 심리 및 뉴스 분석",
        ],
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Data Source: Bloomberg / FRED / News API")

    return menu
