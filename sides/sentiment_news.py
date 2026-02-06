import streamlit as st
import yfinance as yf
import requests as req
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import html
import re
from wordcloud import WordCloud
from PIL import Image
from collections import Counter


# 1. 네이버 API 설정
NAVER_CLIENT_ID = "5oVXMqrseId0LObau9b9"
NAVER_CLIENT_SECRET = "JTk7ZQRTpj"


# ================ 함수 선언 ==================
@st.cache_data(ttl=3600)  # 1시간동안 캐싱
def get_vix_data():
    # 공포지수 데이터 가져오기
    try:
        vix = yf.download("^VIX", period="6mo")
        if not vix.empty and len(vix) >= 2:
            # 가져온 데이터가 비어있으면 안됨
            # 전날과 오늘의 비교를 해야하므로 최소 2개
            current_vix = vix["Close"].iloc[-1]  # 가장 최근 종가 데이터
            prev_vix = vix["Close"].iloc[-2]  # 그 전날 종가 데이터
            delta = current_vix - prev_vix  # 변동폭

            # 현재값, 변동폭, 전체데이터
            return float(current_vix), float(delta), vix["Close"]
    except Exception as e:
        print(f"VIX ERROR : {e}")


def clean_html(text):
    # 네이버 뉴스 결과에서 HTML 태그 제거, 특수문자 복원
    clean = re.sub(r"<[^>]*>", "", text)  # 정규식으로 태그 제거
    clean = html.unescape(clean)  # 특수문자 암호로 된 것 복원
    clean = clean.strip()  # 공백 제거
    return clean


@st.cache_data(ttl=3600)
def get_naver_news(keyword="특징주", display=100):
    # 네이버 뉴스 검색 API 호출
    url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display={display}&sort=sim"
    N_A = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    res = req.get(url, headers=N_A)
    my_json = json.loads(res.text)  # 딕셔너리로 변환

    filtered_list = []  # 정제된 뉴스 담을 리스트
    cnt = 1

    for i in my_json.get("items", []):
        # 네이버 뉴스 링크가 있는 경우만 처리
        if "n.news.naver" in i.get("link", ""):
            # 리스트에 추가
            filtered_list.append(i)
            cnt += 1
    return filtered_list


def get_unique_companies(news_items):
    # 뉴스 제목에서 첫번째 단어를 추출해 중복 제거
    unique_list = []
    seen_companies = set()  # 중복된 기업을 기억해두는 집합

    for item in news_items:
        # clen 함수로 태그, html 제거
        clean_title = clean_html(item["title"])
        clean_desc = clean_html(item["description"])

        # item에 정제된 내용으로 교체
        item["title"] = clean_title
        item["description"] = clean_desc

        # 기업명이 아니라 기사 맨 앞 [단독], [특징주]들이 나와 대괄호 덩어리 지우기
        title_for_extract = re.sub(r"\[.*?\]", "", clean_title)
        title_for_extract = re.sub(r"\(.*?\)", "", title_for_extract)
        clean_t = re.sub(r"[^\w\s]", " ", title_for_extract).strip()

        if not clean_t:
            continue  # 제목을 다 지웠을 때 아무것도 안남았다면 다음 뉴스로 넘어가기

        words = clean_t.split()  # 띄어쓰기 기준으로 토막내기
        if not words:
            continue

        company_name = words[0]  # 맨 앞에 있는 단어를 기업 이름으로 간주

        # 중복인 기업명 집합에 넣기
        if company_name not in seen_companies:
            unique_list.append(item)
            seen_companies.add(company_name)

    return unique_list


def render_sentiment_news():

    def wcChart(news_items):
        # 종목명만 추출해 워드클라우드 생성
        try:
            stock_names = []

            # 불용어 설정
            STOPWORDS = [
                "특징주",
                "오전",
                "오후",
                "장중",
                "마감",
                "속보",
                "종합",
                "급등",
                "급락",
                "상승",
                "하락",
                "강세",
                "약세",
                "코스피",
                "코스닥",
                "증시",
                "단독",
                "주식",
                "ET특징주",
                "포토",
                "투자",
                "공시",
                "뉴스",
                "투데이",
            ]
            for item in news_items:
                # 1. HTML 태그 및 기사
                title = clean_html(item["title"])
                title = re.sub(r"\[.*?\]", "", title)  # [특징주] 제거
                title = re.sub(r"\(.*?\)", "", title)  # (종합) 제거
                # 2. 특수문자 제거
                title = re.sub(r"[^\w\s]", " ", title).strip()
                if not title:
                    continue
                # 3. 단어 분리
                words = title.split()
                if not words:
                    continue

                # 4. 맨 앞의 단어 1개만 가져와서 종목명으로 간주
                candidate = words[0]

                # 5. 글자 수 2개 이상이고, 금지어(STOPWORDS)에 없으면 종목으로 인정
                if len(candidate) >= 2 and candidate not in STOPWORDS:
                    stock_names.append(candidate)

            # 6. 빈도수 계산 (Counter 활용)
            # 텍스트 뭉치가 아니라 {'삼성전자': 5, '카카오': 3} 형태의 데이터 생성
            counts = Counter(stock_names)

            # 7. 상위 30개 종목만 추출
            top_stocks = dict(counts.most_common(30))

            # 8. 워드클라우드 생성
            try:
                img = Image.open("data/background_2.png")
                my_mask = np.array(img)
            except:
                my_mask = None

            wc = WordCloud(
                font_path=r"C:\Windows\Fonts\Gulim.ttc",
                background_color="white",
                max_words=30,  # 종목 30개만
                mask=my_mask,
                colormap="Dark2",
                contour_color="black",
                contour_width=2,
                normalize_plurals=False,  # 단어 변형 방지
            )

            wc.generate_from_frequencies(top_stocks)  # 빈도수 데이터로 생성
            # 그래프 출력
            fig = plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            st.pyplot(fig)

        except Exception as e:
            st.error(f"워드클라우드 에러: {e}")

    # --- UI 렌더링 ---
    st.header("🔍 시장 심리 및 뉴스 분석")

    # ① VIX 지수
    vix_val, vix_delta, vix_history = get_vix_data()

    if vix_val is not None:
        st.subheader("📊 오늘의 공포 지수 (VIX)")

        # 1:2 비율로 컬럼 분할 (왼쪽: 수치, 오른쪽: 그래프)
        col1, col2 = st.columns([1, 2])

        with col1:
            st.metric(
                label="VIX 지수",
                value=f"{vix_val:.2f}",
                delta=f"{vix_delta:.2f}",
                delta_color="inverse",
            )
            # 상태 메시지 표시
            if vix_val < 20:
                st.success("☀️ 자 드가자")
            elif vix_val < 30:
                st.warning("☁️ 하고싶으면 해보세요 ㅋㅋ")
            else:
                st.error(
                    "🚨 차트보면서 땀흘리면 운동 많이 될거야..스트레스 많이 받을거야.. "
                )

        with col2:
            # VIX 추세 그래프 (최근 1달)
            st.caption("📉 최근 1개월 VIX 추이")
            st.line_chart(vix_history, height=150, color="#FF0000")  # 붉은색 라인 차트

    ""
    "---"
    ""

    # ② 워드클라우드
    st.subheader("☁️ 오느릐 관심 종목들")  # 주의깊게 봐야할 회사

    news_items = get_naver_news()

    if news_items:
        try:
            data_amount = st.slider("가져올 뉴스 개수", 1, 50, 10)
            wcChart(news_items)
        except Exception as e:
            st.warning(f"워드클라우드 생성 실패: {e}")

    ""
    "---"
    ""

    # ③ 뉴스 헤드라인 리스트
    st.subheader("📰 실시간 주요 뉴스")

    if news_items:
        # 기업별로 하나만 남긴 리스트를 받음
        unique_news = get_unique_companies(news_items)

        # 상위 15개 기업 출력
        for item in unique_news[:15]:
            with st.expander(f"📌 {item['title']}"):
                st.write(item["description"])
                st.markdown(f"[기사 원문 보기]({item['link']})")
    else:
        st.write("표시할 뉴스가 없습니다.")
