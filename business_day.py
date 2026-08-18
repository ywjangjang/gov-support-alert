"""
주말·공휴일 판단.

Slack 알림은 영업일에만 보낸다. GitHub Actions 러너의 시각은 UTC라서,
날짜를 그대로 쓰면 한국 날짜와 어긋날 수 있으므로 항상 KST로 변환해서 판단한다.

공휴일은 `holidays` 패키지가 계산한다. 설·추석 같은 음력 공휴일과 대체공휴일까지
자동으로 처리해줘서 매년 목록을 손으로 갱신할 필요가 없다.
"""
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def today_kst():
    """GitHub Actions(UTC)에서 실행되더라도 한국 기준 날짜를 반환."""
    return datetime.now(KST).date()


def holiday_name(date):
    """공휴일이면 이름을, 아니면 None을 반환."""
    try:
        import holidays
    except ImportError:
        # 패키지가 없으면 공휴일 판단을 포기하고 평일로 본다.
        # 알림을 잘못 보내는 쪽이, 조용히 빠뜨리는 쪽보다 낫다.
        return None
    return holidays.SouthKorea(years=date.year).get(date)


def is_business_day(date):
    """토·일과 공휴일이 아니면 True."""
    if date.weekday() >= 5:  # 5=토, 6=일
        return False
    return holiday_name(date) is None


def describe(date):
    """로그에 남길 사람이 읽을 수 있는 설명."""
    if date.weekday() >= 5:
        return "주말"
    name = holiday_name(date)
    return f"공휴일({name})" if name else "영업일"
