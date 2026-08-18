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

# ── 시·군·구 단위 지역 한정 ────────────────────────────────────────────────────
# 서울/경기 공고라도 특정 시·군·구 소재 기업만 신청할 수 있는 경우가 많다.
# (예: 성남시 고용우수기업, 시흥시 휴게시설 개선) 광역 키워드 '서울'/'경기'만
# 보고 통과시키면 이런 공고가 전부 '적합'으로 올라오므로 별도로 걸러낸다.

# 당사 사업장이 있는 시·군·구 — 이 이름이 있으면 시·군 한정이어도 통과
COMPANY_DISTRICTS = ["화성시", "강남구"]

# 당사 사업장이 없는 수도권 시·군·구
OTHER_DISTRICTS = [
    # 경기도 시·군 (당사 공장 소재지 제외)
    "수원시", "성남시", "고양시", "용인시", "부천시", "안산시", "안양시", "남양주시",
    "평택시", "의정부시", "시흥시", "파주시", "광명시", "김포시", "군포시", "광주시",
    "이천시", "양주시", "오산시", "구리시", "안성시", "포천시", "의왕시", "하남시",
    "여주시", "동두천시", "과천시", "가평군", "양평군", "연천군",
    # 서울시 자치구 (당사 본사 소재지 제외)
    "종로구", "용산구", "성동구", "광진구", "동대문구", "중랑구", "성북구", "강북구",
    "도봉구", "노원구", "은평구", "서대문구", "마포구", "양천구", "강서구", "구로구",
    "금천구", "영등포구", "동작구", "관악구", "서초구", "송파구", "강동구",
    # 특정 단지 입주기업 한정 공고
    "판교",
]

# 시·군 이름이 나와도 전국·광역 단위면 신청 가능하므로 통과시킨다
WIDE_REGION_KEYWORDS = ["전국", "수도권"]

# 회사가 해당되지 않는 게 명백한 지원대상 한정 문구들
EXCLUSION_KEYWORDS = [
    "1인 기업", "소상공인 전용", "자영업",
    "여성기업 전용", "장애인기업 전용", "사회적기업 전용",
    "농업인", "어업인", "전통시장",
    # 공고 게시판에 섞여 들어오는, 기관 자체의 채용/임원선임 공지 (지원사업이 아님)
    "신입직원", "상임이사", "이사장 공개모집", "체험형 인턴", "청년인턴",
    "채용공고", "직원 채용", "사무지원인력", "공무직", "기간제근로자",
]

# 지원금이 아니라 행사·교육·시상인 공고 (신청해도 받는 게 없음)
NON_SUPPORT_KEYWORDS = [
    # 행사
    "밋업", "세미나", "설명회", "박람회", "교류회", "간담회", "포럼",
    "컨퍼런스", "콘퍼런스", "워크숍", "워크샵", "데모데이", "전시회",
    # 공모·시상
    "경진대회", "공모전", "공모대전", "우수성과", "우수사례", "시상식", "포상", "수상자",
    # 교육·프로그램
    "아카데미", "국비교육", "교육생", "특강", "강연", "인턴십",
    "오픈이노베이션", "배치프로그램",
]

# 창업 초기기업 전용 공고 — 당사는 설립 7년을 넘겨 신청자격이 없다
STARTUP_ONLY_KEYWORDS = [
    "팁스", "TIPS", "예비창업", "초기창업", "초기 창업", "창업기업", "창업보육",
    "창업스쿨", "창업패키지", "창업올인원", "창업도약", "재창업", "창업중심대학",
    "실험실창업", "실험실 창업", "창업경진", "창업사관학교", "청년창업",
]

# ── 업종 블랙리스트 ───────────────────────────────────────────────────────────
# 특정 산업 전용 공고는 당사가 신청할 수 없다. 블랙리스트 키워드가 하나라도
# 있으면 부적합으로 본다. (예전에는 화이트리스트가 우선이라 '방사선 기반
# 소재ㆍ장비' 같은 공고가 '장비' 때문에 통과되는 문제가 있었다)
INDUSTRY_BLACKLIST = [
    # 뷰티·화장품
    "뷰티", "화장품", "코스메틱",
    # 콘텐츠·미디어·출판
    "콘텐츠산업", "미디어산업", "출판", "방송산업", "영화산업", "드라마", "웹툰", "애니메이션",
    # 문화·예술·체육
    "문화체육관광", "문화산업", "예술", "공연예술", "공연장", "미술", "음악산업",
    "스포츠", "체육",
    # 바이오·제약·의료
    "바이오", "제약", "의약품", "의료기기", "헬스케어", "백신", "임상시험",
    # 원자력·방사선
    "방사선", "원자력", "핵융합",
    # 반도체·양자·우주·방산
    "반도체", "양자", "디스플레이", "이차전지",
    "방산", "방위산업", "우주항공", "항공우주", "방위",
    # 물·해양 특화 산업
    "물산업", "상하수도", "해양", "항만", "조선산업",
    # 농업·수산·축산
    "농업", "농식품", "수산", "축산", "임업",
    # 관광·여행·숙박
    "관광산업", "여행업", "숙박업",
    # 게임·엔터테인먼트
    "게임산업", "게임개발", "e스포츠",
    # 패션·섬유·자동차
    "패션산업", "섬유산업", "자동차산업",
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


def _implies_other_district(text):
    """수도권이지만 당사 사업장이 없는 시·군·구 한정 공고일 때 True 반환."""
    if not any(d in text for d in OTHER_DISTRICTS):
        return False
    if any(d in text for d in COMPANY_DISTRICTS):
        return False
    return not any(kw in text for kw in WIDE_REGION_KEYWORDS)


def _has_exclusion(text):
    return next((kw for kw in EXCLUSION_KEYWORDS if kw in text), None)


def _is_small_business_only(text):
    """'소상공인' 대상 공고 중 중소기업이 함께 언급되지 않는 것만 제외한다."""
    return "소상공인" in text and "중소기업" not in text


def _has_non_support(text):
    return next((kw for kw in NON_SUPPORT_KEYWORDS if kw in text), None)


def _has_startup_only(text):
    return next((kw for kw in STARTUP_ONLY_KEYWORDS if kw in text), None)


def _check_industry_fit(text):
    """업종 블랙리스트 키워드가 있으면 그 키워드를, 없으면 None을 반환."""
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

    # 지역 판단에는 소관기관명(agency)도 쓴다 — '화성시청'처럼 기관명 자체가 지역 신호다.
    region_text = f"{title} {target} {agency}"
    # 지원대상·업종·행사 여부 판단에는 기관명을 쓰지 않는다.
    # 기관명은 '공공연연구인력파견지원'처럼 업종 키워드('공연')가 우연히 겹치거나
    # 'OO아카데미'처럼 행사 키워드가 들어 있어서 무관한 공고를 잘못 걸러낸다.
    content_text = f"{title} {target}"

    matched_exclusion = _has_exclusion(content_text)
    if matched_exclusion:
        return {
            "status": "부적합",
            "reason": f"지원대상이 '{matched_exclusion}'{_euro(matched_exclusion)} 한정되어 당사 조건과 맞지 않음",
        }

    if _is_small_business_only(content_text):
        return {
            "status": "부적합",
            "reason": "지원대상이 소상공인으로 한정되어 당사 조건과 맞지 않음",
        }

    matched_non_support = _has_non_support(content_text)
    if matched_non_support:
        return {
            "status": "부적합",
            "reason": f"자금 지원사업이 아닌 행사·교육·시상 공고('{matched_non_support}')",
        }

    matched_startup = _has_startup_only(content_text)
    if matched_startup:
        return {
            "status": "부적합",
            "reason": f"창업 초기기업 전용 공고('{matched_startup}')로 당사 업력 조건과 맞지 않음",
        }

    if not _mentions_company_region(region, profile):
        return {
            "status": "부적합",
            "reason": f"지원지역이 '{region}'{_euro(region)} 한정되어 당사 사업장 소재지와 맞지 않음",
        }

    if _title_implies_non_company_region(region_text):
        return {
            "status": "부적합",
            "reason": "공고 제목/대상에 당사 사업장 소재지와 무관한 타 지역 한정 문구가 포함됨",
        }

    if _implies_other_district(region_text):
        return {
            "status": "부적합",
            "reason": "특정 시·군·구 소재 기업 한정 공고로 당사 사업장 소재지와 맞지 않음",
        }

    mismatched_industry = _check_industry_fit(content_text)
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
