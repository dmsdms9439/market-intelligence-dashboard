import streamlit as st
from streamlit_option_menu import option_menu

from data.ecos import fetch_all_kpis, KpiValue


@st.cache_data(ttl=60 * 60)
def _cached_all_kpis(api_key: str):
    return fetch_all_kpis(api_key)


def _format_value(x: float | None, unit: str | None) -> str:
    if x is None:
        return "N/A"
    if unit and len(unit) <= 8:
        return f"{x:,.2f} {unit}"
    return f"{x:,.2f}"


def _format_delta(latest: float | None, prev: float | None) -> str | None:
    if latest is None or prev is None:
        return None
    return f"{latest - prev:+.2f}"


def inject_sidebar_metric_css():
    st.markdown(
        """
        <style>
        /* 사이드바 metric 전체 간격 */
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            padding: 6px 4px;
        }

        /* metric label */
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            font-size: 0.78rem;
            line-height: 1.1;
        }

        /* metric value */
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            font-size: 1.1rem;
        }

        /* metric delta */
        [data-testid="stSidebar"] [data-testid="stMetricDelta"] {
            font-size: 0.72rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_korea_kpis(api_key: str):
    inject_sidebar_metric_css()
    st.markdown("---")
    st.subheader("◾국내 핵심 지표")

    kpis = _cached_all_kpis(api_key)

    for k in kpis:
        label = k.name if not k.latest_date else f"{k.name} ({k.latest_date})"
        st.metric(
            label=label,
            value=_format_value(k.latest, k.unit),
            delta=_format_delta(k.latest, k.prev),
        )


def render_sidebar():
    with st.sidebar:
        st.header("거시경제 분석 대시보드")

        menu = option_menu(
            menu_title="menu",
            menu_icon="back",
            options=[
                "시장 현황",
                "자산 상관 분석",
                "뉴스·심리 분석",
                "현실 손익 환산기",
            ],
            icons=["1-square", "2-square", "3-square", "4-square"],
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "#77002E", "font-size": "18px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "#36454F"},
            },
        )

        api_key = "UKCOV3Q9BOBONL0LGAWI"  # 너 키 하드코딩 유지
        render_korea_kpis(api_key)
        st.markdown("---")
        st.caption("출처: 한국은행 ECOS 통계시스템")
    return menu
