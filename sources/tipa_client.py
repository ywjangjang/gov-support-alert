"""중소기업기술정보진흥원(TIPA) R&D 사업공고 스크래핑."""
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.smtech.go.kr/front/ifg/no/notice02_list.do"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_announcements():
    response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # 같은 클래스(tbl_base tbl_type01)를 쓰는 로그인 팝업 테이블이 더 앞에 있어, caption으로 구분한다.
    table = next(
        (t for t in soup.select("table.tbl_base.tbl_type01") if "목록" in (t.caption.get_text() if t.caption else "")),
        None,
    )
    if table is None:
        return []

    results = []
    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        link = cells[3].find("a")
        if link is None:
            continue
        title = link.get_text(strip=True)
        if not title:
            continue

        href = re.sub(r";jsessionid=[^?]*", "", link.get("href", ""))
        ancm_id_match = re.search(r"ancmId=([^&]+)", href)
        ann_id = ancm_id_match.group(1) if ancm_id_match else title
        detail_url = urljoin(LIST_URL, href) if href and not href.startswith("javascript:") else LIST_URL

        period = cells[4].get_text(strip=True)
        end_date = period.split("~")[-1].strip() if "~" in period else None

        results.append({
            "id": f"TIPA-{ann_id}",
            "source": "TIPA",
            "title": title,
            "agency": cells[2].get_text(strip=True) or "중소기업기술정보진흥원",
            "end_date": end_date,
            "region": None,  # 전국 대상 R&D 사업
            "target": None,
            "url": detail_url,
        })
    return results
