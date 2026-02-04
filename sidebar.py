import streamlit as st
from streamlit_option_menu import option_menu


def render_sidebar():
    with st.sidebar:

        menu = option_menu(
            menu_title="메뉴 선택",
            menu_icon="cast",
            options=[
                "① 주요 자산 현황 대시보드",
                "② 위험자산–안전자산 상관관계 분석",
                "③ 시장 심리 및 뉴스 분석",
            ],
            icons=["speedometer2", "bar-chart-line", "gear"],
            default_index=0,
            styles={
                # container : 메뉴 탭을 감싸는 전체공간
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "18px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#eee",
                },  # hover-마우스 오버시 색상
                "nav-link-selected": {
                    "background-color": "#02ab21"
                },  # 선택된 네비 메뉴
            },
        )
    return menu
