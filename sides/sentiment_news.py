import streamlit as st
import yfinance as yf
import requests as req
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from collections import Counter
import re
import numpy as np
from PIL import Image
import json

# 1. 네이버 API 설정
NAVER_CLIENT_ID = "5oVXMqrseId0LObau9b9"
NAVER_CLIENT_SECRET = "JTk7ZQRTpj"


@st.cache_data(ttl=3600)
def get_vix_data():
    """공포지수(VIX) 데이터 가져오기"""
    vix = yf.download("^VIX", period="2d")
    if not vix.empty and len(vix) >= 2:
        current_vix = vix["Close"].iloc[-1]
        prev_vix = vix["Close"].iloc[-2]
        delta = current_vix - prev_vix
        return float(current_vix), float(delta)
    return None, None


def clean_html(text):
    """네이버 뉴스 결과에서 HTML 태그 및 특수문자 제거"""
    clean = re.sub("<.*?>", "", text)  # 태그 제거
    clean = re.sub("&#39;", "'", clean)
    clean = re.sub("&quot;", '"', clean)
    clean = re.sub("&amp;", "&", clean)
    return clean


@st.cache_data(ttl=3600)
def get_naver_news(keyword="증권", display=30):
    """네이버 뉴스 검색 API 호출"""
    url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display={display}&sort=sim"
    N_A = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    res = req.get(url, headers=N_A)
    my_json = json.loads(res.text)  # json 형식으로 파싱
    return my_json["items"]


def render_sentiment_news():
    def wcChart(new_items):
        """뉴스 헤드라인 기반 워드클라우드 생성"""
        try:
            # 1. 배경 이미지 불러오기 및 넘파이 배열 변환
            img = Image.open("data/background_2.png")
            my_mask = np.array(img)

            # 2. 뉴스 제목들만 합쳐서 하나의 문자열로 만들기
            all_titles = " ".join([item["title"] for item in news_items])

            # 3. 워드클라우드 객체 설정
            wc = WordCloud(
                font_path=r"C:\Windows\Fonts\Gulim.ttc",
                background_color="white",
                max_words=100,
                random_state=99,
                stopwords=[
                    "뉴스",
                    "경제",
                    "시장",
                    "오늘",
                    "날",
                    "포토",
                    "기자",
                    "증시",
                    "분석",
                ],
                mask=my_mask,
                contour_color="black",
                contour_width=3,
            )

            # 4. 문자열 데이터로 워드클라우드 생성
            wc.generate(all_titles)

            # 5. 그래프
            fig = plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            st.pyplot(fig)

        except Exception as e:
            st.error(f"함수 내부 에러 발생: {e}")
            raise e

    # --- UI 렌더링 ---
    st.header("🔍 시장 심리 및 뉴스 분석")

    # ① VIX 지수
    vix_val, vix_delta = get_vix_data()
    if vix_val is not None:
        st.subheader("📊 오늘의 공포 지수 (VIX)")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.metric(
                label="VIX 지수",
                value=f"{vix_val:.2f}",
                delta=f"{vix_delta:.2f}",
                delta_color="inverse",
            )
        with col2:
            if vix_val < 20:
                st.success("☀️ 시장이 평온합니다. 투자 심리가 긍정적입니다.")
            elif vix_val < 30:
                st.warning("☁️ 변동성이 커지고 있습니다. 조심스러운 접근이 필요합니다.")
            else:
                st.error("⛈️ 시장에 공포가 가득합니다! 안전 자산 확보를 권장합니다.")

    st.divider()

    # ② 워드클라우드
    st.subheader("☁️ 뉴스 키워드 트렌드")  # 주의깊게 봐야할 회사들로 교체?

    news_items = get_naver_news()

    if news_items:
        try:
            data_amount = st.slider("가져올 뉴스 개수", 1, 50, 10)
            wcChart(news_items)
        except Exception as e:
            st.warning(f"워드클라우드 생성 실패: {e}")

    st.divider()

    # ③ 뉴스 헤드라인 리스트
    st.subheader("📰 실시간 주요 뉴스")
    for item in news_items[:8]:  # 8개 출력
        with st.expander(f"📌 {item['title']}"):
            st.write(item["description"])
            st.markdown(f"[기사 원문 보기]({item['link']})")
