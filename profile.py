"""
COMPANY_PROFILE 형식 예시 (실제 코드에서는 사용되지 않음).

실제 회사 정보는 config.py에 채워넣으세요 — config.py는 .gitignore에 들어있어
GitHub(특히 public 저장소)에 절대 올라가지 않습니다. 회사명/인력수/소재지 같은
식별 정보를 공개 저장소에 커밋하지 않기 위한 구조입니다.
"""

COMPANY_PROFILE_EXAMPLE = {
    "name": "예시주식회사",
    "homepage": "https://example.com/",
    "founded": "2017-01-01",
    "employee_count": 50,
    "industries": ["제조업"],
    # 사이트마다 "서울특별시"/"서울"처럼 표기가 달라서 축약형도 같이 등록해두면 좋다.
    "locations": ["서울특별시", "서울"],
    "certifications": ["벤처기업"],
    "is_sme": True,  # 중소기업확인서 보유 여부
    # 관심 지원분야 — 공고 제목/내용에 이 키워드가 있으면 적합 가능성을 높게 본다.
    "interest_keywords": ["R&D", "기술개발", "채용", "인력", "시설", "운전자금"],
}
