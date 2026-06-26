"""
정부지원사업 자동 수집 + 적합성 판단 + Slack 알림 + 월별 페이지 생성.

실행: python3 main.py
(반복 실행 없음 — GitHub Actions가 매일 1회 이 스크립트를 실행하도록 예약함)
"""
import traceback

import config
import filter_rules
import notifier
import pages_builder
import seen_store
from sources import bizinfo_client, kibo_client, kstartup_client, sba_client, tipa_client


def collect_all():
    fetchers = [
        ("기업마당", lambda: bizinfo_client.fetch_announcements(config.BIZINFO_API_KEY)),
        ("K-스타트업", lambda: kstartup_client.fetch_announcements(config.KSTARTUP_API_KEY)),
        ("서울SBA", sba_client.fetch_announcements),
        ("TIPA", tipa_client.fetch_announcements),
        ("기술보증기금", kibo_client.fetch_announcements),
    ]
    collected = []
    for name, fetch in fetchers:
        try:
            items = fetch()
            print(f"[{name}] {len(items)}건 수집")
            collected.extend(items)
        except Exception:
            print(f"[{name}] 수집 실패:")
            traceback.print_exc()
    return collected


PAGES_URL = "https://ywjangjang.github.io/gov-support-alert/"


def format_summary_slack_message(new_fitting):
    count = len(new_fitting)
    lines = [f"새 지원사업 공고 *{count}건*이 올라왔습니다."]
    for ann, judged in new_fitting[:5]:
        label = f"[{judged['status']}]"
        end = f" (~{ann['end_date']})" if ann.get("end_date") else ""
        lines.append(f"• {label} {ann['title']}{end}")
    if count > 5:
        lines.append(f"• 외 {count - 5}건")
    lines.append(f"\n자세히 보기: {PAGES_URL}")
    return "\n".join(lines)


def main():
    announcements = collect_all()
    judged_all = [(ann, filter_rules.judge(ann, config.COMPANY_PROFILE)) for ann in announcements]
    pages_builder.record_results(judged_all)

    seen = seen_store.load_seen(config.SEEN_ANNOUNCEMENTS_FILE)
    new_announcements = seen_store.pick_new(announcements, seen)
    new_ids = {ann["id"] for ann in new_announcements}

    new_fitting = [
        (ann, judged) for ann, judged in judged_all
        if ann["id"] in new_ids and judged["status"] != "부적합"
    ]

    if new_fitting and config.SLACK_WEBHOOK_URL:
        notifier.send_slack_message(config.SLACK_WEBHOOK_URL, format_summary_slack_message(new_fitting))

    seen_store.save_seen(config.SEEN_ANNOUNCEMENTS_FILE, seen)
    print(f"총 {len(announcements)}건 수집, 신규 {len(new_announcements)}건, Slack 알림 {len(new_fitting)}건 요약 발송")


if __name__ == "__main__":
    main()
