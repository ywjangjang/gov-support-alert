"""GitHub Pages용 월별 정적 페이지 생성. docs/ 폴더 전체가 그대로 Pages에 배포됨."""
import html
import json
import os
from datetime import datetime

DOCS_DIR = "docs"
DATA_DIR = os.path.join(DOCS_DIR, "data")

STATUS_ORDER = {"적합": 0, "모호": 1, "부적합": 2}
STATUS_COLOR = {"적합": "#1a7f37", "모호": "#9a6700", "부적합": "#6e7781"}

PAGE_CSS = """
body { font-family: -apple-system, sans-serif; max-width: 1080px; margin: 2rem auto; padding: 0 1rem; color: #1f2328; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #d0d7de; padding: 8px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
.badge { padding: 2px 8px; border-radius: 12px; color: white; font-size: 12px; white-space: nowrap; }
nav a { margin-right: 12px; }
.filter-bar { margin: 1rem 0; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.filter-btn { padding: 6px 16px; border: 1px solid #d0d7de; border-radius: 20px; background: white; cursor: pointer; font-size: 13px; }
.filter-btn.active { color: white; border-color: transparent; }
.filter-btn[data-status="전체"].active { background: #1f2328; }
.filter-btn[data-status="적합"].active { background: #1a7f37; }
.filter-btn[data-status="모호"].active { background: #9a6700; }
.filter-btn[data-status="부적합"].active { background: #6e7781; }
.filter-btn[data-status="검토완료"].active { background: #0969da; }
#count { font-size: 13px; color: #57606a; margin-left: 4px; }
.review-btn {
  padding: 3px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; white-space: nowrap;
  border: 1px solid #d0d7de; background: white; color: #57606a;
}
.review-btn:hover { background: #f0f6ff; border-color: #0969da; color: #0969da; }
.review-btn.done { background: #dafbe1; border-color: #1a7f37; color: #1a7f37; }
tr.reviewed td { opacity: 0.5; }
"""

PAGE_JS = """
const STORAGE_KEY = 'gov_reviewed';
function loadReviewed() {
  try { return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')); }
  catch { return new Set(); }
}
function saveReviewed(set) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...set]));
}

let reviewed = loadReviewed();
let currentStatus = '전체';
const buttons = document.querySelectorAll('.filter-btn');
const rows = document.querySelectorAll('tbody tr');

function applyFilter(status) {
  currentStatus = status;
  let visible = 0;
  rows.forEach(row => {
    const id = row.dataset.id;
    const isReviewed = reviewed.has(id);
    const statusMatch = status === '전체' || row.dataset.status === status;
    const show = status === '검토완료' ? isReviewed : (!isReviewed && statusMatch);
    row.style.display = show ? '' : 'none';
    if (show) visible++;
    // 검토완료 탭에서는 버튼을 "되돌리기"로 표시
    const btn = row.querySelector('.review-btn');
    if (btn) {
      btn.textContent = isReviewed ? '↩ 되돌리기' : '✓ 검토완료';
      btn.classList.toggle('done', isReviewed);
    }
  });
  document.getElementById('count').textContent = visible + '건';
  buttons.forEach(b => b.classList.toggle('active', b.dataset.status === status));
}

function toggleReview(id) {
  if (reviewed.has(id)) { reviewed.delete(id); } else { reviewed.add(id); }
  saveReviewed(reviewed);
  applyFilter(currentStatus);
}

buttons.forEach(b => b.addEventListener('click', () => applyFilter(b.dataset.status)));
applyFilter('전체');
"""


def _month_key(dt):
    return dt.strftime("%Y-%m")


def record_results(judged_announcements, now=None):
    """오늘 수집/판단한 공고를 이번 달 데이터 파일에 누적하고, 월별 페이지와 인덱스를 다시 만든다."""
    now = now or datetime.now()
    month = _month_key(now)
    os.makedirs(DATA_DIR, exist_ok=True)
    data_path = os.path.join(DATA_DIR, f"{month}.json")

    existing = []
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    existing_ids = {row["id"] for row in existing}

    today_str = now.strftime("%Y-%m-%d")
    for ann, judged in judged_announcements:
        if ann["id"] in existing_ids:
            continue
        existing.append({
            "id": ann["id"],
            "source": ann["source"],
            "title": ann["title"],
            "agency": ann.get("agency"),
            "end_date": ann.get("end_date"),
            "url": ann.get("url"),
            "status": judged["status"],
            "reason": judged["reason"],
            "collected_date": today_str,
        })
        existing_ids.add(ann["id"])

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    _build_month_page(month, existing)
    _build_index_page()


def _row_html(row):
    status = row["status"]
    color = STATUS_COLOR.get(status, "#6e7781")
    row_id = html.escape(row["id"], quote=True)
    title = html.escape(row["title"])
    title_cell = f'<a href="{html.escape(row["url"])}" target="_blank">{title}</a>' if row.get("url") else title
    return (
        f'<tr data-status="{status}" data-id="{row_id}">'
        f'<td>{html.escape(row["collected_date"])}</td>'
        f'<td><span class="badge" style="background:{color}">{status}</span></td>'
        f'<td>{html.escape(row["source"])}</td>'
        f"<td>{title_cell}</td>"
        f'<td>{html.escape(row.get("end_date") or "-")}</td>'
        f'<td>{html.escape(row["reason"])}</td>'
        f'<td><button class="review-btn" onclick="toggleReview(\'{row_id}\')">✓ 검토완료</button></td>'
        "</tr>"
    )


def _build_month_page(month, rows):
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["collected_date"], STATUS_ORDER.get(r["status"], 9)),
        reverse=True,
    )
    body_rows = "\n".join(_row_html(r) for r in rows_sorted)
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{month} 정부지원사업 공고</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<nav><a href="index.html">&larr; 월별 목록</a></nav>
<h1>{month} 정부지원사업 공고</h1>
<div class="filter-bar">
  <button class="filter-btn active" data-status="전체">전체</button>
  <button class="filter-btn" data-status="적합">적합</button>
  <button class="filter-btn" data-status="모호">모호</button>
  <button class="filter-btn" data-status="부적합">부적합</button>
  <button class="filter-btn" data-status="검토완료">검토완료</button>
  <span id="count"></span>
</div>
<table>
<thead><tr><th>수집일</th><th>판단</th><th>출처</th><th>공고명</th><th>마감일</th><th>판단 이유</th><th></th></tr></thead>
<tbody>
{body_rows}
</tbody>
</table>
<script>{PAGE_JS}</script>
</body>
</html>
"""
    with open(os.path.join(DOCS_DIR, f"{month}.html"), "w", encoding="utf-8") as f:
        f.write(page)


def _build_index_page():
    months = sorted(
        (f[:-5] for f in os.listdir(DATA_DIR) if f.endswith(".json")),
        reverse=True,
    )
    items = "\n".join(f'<li><a href="{m}.html">{m}</a></li>' for m in months)
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>정부지원사업 알림</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<h1>정부지원사업 알림 - 월별 목록</h1>
<ul>
{items}
</ul>
</body>
</html>
"""
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
