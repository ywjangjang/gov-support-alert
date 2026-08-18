"""
아직 Slack으로 보내지 않은 알림 대기열.

주말·공휴일에 올라온 공고도 수집·판단은 그대로 하되 알림만 미룬다.
이때 그냥 건너뛰면 그 공고는 seen_announcements.json에 '이미 본 공고'로 기록돼서
다음 영업일에도 신규로 잡히지 않고 영영 알림 없이 묻힌다.
그래서 알릴 내용을 여기에 쌓아두고, 다음 영업일에 한꺼번에 보낸다.

형태: {"fit": [{"title": ..., "end_date": ...}, ...], "maybe_count": 3}
"""
import json
import os


def empty():
    return {"fit": [], "maybe_count": 0}


def load(path):
    if not os.path.exists(path):
        return empty()
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return empty()
    return {
        "fit": data.get("fit", []),
        "maybe_count": data.get("maybe_count", 0),
    }


def save(path, pending):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def add(pending, new_fit, new_maybe):
    """이번 실행에서 나온 '적합' 공고와 '모호' 건수를 대기열에 더한다."""
    pending["fit"].extend(
        {"title": ann["title"], "end_date": ann.get("end_date")} for ann, _judged in new_fit
    )
    pending["maybe_count"] += len(new_maybe)
    return pending
