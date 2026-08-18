"""
정부지원사업 자동 수집 + 적합성 판단 + Slack 알림 + 월별 페이지 생성.

실행: python3 main.py
(반복 실행 없음 — GitHub Actions가 매일 1회 이 스크립트를 실행하도록 예약함)
"""
import traceback

import business_day
import config
import filter_rules
import notifier
import pages_builder
import pending_store
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


def format_summary_slack_message(pending):
    """'적합' 공고 목록을 본문으로, '모호' 건수는 한 줄 요약으로 붙인다.

    주말·공휴일에 쌓인 대기열이 함께 들어올 수 있어 여러 날치가 한 번에 나갈 수 있다.
    """
    fit = pending["fit"]
    count = len(fit)
    lines = [f"신청 검토가 필요한 새 지원사업 *{count}건*이 올라왔습니다."]
    for item in fit[:5]:
        end = f" (~{item['end_date']})" if item.get("end_date") else ""
        lines.append(f"• {item['title']}{end}")
    if count > 5:
        lines.append(f"• 외 {count - 5}건")
    if pending["maybe_count"]:
        lines.append(f"\n판단 보류(모호) {pending['maybe_count']}건도 함께 올라왔습니다.")
    lines.append(f"\n자세히 보기: {PAGES_URL}")
    return "\n".join(lines)


def main():
    announcements = collect_all()
    judged_all = [(ann, filter_rules.judge(ann, config.COMPANY_PROFILE)) for ann in announcements]
    pages_builder.record_results(judged_all)

    seen = seen_store.load_seen(config.SEEN_ANNOUNCEMENTS_FILE)
    new_announcements = seen_store.pick_new(announcements, seen)
    new_ids = {ann["id"] for ann in new_announcements}

    new_fit = [(a, j) for a, j in judged_all if a["id"] in new_ids and j["status"] == "적합"]
    new_maybe = [(a, j) for a, j in judged_all if a["id"] in new_ids and j["status"] == "모호"]

    # 이번에 나온 알림거리를 대기열에 넣는다. 주말·공휴일이면 여기 쌓인 채로 넘어가고,
    # 다음 영업일 실행 때 그동안 쌓인 것까지 한 번에 나간다.
    pending = pending_store.add(
        pending_store.load(config.PENDING_NOTIFICATIONS_FILE), new_fit, new_maybe
    )

    today = business_day.today_kst()
    workday = business_day.is_business_day(today)

    # Slack은 영업일에, '적합' 공고가 실제로 있을 때만 보낸다.
    # '모호'만 있는 날은 알림 없이 넘어가고, 월별 페이지에는 그대로 쌓인다.
    sent = bool(workday and pending["fit"] and config.SLACK_WEBHOOK_URL)
    if sent:
        notifier.send_slack_message(
            config.SLACK_WEBHOOK_URL, format_summary_slack_message(pending)
        )
    if workday:
        # 보냈든( 발송 완료) 안 보냈든(적합 0건) 영업일에 한 번 정리해서
        # 대기열이 무한정 커지지 않게 한다.
        pending = pending_store.empty()

    pending_store.save(config.PENDING_NOTIFICATIONS_FILE, pending)
    seen_store.save_seen(config.SEEN_ANNOUNCEMENTS_FILE, seen)

    if sent:
        slack_log = "발송"
    elif not workday:
        slack_log = f"미발송({business_day.describe(today)}, 대기 {len(pending['fit'])}건)"
    else:
        slack_log = "미발송(적합 0건)"
    print(
        f"총 {len(announcements)}건 수집, 신규 {len(new_announcements)}건 "
        f"(적합 {len(new_fit)}건 / 모호 {len(new_maybe)}건), "
        f"Slack {slack_log}"
    )


if __name__ == "__main__":
    main()
