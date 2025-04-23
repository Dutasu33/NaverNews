#아래의 파일은 스트림릿 및 셀크기,날짜필처 포함된 코드이다.

import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
import pandas as pd
import time
import datetime
import requests
import io
import urllib.parse

# ✅ 페이지 레이아웃 설정
st.set_page_config(layout="wide")
st.title('📰 Naver News Search')

# ✅ 사용자 입력: 검색어 + 날짜 범위
search_query = st.text_input('🔍 검색어를 입력하세요:')
today = datetime.date.today()
start_date = st.date_input("📅 시작 날짜", today - datetime.timedelta(days=7))
end_date = st.date_input("📅 종료 날짜", today)

# 검색 버튼 추가
search_button = st.button('검색 시작')

# ✅ 테이블 CSS 스타일 정의
st.markdown("""
<style>
table {
    table-layout: fixed;
    width: 100%;
    border-collapse: collapse;
}
th:nth-child(1), td:nth-child(1) {  /* 번호 */
    width: 5%;
    text-align: center;
    font-size: 0.9em;
}
th:nth-child(2), td:nth-child(2) {  /* 제목 */
    width: 30%;
}
th:nth-child(3), td:nth-child(3) {  /* 내용 */
    width: 40%;
}
th:nth-child(4), td:nth-child(4) {  /* URL */
    width: 12%;
    font-size: 0.8em;
}
th, td {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 4px;
    border: 1px solid #ddd;
}
</style>
""", unsafe_allow_html=True)

# ✅ 크롤링 실행 조건
if search_button and search_query and start_date <= end_date:
    # 날짜 포맷 변환
    start_str = start_date.strftime('%Y.%m.%d')
    end_str = end_date.strftime('%Y.%m.%d')

    # 크롬 드라이버 설정
    chrome_driver_path = r"D:\backup\Downloads\chromedriver-win64 (1)\chromedriver-win64\chromedriver.exe"
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    # 네이버 뉴스 검색 URL (날짜 필터 포함)
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://search.naver.com/search.naver?ssc=tab.news.all&query={encoded_query}&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds={start_str}&de={end_str}&docid=&related=0&mynews=0&office_type=0&office_section_code=0&news_office_checked=&nso=so:r,p:from{start_str.replace('.', '')}to{end_str.replace('.', '')}&is_sug_officeid=0&office_category=&service_area="

    # URL 출력
    st.write(f"Generated URL: {url}")

    driver.get(url)
    time.sleep(2)

    print(url)

    # 스크롤 다운으로 뉴스 추가 로딩
    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    titles, contents, urls, image_urls = [], [], [], []
    news_boxes = driver.find_elements(By.CSS_SELECTOR, "div.sds-comps-vertical-layout")

    for box in news_boxes:
        try:
            title_elem = box.find_element(By.CSS_SELECTOR, "span.sds-comps-text-ellipsis-1.sds-comps-text-type-headline1")
            content_elem = box.find_element(By.CSS_SELECTOR, "span.sds-comps-text-ellipsis-3.sds-comps-text-type-body1")
            link_elem = box.find_element(By.CSS_SELECTOR, "a.bynlPWBHumGsbotLYK9A.jT1DuARpwIlNAFMacxlu")
            image_elem = box.find_element(By.CSS_SELECTOR, "img")

            title = title_elem.text.strip()
            content = content_elem.text.strip()
            link = link_elem.get_attribute("href").strip()
            image_url = image_elem.get_attribute("src").strip()

            # 추가된 로직: 중복 확인 및 리스트에 추가
            if (title, link) not in zip(titles, urls):
                titles.append(title)
                contents.append(content)
                urls.append(link)
                image_urls.append(image_url)

        except Exception:
            continue

    driver.quit()

    # ✅ 데이터프레임 구성
    df = pd.DataFrame({
        "번호": range(1, len(titles) + 1),
        "제목": titles,
        "내용": contents,
        "URL": urls,
    })
    df = df.drop_duplicates(subset='제목', keep='first').reset_index(drop=True)

    # Limit content to two lines
    df['내용'] = df['내용'].apply(lambda x: '<br>'.join(x.split('\n')[:2]))

    # ✅ HTML용 컬럼은 따로 생성
    df['URL_HTML'] = df['URL'].apply(lambda x: f'<a href="{x}" target="_blank">기사 보기</a>')

    # ✅ Streamlit 웹에서 HTML 링크 표시 (URL 컬럼 삭제, URL_HTML 컬럼 유지)
    st.write(f"✅ 총 {len(df)}개의 뉴스가 검색되었습니다.")
    st.write(df.drop(columns=['URL']).to_html(escape=False, index=False), unsafe_allow_html=True)

    # ✅ Excel에는 HYPERLINK 함수만 들어가도록 따로 생성
    df['기사 보기'] = df['URL'].apply(lambda x: f'=HYPERLINK("{x}", "기사 보기")' if pd.notna(x) else "")

    # ❗ 엑셀에는 HTML 태그 들어가지 않게 URL_HTML 제거
    excel_df = df.drop(columns=['URL', 'URL_HTML'])

    # ✅ 엑셀 파일 생성
    excel_buffer = io.BytesIO()
    excel_df.to_excel(excel_buffer, index=False)

    # ✅ CSV 파일 생성
    csv_buffer = io.StringIO()
    excel_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')

    # 날짜를 문자열로 변환
    start_str_filename = start_date.strftime('%Y%m%d')
    end_str_filename = end_date.strftime('%Y%m%d')

    # 파일 이름에 검색어와 날짜 범위 포함
    file_name = f"네이버뉴스_{search_query}_{start_str_filename}_{end_str_filename}.xlsx"

    # ✅ 다운로드 버튼
    st.download_button(
        label="⬇️ 엑셀로 다운로드",
        data=excel_buffer.getvalue(),
        file_name=file_name,
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    # ✅ CSV 다운로드 버튼
    st.download_button(
        label="⬇️ CSV로 다운로드",
        data=csv_buffer.getvalue(),
        file_name=file_name.replace('.xlsx', '.csv'),
        mime='text/csv'
    )

# ❗ 날짜 오류 처리
elif start_date > end_date:
    st.error("❌ 종료 날짜는 시작 날짜보다 이후여야 합니다.") 