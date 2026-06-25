"""기업마당(bizinfo.go.kr) Open API 클라이언트.

인증키는 기업마당 자체 신청(https://www.bizinfo.go.kr/web/lay1/program/S1T175C174/apiDetail.do?id=bizinfoApi)
또는 공공데이터포털(data.go.kr)에서 발급받습니다.
"""
import xml.etree.ElementTree as ET

import requests

API_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"

# 실제 키 발급 전에는 응답을 확인할 수 없어, 문서에 적힌 후보 필드명을 모두 시도합니다.
FIELD_CANDIDATES = {
    "title": ["pblancNm", "title"],
    "id": ["pblancId", "seq"],
    "url": ["pblancUrl", "link"],
    "agency": ["jrsdInsttNm", "author"],
    "target": ["trgetNm"],
    "period": ["reqstBeginEndDe", "reqstDt"],
}


def _local_tag(tag):
    return tag.split("}")[-1]


def _extract(fields, key):
    for name in FIELD_CANDIDATES[key]:
        value = fields.get(name)
        if value:
            return value
    return None


def fetch_announcements(api_key, page_index=1, page_unit=50):
    params = {
        "crtfcKey": api_key,
        "dataType": "rss",
        "pageUnit": page_unit,
        "pageIndex": page_index,
    }
    response = requests.get(API_URL, params=params, timeout=20)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    results = []
    for item in root.iter():
        if _local_tag(item.tag) != "item":
            continue
        fields = {_local_tag(child.tag): (child.text or "").strip() for child in item}

        title = _extract(fields, "title")
        if not title:
            continue

        period = _extract(fields, "period") or ""
        end_date = period.split("~")[-1].strip() if "~" in period else None

        ann_id = _extract(fields, "id") or title
        results.append({
            "id": f"기업마당-{ann_id}",
            "source": "기업마당",
            "title": title,
            "agency": _extract(fields, "agency"),
            "end_date": end_date,
            "region": None,  # 공고 대부분이 전국 대상 중앙부처 사업이라 지역 제한 필드가 명확하지 않음
            "target": _extract(fields, "target"),
            "url": _extract(fields, "url"),
        })
    return results
