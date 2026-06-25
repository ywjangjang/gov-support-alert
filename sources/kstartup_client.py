"""K-스타트업(k-startup.go.kr) Open API 클라이언트.

인증키는 공공데이터포털 "창업진흥원_K-Startup 조회서비스"(data.go.kr/data/15125364/openapi.do)에서 발급받습니다.
"""
import xml.etree.ElementTree as ET

import requests

API_URL = "https://nidapi.k-startup.go.kr/api/kisedKstartupService/v1/getAnnouncementInformation"


def fetch_announcements(api_key, page=1, per_page=50):
    params = {"serviceKey": api_key, "page": page, "perPage": per_page}
    response = requests.get(API_URL, params=params, timeout=20)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    results = []
    for item in root.iter("item"):
        fields = {col.get("name"): (col.text or "").strip() for col in item.findall("col") if col.get("name")}

        if fields.get("rcrt_prgs_yn") == "N":
            continue  # 모집 종료된 공고는 제외

        title = fields.get("biz_pbanc_nm")
        if not title:
            continue

        ann_id = fields.get("pbanc_sn") or title
        results.append({
            "id": f"K스타트업-{ann_id}",
            "source": "K-스타트업",
            "title": title,
            "agency": fields.get("pbanc_ntrp_nm"),
            "end_date": fields.get("pbanc_rcpt_end_dt"),
            "region": fields.get("supt_regin"),
            "target": fields.get("aply_trgt_ctnt"),
            "url": fields.get("detl_pg_url"),
        })
    return results
