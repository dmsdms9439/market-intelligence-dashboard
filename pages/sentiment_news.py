%%writefile module/pr1cr.py

import streamlit as st
import yfinance as yf
import requests as req
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
import re
import numpy as np
from PIL import Image

# 1. 네이버 API 설정
NAVER_CLIENT_ID = '5oVXMqrseId0LObau9b9'
NAVER_CLIENT_SECRET = 'JTk7ZQRTpj'

@st.cache_data(ttl=3600)
def get_vix_data():
    """공포지수(VIX) 데이터 가져오기"""
    vix = yf.download("^VIX", period="2d")
    if not vix.empty and len(vix) >= 2:
        current_vix = vix['Close'].iloc[-1]
        prev_vix = vix['Close'].iloc[-2]
        delta = current_vix - prev_vix
        return float(current_vix), float(delta)
    return None, None

def clean_html(text):
    """네이버 뉴스 결과에서 HTML 태그 및 특수문자 제거"""
    clean = re.sub('<.*?>', '', text) # 태그 제거
    clean = re.sub('&#39;', "'", clean)
    clean = re.sub('&quot;', '"', clean)
    clean = re.sub('&amp;', '&', clean)
    return clean

@st.cache_data(ttl=3600)
def get_naver_news(query='거시경제', display=30):
    """네이버 뉴스 검색 API 호출"""
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display={display}&sort=sim"
    N_A = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    res = req.get(url, headers=N_A)
    
    if res.status_code == 200:
        items = res.json().get('items', [])
        for item in items:
            item['title'] = clean_html(item['title'])
            item['description'] = clean_html(item['description'])
        return items
    else:
        st.error(f"네이버 API 호출 실패: {res.status_code}")
        return []

def create_wordcloud(news_items):
    """뉴스 헤드라인 기반 워드클라우드 생성"""
    okt = Okt()
    all_titles = " ".join([item['title'] for item in news_items])
    
    # 명사 추출 및 불용어 제거
    nouns = okt.nouns(all_titles)
    stopwords = ['뉴스', '경제', '시장', '오늘', '날', '포토', '기자', '증시', '분석']
    words = [n for n in nouns if len(n) > 1 and n not in stopwords]
    
    count = Counter(words)
    
    # 워드클라우드 생성 (Windows는 malgun.ttf, Mac은 AppleGothic.ttf)
    # 폰트 경로가 틀리면 오류가 나니 주의하세요!
    wc = WordCloud(
        font_path="malgun.ttf", 
        background_color="white",
        width=800, height=400
    ).generate_from_frequencies(count)
    
    return wc

def wcChart(new_items, back_mask, max_words, emp):
    # 배경 이미지 선택
    if back_mask =='타원':
        img = Image.open('data/background_1.png')
    elif back_mask =='말풍선':
        img = Image.open('data/background_2.png')
    elif back_mask =='하트':
        img = Image.open('data/background_3.png')
    else :
        img = Image.open('data/background_0.png')

    my_mask = np.array(img)
    
    wc = WordCloud(
        font_path=r'C:\Windows\Fonts\Gulim.ttc',
        background_color='white',                  # 배경색 지정
        max_words=max_words,                              # 함수의 매개변수인 max_word 입력
        random_state=99,                           # 출력위치 고정 랜덤 시드값
        stopwords=['있다', '및', '수', '이', '다', 'the', 'a', 'of', 'to', 'in', 'and'], # 제외하고 싶은 단어 설정(불용어 설정)
        mask=my_mask,
        contour_color='black',
        contour_width=3)
    
    wc.generate(new_items)
    fig = plt.subplots(figsize=(10, 5))
    plt.imshow(wc, interpolation='bilinear')
    plt.axis('off')
    st.pyplot(fig)

# --- UI 렌더링 ---
st.header("🔍 시장 심리 및 뉴스 분석")

# ① VIX 지수
vix_val, vix_delta = get_vix_data()
if vix_val is not None:
    st.subheader("📊 오늘의 공포 지수 (VIX)")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric(label="VIX 지수", value=f"{vix_val:.2f}", delta=f"{vix_delta:.2f}", delta_color="inverse")
    with col2:
        if vix_val < 20:
            st.success("☀️ 시장이 평온합니다. 투자 심리가 긍정적입니다.")
        elif vix_val < 30:
            st.warning("☁️ 변동성이 커지고 있습니다. 조심스러운 접근이 필요합니다.")
        else:
            st.error("⛈️ 시장에 공포가 가득합니다! 안전 자산 확보를 권장합니다.")

st.divider()

# ② 워드클라우드
st.subheader("☁️ 뉴스 키워드 트렌드")
news_items = get_naver_news()

if news_items:
    try:
        wcChart(corpus, back_mask, max_words, emp)
    except Exception as e:
        st.info("워드클라우드를 생성하려면 한글 폰트 설정이 필요합니다.")

st.divider()

# ③ 뉴스 헤드라인 리스트
st.subheader("📰 실시간 주요 뉴스")
for item in news_items[:8]: # 8개 출력
    with st.expander(f"📌 {item['title']}"):
        st.write(item['description'])
        st.markdown(f"[기사 원문 보기]({item['link']})")