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
import html

# 1. 네이버 API 설정
NAVER_CLIENT_ID = "8xWG51_vAzI7wHiEjYB4"
NAVER_CLIENT_SECRET = "xIiND03IGe"


@st.cache_data(ttl=3600)
def get_vix_data():
    """공포지수(VIX) 데이터 가져오기"""
    try:
        # period='1mo'로 변경하여 최근 한 달 추이를 가져오기.
        vix = yf.download("^VIX", period="1mo", progress=False)

        if not vix.empty and len(vix) >= 2:
            current_vix = vix["Close"].iloc[-1]
            prev_vix = vix["Close"].iloc[-2]
            delta = current_vix - prev_vix

            # 현재값, 등락폭, 그리고 그래프용 히스토리(전체 데이터) 반환
            return float(current_vix), float(delta), vix["Close"]
    except Exception as e:
        print(f"VIX Fetch Error: {e}")
        pass
    return None, None, None


def clean_html(text):
    """
    네이버 뉴스 결과에서 HTML 태그 제거 및 특수문자 완벽 복원
    """
    clean = re.sub(r"<[^>]*>", "", text)  # 1. 정규식을 이용한 HTML 태그 제거
    clean = html.unescape(clean)  # 2. HTML 엔티티 복원 (&quot; -> ", &amp; -> & 등)
    clean = clean.strip()  # 3. 추가적인 공백 정돈 (필요 시)
    return clean


@st.cache_data(ttl=3600)
def get_naver_news(keyword="특징주", display=100):
    """네이버 뉴스 검색 API 호출"""
    url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display={display}&sort=sim"
    N_A = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    res = req.get(url, headers=N_A)
    my_json = json.loads(res.text)

    # --- 원본 코드의 필터링 및 출력 루프 ---
    filtered_list = []  # 필터링된 결과를 담을 리스트
    cnt = 1

    for i in my_json.get("items", []):
        # 네이버 뉴스 플랫폼 링크(n.news.naver)가 있는 경우만 처리
        if "n.news.naver" in i.get("link", ""):
            # 콘솔 출력
            print("Count :", str(cnt))
            print("Title :", i.get("title"))
            print("Link :", i.get("link"))
            print("Description :", i.get("description"))
            print()

            # 리스트에 추가 (나중에 데이터로 쓸 수 있게)
            filtered_list.append(i)
            cnt += 1

    return filtered_list  # 필터링된 리스트 반환


def get_unique_companies(news_items):
    """
    [핵심 기능] 뉴스 제목에서 첫 번째 단어(기업명)를 추출해 중복 제거
    """
    unique_list = []
    seen_companies = set()

    for item in news_items:
        # 1. 태그 및 HTML 제거
        title = clean_html(item["title"])

        # 2. [특징주] 같은 대괄호 삭제
        title_no_tag = re.sub(r"\[.*?\]", "", title)
        title_no_tag = re.sub(r"\(.*?\)", "", title_no_tag)

        # 3. 특수문자 제거 후 공백 정리
        clean_t = re.sub(r"[^\w\s]", " ", title_no_tag).strip()

        if not clean_t:
            continue

        # 4. 첫 단어 추출 (이게 보통 기업명)
        words = clean_t.split()
        if not words:
            continue

        company_name = words[0]  # 예: '이마트', '넥센타이어'

        # 5. 중복 아니면 추가
        if company_name not in seen_companies:
            unique_list.append(item)
            seen_companies.add(company_name)

    return unique_list


def render_sentiment_news():

    def wcChart(news_items):
        """
        뉴스 제목의 패턴을 분석해 '종목명'만 추출하여 워드클라우드 생성
        """
        try:
            stock_names = []

            # 워드클라우드에서 뺄 단어들 (혹시 첫 단어로 나오더라도 무시)
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
                # 1. HTML 태그 및 기사 말머리([...]) 제거
                title = clean_html(item["title"])
                title = re.sub(r"\[.*?\]", "", title)  # [특징주] 제거
                title = re.sub(r"\(.*?\)", "", title)  # (종합) 제거

                # 2. 특수문자 제거 (쉼표, 따옴표 등을 공백으로)
                # 예: "삼성전자, SK하이닉스" -> "삼성전자  SK하이닉스"
                title = re.sub(r"[^\w\s]", " ", title).strip()

                if not title:
                    continue

                # 3. 단어 분리
                words = title.split()
                if not words:
                    continue

                # 4. [핵심] 맨 앞의 단어 1~2개만 가져오기
                # 보통 첫 번째 단어가 종목명이지만, "삼성전자 SK하이닉스"처럼 두 개가 올 수도 있음
                # 여기서는 안전하게 '첫 번째 단어'만 가져와서 종목명으로 간주
                candidate = words[0]

                # 5. 글자 수 2개 이상이고, 금지어(STOPWORDS)에 없으면 종목으로 인정
                if len(candidate) >= 2 and candidate not in STOPWORDS:
                    stock_names.append(candidate)

            # 6. 빈도수 계산 (Counter 활용)
            # 텍스트 뭉치가 아니라 {'삼성전자': 5, '카카오': 3} 형태의 데이터 생성
            counts = Counter(stock_names)

            # 7. 상위 30개 종목만 추출
            top_stocks = dict(counts.most_common(30))

            # 8. 워드클라우드 생성 (generate_from_frequencies 사용)
            try:
                img = Image.open("data/background_2.png")
                my_mask = np.array(img)
            except:
                my_mask = None

            wc = WordCloud(
                font_path=r"C:\Windows\Fonts\Gulim.ttc",
                background_color="white",
                max_words=30,  # 종목 30개만 깔끔하게
                mask=my_mask,
                colormap="Dark2",  # 글자가 진하게 잘 보이는 색상 테마
                contour_color="black",
                contour_width=2,
                normalize_plurals=False,  # 단어 변형 방지
            ).generate_from_frequencies(
                top_stocks
            )  # [중요] 빈도수 데이터로 생성

            # 그래프 출력
            fig = plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation="bilinear")
            plt.axis("off")
            st.pyplot(fig)

            # (선택사항) 어떤 종목들이 들어갔는지 터미널에서 확인하고 싶다면 주석 해제
            # print(top_stocks)

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
                st.success("☀️ 평온 (Greed)")
            elif vix_val < 30:
                st.warning("☁️ 주의 (Fear)")
            else:
                st.error("⛈️ 공포 (Extreme Fear)")

        with col2:
            # VIX 추세 그래프 (최근 1달)
            st.caption("📉 최근 1개월 VIX 추이")
            st.line_chart(vix_history, height=150, color="#FF0000")  # 붉은색 라인 차트
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

    if news_items:
        # [여기서 함수 호출] 기업별로 하나만 남긴 리스트를 받음
        unique_news = get_unique_companies(news_items)

        # 상위 8개 기업 출력
        for item in unique_news[:15]:
            title = clean_html(item["title"])
            desc = clean_html(item["description"])

            with st.expander(f"📌 {title}"):
                st.write(desc)
                st.markdown(f"[기사 원문 보기]({item['link']})")
    else:
        st.write("표시할 뉴스가 없습니다.")
