"""기술보증기금(KIBO) 공지사항 게시판 스크래핑.

채용공고 등 지원사업과 무관한 글도 섞여 있어, filter_rules.py의 관심분야 키워드
매칭에서 자연스럽게 걸러지도록 둔다(여기서는 게시판 글을 그대로 수집만 한다).
"""
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.kibo.or.kr/main/board/boardType01.do?mode=list&article.offset=0"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_announcements():
    response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    results = []
    for row in soup.select("table.board-table tbody tr"):
        link = row.select_one("td.b-td-title a")
        if link is None:
            continue
        title = link.get_text(strip=True)
        if not title:
            continue

        href = link.get("href", "")
        article_match = re.search(r"articleNo=(\d+)", href)
        ann_id = article_match.group(1) if article_match else title

        date_span = row.select_one("span.b-date")
        posted_date = date_span.get_text(strip=True) if date_span else None

        results.append({
            "id": f"기보-{ann_id}",
            "source": "기술보증기금",
            "title": title,
            "agency": "기술보증기금",
            "end_date": None,  # 공지사항 게시판이라 마감일은 본문 확인 필요
            "region": None,
            "target": None,
            "url": urljoin(LIST_URL, href),
            "posted_date": posted_date,
        })
    return results
