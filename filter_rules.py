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

# 당사 소재지(서울/경기)와 무관한 타 지역 키워드
NON_COMPANY_REGIONS = [
    # 광역 묶음 표현
    "영남", "호남", "충청", "강원", "영호남",
    # 경상도
    "경북", "경상북도", "경남", "경상남도", "경상도",
    # 전라도
    "전북", "전라북도", "전남", "전라남도", "전라도",
    # 충청도
    "충북", "충청북도", "충남", "충청남도",
    # 강원
    "강원도", "강원특별자치도",
    # 광역시·특별자치시
    "제주", "부산", "대구", "광주", "대전", "울산", "세종", "인천",
    # 경상도 주요 도시
    "창원시", "진주시", "포항시", "경주시", "구미시", "안동시", "김해시",
    "거제시", "통영시", "사천시", "밀양시", "양산시", "거창군",
    # 전라도 주요 도시
    "전주시", "익산시", "군산시", "광양시", "여수시", "순천시", "목포시",
    # 충청도 주요 도시
    "청주시", "천안시", "아산시", "공주시", "논산시", "당진시",
    # 강원 주요 도시
    "춘천시", "원주시", "강릉시", "동해시", "속초시", "태백시",
    # 제주
    "제주시", "서귀포시",
]

# 타 지역이 나와도 이것도 함께 있으면 당사 해당 가능 (전국/수도권/당사 지역)
COMPANY_REGION_KEYWORDS = ["전국", "수도권", "서울", "경기", "화성"]

# 회사가 해당되지 않는 게 명백한 지원대상 한정 문구들
EXCLUSION_KEYWORDS = [
    "예비창업자", "예비창업패키지", "1인 기업", "소상공인 전용",
    "청년창업", "여성기업 전용", "장애인기업 전용", "사회적기업 전용",
    "농업인", "어업인", "전통시장",
    # 공고 게시판에 섞여 들어오는, 기관 자체의 채용/임원선임 공지 (지원사업이 아님)
    "신입직원", "상임이사", "이사장 공개모집", "체험형 인턴", "청년인턴",
]

# ── 업종 화이트리스트 방식 ─────────────────────────────────────────────────────
# 공고에 업종 키워드가 등장할 때:
#   INDUSTRY_WHITELIST 키워드가 하나라도 있으면 → 업종 관련성 있음 (통과)
#   INDUSTRY_BLACKLIST 키워드만 있고 화이트리스트가 없으면 → 부적합
#   아무 업종 키워드도 없으면 → 전 업종 대상으로 간주 (통과)

# 뽀득이 해당될 수 있는 업종 키워드
INDUSTRY_WHITELIST = [
    # 제조
    "제조", "제조업", "스마트제조", "장비", "기계", "금속", "소재",
    # 렌탈·서비스
    "렌탈", "리스", "구독", "서비스업", "유지보수", "애프터서비스",
    # 위생·환경·세척
    "위생", "세척", "청결", "청소", "환경", "에너지절감", "탄소중립", "클린",
    # 디지털·자동화
    "IoT", "스마트팩토리", "자동화", "디지털전환", "DX", "스마트기기",
    # 물류·유통
    "물류", "유통", "공급망",
]

# 뽀득과 무관한 특정 업종 키워드
INDUSTRY_BLACKLIST = [
    # 뷰티·화장품
    "뷰티", "화장품", "코스메틱",
    # 콘텐츠·미디어·출판
    "콘텐츠산업", "미디어산업", "출판", "방송산업", "영화산업", "드라마", "웹툰", "애니메이션",
    # 바이오·제약·의료
    "바이오", "제약", "의약품", "의료기기", "헬스케어",
    # 방산·우주항공
    "방산", "방위산업", "우주항공", "항공우주", "방위",
    # 농업·수산·축산
    "농업", "농식품", "수산", "축산", "임업",
    # 관광·여행·숙박
    "관광산업", "여행업", "숙박업",
    # 게임·엔터테인먼트
    "게임산업", "게임개발", "e스포츠",
    # 패션·섬유
    "패션산업", "섬유산업",
]


def _mentions_company_region(region_text, profile):
    if not region_text:
        return True  # 지역 제한 명시 없음 -> 전국 대상으로 간주
    if "전국" in region_text:
        return True
    return any(loc in region_text for loc in profile["locations"])


def _title_implies_non_company_region(text):
    """제목/대상/기관 텍스트에 당사 소재지와 무관한 타 지역명만 나올 때 True 반환."""
    if not any(r in text for r in NON_COMPANY_REGIONS):
        return False
    return not any(r in text for r in COMPANY_REGION_KEYWORDS)


def _has_exclusion(text):
    return next((kw for kw in EXCLUSION_KEYWORDS if kw in text), None)


def _check_industry_fit(text):
    """
    업종 화이트리스트 검사.
    - 화이트리스트 키워드가 하나라도 있으면 None 반환 (통과)
    - 블랙리스트 키워드만 있으면 해당 키워드 반환 (부적합 처리용)
    - 아무 키워드도 없으면 None 반환 (전 업종 대상으로 간주, 통과)
    """
    if any(kw in text for kw in INDUSTRY_WHITELIST):
        return None
    return next((kw for kw in INDUSTRY_BLACKLIST if kw in text), None)


def _euro(word):
    """받침 유무에 따라 '로'/'으로' 조사를 고른다."""
    last_char = word[-1]
    if "가" <= last_char <= "힣" and (ord(last_char) - 0xAC00) % 28 != 0:
        return "으로"
    return "로"


def judge(announcement, profile):
    title = announcement.get("title") or ""
    target = announcement.get("target") or ""
    agency = announcement.get("agency") or ""
    region = announcement.get("region")
    combined_text = f"{title} {target} {agency}"

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

    if _title_implies_non_company_region(combined_text):
        return {
            "status": "부적합",
            "reason": "공고 제목/대상에 당사 사업장 소재지와 무관한 타 지역 한정 문구가 포함됨",
        }

    mismatched_industry = _check_industry_fit(combined_text)
    if mismatched_industry:
        return {
            "status": "부적합",
            "reason": f"당사 업종과 무관한 '{mismatched_industry}' 분야 전용 공고",
        }

    # 관심키워드 매칭에는 소관기관명(agency)을 넣지 않는다.
    # '고용'이 '고용노동부', '인력'이 'OO인력개발센터'처럼 기관명에 우연히 포함돼
    # 무관한 공고가 '적합'으로 오분류되는 것을 막기 위함. 진짜 적합 공고는 제목/대상에 키워드가 있다.
    interest_text = f"{title} {target}"
    matched_keyword = next(
        (kw for kw in profile["interest_keywords"] if kw in interest_text), None
    )
    if matched_keyword:
        return {
            "status": "적합",
            "reason": f"관심분야 키워드 '{matched_keyword}' 포함, 지역/지원대상/업종 제한에 걸리지 않음",
        }

    return {
        "status": "모호",
        "reason": "지역/지원대상/업종 제한에는 걸리지 않으나 관심분야(R&D·인력채용·시설·운전자금) 키워드가 제목/대상에 명확히 보이지 않아 직접 확인 필요",
    }
