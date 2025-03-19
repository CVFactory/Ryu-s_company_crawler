import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import json
import pandas as pd

# ------------------------------
# 1. 설정 (키워드 & 깊이 & 필터링)
# ------------------------------
max_depth = 2  # 크롤링 깊이 2로 제한
visited_urls = set()  # 방문한 URL 저장

# 크롤링 제외할 URL 패턴
EXCLUDE_URLS = [
    "login", "signin", "signup", "register", "user", "account", "profile",
    "password", "mypage", "session", "search", "apply", "cart", "recruit",
    "faq", "help", "terms", "privacy", "support", "subsid", "policy",
    "guide", "myform", "email", "phoneBook", "process", "return",
    "로그인", "회원가입", "비밀번호", "계정", "아이디", "고객센터",
    "문의", "이용약관", "개인정보처리방침", "약관", "법적고지", "자주 묻는 질문",
    "도움말", "지원하기", "채용 공고", "채용 절차", "이메일 문의",
    "채용 FAQ", "온라인 문의", "자주 하는 질문", "연락처"
]

# 크롤링할 주요 URL 패턴
TARGET_KEYWORDS = [
    "about", "vision", "mission", "values", "culture", "philosophy",
    "our-story", "who-we-are", "strategy", "sustainability", "esg",
    "corporate", "ethics", "principles", "history", "leadership",
    "careers", "people", "insight", "story", "team", "life",
    "company", "identity", "responsibility", "commitment",
    "work", "growth", "innovation", "environment", "future",
    "비전", "미션", "핵심가치", "철학", "가치", "목표", "전략",
    "비전선언문", "기업소개", "윤리", "기업 윤리", "사회적 책임",
    "지속 가능성", "환경", "윤리 강령", "리더십", "성장", "혁신",
    "기업문화", "조직문화", "근무 환경", "일하는 방식", "기업가정신",
    "팀워크", "경영이념", "인재상", "핵심 인재", "조직문화",
    "채용 철학", "일하기 좋은 회사", "우리의 가치"
]

# 크롤링 후 제거할 단어 목록
EXCLUDE_WORDS = [
    "로그인", "아이디", "비밀번호", "회원가입", "검색", "채용공고",
    "지원하기", "인재 등록", "공고", "상시지원", "채용 안내"
]

# ------------------------------
# 2. Selenium 설정
# ------------------------------
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=3")
chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

webdriver_path = r"C:\Users\kci01\chromedriver.exe"
service = Service(webdriver_path)

# ------------------------------
# 3. 정적/동적 페이지 감지
# ------------------------------
def detect_page_type(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            html = response.text
            if html.count("<script") > 5:
                return "dynamic"
            return "static"
    except requests.exceptions.RequestException:
        return "dynamic"
    return "static"

# ------------------------------
# 4. 불필요한 문장 제거
# ------------------------------
def clean_text(text):
    return "\n".join([line for line in text.split("\n") if not any(word in line for word in EXCLUDE_WORDS)])

# ------------------------------
# 5. 정적 페이지 크롤링
# ------------------------------
def crawl_static(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if response.status_code != 200:
            return "", ""

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        return clean_text(text), soup
    except requests.exceptions.RequestException:
        return "", None

# ------------------------------
# 6. 동적 페이지 크롤링
# ------------------------------
def crawl_dynamic(url):
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    text = soup.get_text(" ", strip=True)
    return clean_text(text), soup

# ------------------------------
# 7. 재귀 크롤링 함수
# ------------------------------
def recursive_crawl(url, depth=1):
    if url in visited_urls or depth > max_depth:
        return []

    visited_urls.add(url)
    print(f"[Depth {depth}] 크롤링 중: {url}")

    page_type = detect_page_type(url)
    if page_type == "static":
        page_text, soup = crawl_static(url)
    else:
        page_text, soup = crawl_dynamic(url)

    extracted_pages = []
    if page_text:
        extracted_pages.append({"url": url, "content": page_text})

    if soup:
        for link in soup.find_all("a", href=True):
            sub_url = link["href"]

            if sub_url.startswith("/"):
                sub_url = url.rstrip("/") + sub_url

            if any(exclude in sub_url.lower() for exclude in EXCLUDE_URLS):
                print(f"제외된 URL: {sub_url}")
                continue

            if not any(keyword in sub_url.lower() for keyword in TARGET_KEYWORDS):
                print(f"스킵된 URL (관련 없음): {sub_url}")
                continue

            if sub_url.startswith("http") and sub_url not in visited_urls:
                extracted_pages += recursive_crawl(sub_url, depth + 1)

    return extracted_pages

# ------------------------------
# 8. 크롤링 실행
# ------------------------------
base_url = "https://www.samsungcareers.com"
data = recursive_crawl(base_url, depth=1)

# ------------------------------
# 9. 데이터 저장
# ------------------------------
df = pd.DataFrame(data)
df.to_csv("crawled_pages.csv", index=False)

json_data = {"pages": data}
with open("crawled_pages.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False, indent=4)

print(f"크롤링 완료! {len(data)}개의 페이지 저장됨.")