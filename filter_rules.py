"""
규칙기반 1차 적합성 판단.

각 source 클라이언트는 공고를 다음 형태의 dict로 정규화해서 넘겨야 합니다:
{
    "id": "기업마당-12345",       # 중복판단용 고유 key (source + 원본 ID)
    "source": "기업마당",
    "title": "...",
    "agency": "...",             # 소관기관
    "end_date": "2026-07-31",    # 마감일, 모르면 None
    "region": "전국" or "서울특별시" or None,   # 지원지역 원문, 제한 없으면 None
    "target": "중소기업 대상" 등 지원대상 원문,  # 모르면 None
    "url": "https://...",
}

judge()는 위 dict와 회사 프로필을 받아 {"status": "적합"|"모호"|"부적합", "reason": "..."}를 반환합니다.
나중에 LLM 2차 판단(llm_judge.py)을 추가할 때도 같은 입출력 형태를 쓰면 끼워넣기 쉽습니다.
"""

# 회사가 해당되지 않는 게 명백한 지원대상 한정 문구들
EXCLUSION_KEYWORDS = [
    "예비창업자", "예비창업패키지", "1인 기업", "소상공인 전용",
    "청년창업", "여성기업 전용", "장애인기업 전용", "사회적기업 전용",
    "농업인", "어업인", "전통시장",
    # 공고 게시판에 섞여 들어오는, 기관 자체의 채용/임원선임 공지 (지원사업이 아님)
    "신입직원", "상임이사", "이사장 공개모집", "체험형 인턴", "청년인턴",
]


def _mentions_company_region(region_text, profile):
    if not region_text:
        return True  # 지역 제한 명시 없음 -> 전국 대상으로 간주
    if "전국" in region_text:
        return True
    return any(loc in region_text for loc in profile["locations"])


def _has_exclusion(text):
    return next((kw for kw in EXCLUSION_KEYWORDS if kw in text), None)


def _euro(word):
    """받침 유무에 따라 '로'/'으로' 조사를 고른다."""
    last_char = word[-1]
    if "가" <= last_char <= "힣" and (ord(last_char) - 0xAC00) % 28 != 0:
        return "으로"
    return "로"


def judge(announcement, profile):
    title = announcement.get("title") or ""
    target = announcement.get("target") or ""
    region = announcement.get("region")
    combined_text = f"{title} {target}"

    matched_exclusion = _has_exclusion(combined_text)
    if matched_exclusion:
        return {
            "status": "부적합",
            "reason": f"지원대상이 '{matched_exclusion}'{_euro(matched_exclusion)} 한정되어 당사 조건과 맞지 않음",
        }

    if not _mentions_company_region(region, profile):
        return {
            "status": "부적합",
            "reason": f"지원지역이 '{region}'{_euro(region)} 한정되어 당사 사업장 소재지와 맞지 않음",
        }

    matched_keyword = next(
        (kw for kw in profile["interest_keywords"] if kw in combined_text), None
    )
    if matched_keyword:
        return {
            "status": "적합",
            "reason": f"관심분야 키워드 '{matched_keyword}' 포함, 지역/지원대상 제한에 걸리지 않음",
        }

    return {
        "status": "모호",
        "reason": "지역/지원대상 제한에는 걸리지 않으나 관심분야(R&D·인력채용·시설·운전자금) 키워드가 제목/대상에 명확히 보이지 않아 직접 확인 필요",
    }
