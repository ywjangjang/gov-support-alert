"""이미 알림을 보낸 공고를 기록해서, 같은 공고를 반복 알림하지 않도록 관리."""
import json
import os


def load_seen(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_seen(path, seen):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def pick_new(announcements, seen):
    """
    아직 알림을 보내지 않은 공고만 골라서 반환.
    seen 딕셔너리는 호출 후 새로 등장한 공고들이 추가된 상태가 됨.
    """
    result = []
    for ann in announcements:
        key = ann["id"]
        if key not in seen:
            result.append(ann)
            seen[key] = {"title": ann["title"], "source": ann["source"]}
    return result
