"""서울산업진흥원(SBA) 지원사업 공고 스크래핑.

목록 페이지는 ASP.NET WebForms(GridView)로 렌더링되고, 공고 제목 링크는 onClick 핸들러로
PostingDetail.aspx를 호출하는 방식이라 href가 따로 없습니다. 행 인덱스별로 흩어진
hidden input/span의 id 패턴(new_displayId_N, new_name_N 등)을 정규식으로 묶어서 추출합니다.
"""
import re

import requests

LIST_URL = "https://www.sba.seoul.kr/Pages/BusinessApply/Posting.aspx"
DETAIL_URL = "https://www.sba.seoul.kr/Pages/BusinessApply/PostingDetail.aspx?p=0&mid={mid}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_announcements():
    response = requests.get(LIST_URL, headers=HEADERS, timeout=20)
    response.raise_for_status()
    html = response.text

    guids = dict(re.findall(r'new_displayId_(\d+)"\s+value="([0-9a-fA-F-]+)"', html))
    titles = dict(re.findall(r'new_name_(\d+)">([^<]*)</span>', html))
    types = dict(re.findall(r'lb_apply_templatename_(\d+)">([^<]*)</span>', html))
    ends = dict(re.findall(r'lb_receipt_end_(\d+)">([^<]*)</span>', html))

    results = []
    for idx, title in titles.items():
        title = title.strip()
        if not title:
            continue
        mid = guids.get(idx)
        results.append({
            "id": f"서울SBA-{mid or title}",
            "source": "서울SBA",
            "title": title,
            "agency": "서울산업진흥원(SBA)",
            "end_date": ends.get(idx, "").strip() or None,
            "region": "서울특별시",
            "target": types.get(idx, "").strip() or None,
            "url": DETAIL_URL.format(mid=mid) if mid else LIST_URL,
        })
    return results
