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


def format_slack_message(ann, judged):
    lines = [
        f"*[{judged['status']}] {ann['title']}*",
        f"출처: {ann['source']}" + (f" ({ann['agency']})" if ann.get("agency") else ""),
    ]
    if ann.get("end_date"):
        lines.append(f"마감일: {ann['end_date']}")
    lines.append(f"판단 이유: {judged['reason']}")
    if ann.get("url"):
        lines.append(ann["url"])
    return "\n".join(lines)


def main():
    announcements = collect_all()
    judged_all = [(ann, filter_rules.judge(ann, config.COMPANY_PROFILE)) for ann in announcements]
    pages_builder.record_results(judged_all)

    seen = seen_store.load_seen(config.SEEN_ANNOUNCEMENTS_FILE)
    new_announcements = seen_store.pick_new(announcements, seen)
    new_ids = {ann["id"] for ann in new_announcements}

    notify_count = 0
    for ann, judged in judged_all:
        if ann["id"] not in new_ids or judged["status"] == "부적합":
            continue
        if not config.SLACK_WEBHOOK_URL:
            continue
        notifier.send_slack_message(config.SLACK_WEBHOOK_URL, format_slack_message(ann, judged))
        notify_count += 1

    seen_store.save_seen(config.SEEN_ANNOUNCEMENTS_FILE, seen)
    print(f"총 {len(announcements)}건 수집, 신규 {len(new_announcements)}건, Slack 알림 {notify_count}건 발송")


if __name__ == "__main__":
    main()
