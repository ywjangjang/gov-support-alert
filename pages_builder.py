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
:root {
  --bg: #ffffff; --fg: #1f2328; --muted: #57606a; --border: #d0d7de;
  --th-bg: #f6f8fa; --card-bg: #f6f8fa; --link: #0969da; --hover: #f0f6ff;
  --urgent: #cf222e; --reviewed-bg: #dafbe1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d1117; --fg: #e6edf3; --muted: #8b949e; --border: #30363d;
    --th-bg: #161b22; --card-bg: #161b22; --link: #4493f8; --hover: #1c2a3a;
    --urgent: #ff7b72; --reviewed-bg: #12361f;
  }
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  max-width: 1100px; margin: 0 auto; padding: 1.5rem 1rem 4rem;
  color: var(--fg); background: var(--bg); line-height: 1.5;
}
h1 { font-size: 1.4rem; margin: 0.5rem 0 1rem; }
a { color: var(--link); }
nav { margin-bottom: 0.5rem; }

/* 상단 요약 통계 타일 */
.stats { display: flex; gap: 10px; flex-wrap: wrap; margin: 0.5rem 0 1rem; }
.stat {
  flex: 1; min-width: 90px; background: var(--card-bg); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px 14px;
}
.stat .num { font-size: 1.6rem; font-weight: 700; line-height: 1; }
.stat .lbl { font-size: 12px; color: var(--muted); margin-top: 4px; }
.stat.적합 .num { color: #1a7f37; }
.stat.모호 .num { color: #9a6700; }
.stat.부적합 .num { color: var(--muted); }

/* 검색창 */
.search-wrap { margin: 0.75rem 0; }
#search {
  width: 100%; padding: 10px 14px; font-size: 14px; border-radius: 10px;
  border: 1px solid var(--border); background: var(--bg); color: var(--fg);
}
#search:focus { outline: 2px solid var(--link); outline-offset: -1px; }

/* 필터 버튼 */
.filter-bar { margin: 0.75rem 0; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.filter-btn {
  padding: 6px 16px; border: 1px solid var(--border); border-radius: 20px;
  background: var(--bg); color: var(--fg); cursor: pointer; font-size: 13px;
}
.filter-btn.active { color: white; border-color: transparent; }
.filter-btn[data-status="전체"].active { background: #1f2328; }
.filter-btn[data-status="적합"].active { background: #1a7f37; }
.filter-btn[data-status="모호"].active { background: #9a6700; }
.filter-btn[data-status="부적합"].active { background: #6e7781; }
.filter-btn[data-status="검토완료"].active { background: #0969da; }
#count { font-size: 13px; color: var(--muted); margin-left: 4px; }

/* 표 */
.table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid var(--border); padding: 9px 10px; text-align: left; vertical-align: top; }
th { background: var(--th-bg); position: sticky; top: 0; white-space: nowrap; }
tr:last-child td { border-bottom: none; }
.badge { padding: 2px 8px; border-radius: 12px; color: white; font-size: 12px; white-space: nowrap; }

/* 마감 D-day */
.deadline { white-space: nowrap; }
.dday { display: inline-block; margin-left: 6px; padding: 1px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.dday.urgent { background: var(--urgent); color: white; }
.dday.soon { background: #9a6700; color: white; }
.dday.normal { border: 1px solid var(--border); color: var(--muted); }
tr.expired td { opacity: 0.45; }
tr.expired .title-cell { text-decoration: line-through; }

/* 필터 그룹 (검토 상태 / AI 판단 2단) */
.filter-group { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 0.5rem 0; }
.filter-label { font-size: 12px; color: var(--muted); min-width: 42px; }
.rev-btn, .stat-btn {
  padding: 6px 14px; border: 1px solid var(--border); border-radius: 20px;
  background: var(--bg); color: var(--fg); cursor: pointer; font-size: 13px;
}
.rev-btn .c, .stat-btn .c { font-size: 11px; opacity: 0.7; margin-left: 3px; }
.rev-btn.active[data-rev="대기"] { background: #1f2328; color: white; border-color: transparent; }
.rev-btn.active[data-rev="지원필요"] { background: #1a7f37; color: white; border-color: transparent; }
.rev-btn.active[data-rev="지원제외"] { background: #6e7781; color: white; border-color: transparent; }
.rev-btn.active[data-rev="전체"] { background: #0969da; color: white; border-color: transparent; }
.stat-btn.active[data-status="적합"] { background: #1a7f37; color: white; border-color: transparent; }
.stat-btn.active[data-status="모호"] { background: #9a6700; color: white; border-color: transparent; }
.stat-btn.active[data-status="부적합"] { background: #6e7781; color: white; border-color: transparent; }
.stat-btn.active[data-status="전체"] { background: #1f2328; color: white; border-color: transparent; }

/* 정렬 드롭다운 */
.sort-wrap { margin-left: auto; font-size: 13px; color: var(--muted); display: flex; align-items: center; gap: 6px; }
#sort {
  padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--bg); color: var(--fg); font-size: 13px; cursor: pointer;
}

/* 행 검토 액션 버튼 */
.actions { white-space: nowrap; }
.act-btn {
  padding: 3px 9px; border-radius: 6px; font-size: 12px; cursor: pointer; white-space: nowrap;
  border: 1px solid var(--border); background: var(--bg); color: var(--muted);
}
.act-btn + .act-btn { margin-left: 4px; }
.act-btn.need:hover { border-color: #1a7f37; color: #1a7f37; }
.act-btn.drop:hover { border-color: var(--urgent); color: var(--urgent); }
.act-btn.need.active { background: #1a7f37; color: white; border-color: transparent; }
.act-btn.drop.active { background: #6e7781; color: white; border-color: transparent; }
tr.state-need td:first-child { box-shadow: inset 3px 0 0 #1a7f37; }
tr.state-drop td { opacity: 0.45; }
.empty { padding: 2rem; text-align: center; color: var(--muted); }
"""

PAGE_JS = """
const REVIEW_KEY = 'gov_review_v2';

// 검토 상태: 'gov_review_v2' = { id: '지원필요' | '지원제외' }. 없으면 '검토 대기'.
function loadReview() {
  try {
    const raw = localStorage.getItem(REVIEW_KEY);
    if (raw) return new Map(Object.entries(JSON.parse(raw)));
  } catch (e) {}
  // 구버전('gov_reviewed' = 검토완료 id 목록) → '지원제외'으로 이관
  try {
    const old = JSON.parse(localStorage.getItem('gov_reviewed') || '[]');
    return new Map(old.map(id => [id, '지원제외']));
  } catch (e) { return new Map(); }
}
function saveReview(m) {
  localStorage.setItem(REVIEW_KEY, JSON.stringify(Object.fromEntries(m)));
}

let review = loadReview();
let revFilter = '대기';       // 대기 | 지원필요 | 지원제외 | 전체
let statusFilter = '적합';    // 적합 | 모호 | 부적합 | 전체
let searchTerm = '';
const revButtons = document.querySelectorAll('.rev-btn');
const statButtons = document.querySelectorAll('.stat-btn');
const rows = document.querySelectorAll('tbody tr');
const originalOrder = Array.from(rows);   // 최초 DOM 순서 = 수집일 최신순
const searchInput = document.getElementById('search');
const sortSelect = document.getElementById('sort');
const emptyRow = document.getElementById('empty-row');

function stateOf(id) { return review.get(id) || '대기'; }

// 마감일 D-day 계산 및 표시 (보는 시점 기준)
function renderDdays() {
  const now = new Date();
  rows.forEach(row => {
    row._deadlineDays = null;   // 마감일 없음 (정렬 시 맨 뒤)
    const cell = row.querySelector('.deadline');
    if (!cell) return;
    const endStr = cell.dataset.end;
    if (!endStr || endStr === '-') return;
    const end = new Date(endStr + 'T23:59:59');
    if (isNaN(end)) return;
    const days = Math.ceil((end - now) / 86400000);
    row._deadlineDays = days;
    let cls, label;
    if (days < 0) { cls = 'normal'; label = '마감'; row.classList.add('expired'); }
    else if (days <= 7) { cls = 'urgent'; label = 'D-' + days; }
    else if (days <= 14) { cls = 'soon'; label = 'D-' + days; }
    else { cls = 'normal'; label = 'D-' + days; }
    const span = document.createElement('span');
    span.className = 'dday ' + cls;
    span.textContent = label;
    cell.appendChild(span);
  });
}

// 행에 현재 검토 상태를 반영 (버튼 하이라이트 + 행 스타일)
function renderRowState(row) {
  const st = stateOf(row.dataset.id);
  row.classList.toggle('state-need', st === '지원필요');
  row.classList.toggle('state-drop', st === '지원제외');
  row.querySelectorAll('.act-btn').forEach(b => b.classList.toggle('active', b.dataset.act === st));
}

function applyFilter() {
  const revCounts = { '대기': 0, '지원필요': 0, '지원제외': 0, '전체': 0 };
  let visible = 0;
  rows.forEach(row => {
    const st = stateOf(row.dataset.id);
    const statusMatch = statusFilter === '전체' || row.dataset.status === statusFilter;
    const searchMatch = !searchTerm || row.dataset.search.includes(searchTerm);
    // 검토 상태 탭 카운트는 현재 '판단'+'검색' 조건 안에서 센다
    if (statusMatch && searchMatch) {
      revCounts[st] = (revCounts[st] || 0) + 1;
      revCounts['전체']++;
    }
    const revMatch = revFilter === '전체' || st === revFilter;
    const show = revMatch && statusMatch && searchMatch;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  revButtons.forEach(b => {
    b.classList.toggle('active', b.dataset.rev === revFilter);
    const c = b.querySelector('.c');
    if (c) c.textContent = revCounts[b.dataset.rev] || 0;
  });
  statButtons.forEach(b => b.classList.toggle('active', b.dataset.status === statusFilter));
  document.getElementById('count').textContent = visible + '건';
  if (emptyRow) emptyRow.style.display = visible === 0 ? '' : 'none';
}

// 정렬: '수집일 최신순'(기본) 또는 '마감일 임박순'
function sortKey(row) {
  const d = row._deadlineDays;
  if (d == null) return 1e9;      // 마감일 없음 → 맨 뒤
  if (d < 0) return 1e8 - d;      // 마감 지남 → 임박 공고 뒤, 덜 지난 순
  return d;                       // 임박 순 (D-day 작을수록 앞)
}
function sortRows(mode) {
  const tbody = document.querySelector('tbody');
  const arr = originalOrder.slice();
  if (mode === 'deadline') arr.sort((a, b) => sortKey(a) - sortKey(b));
  arr.forEach(r => tbody.appendChild(r));
}

// 행의 검토 상태 변경: 같은 버튼을 다시 누르면 '검토 대기'로 복귀
function setReview(id, state) {
  if (review.get(id) === state) { review.delete(id); }
  else { review.set(id, state); }
  saveReview(review);
  const row = document.querySelector('tr[data-id="' + CSS.escape(id) + '"]');
  if (row) renderRowState(row);
  applyFilter();
}

revButtons.forEach(b => b.addEventListener('click', () => { revFilter = b.dataset.rev; applyFilter(); }));
statButtons.forEach(b => b.addEventListener('click', () => { statusFilter = b.dataset.status; applyFilter(); }));
if (searchInput) {
  searchInput.addEventListener('input', () => { searchTerm = searchInput.value.trim().toLowerCase(); applyFilter(); });
}
if (sortSelect) {
  sortSelect.addEventListener('change', () => sortRows(sortSelect.value));
}
renderDdays();
rows.forEach(renderRowState);
applyFilter();
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
    title_cell = (
        f'<a class="title-cell" href="{html.escape(row["url"])}" target="_blank" rel="noopener">{title}</a>'
        if row.get("url") else f'<span class="title-cell">{title}</span>'
    )
    end_date = row.get("end_date") or "-"
    # 검색용 텍스트 (소문자로 미리 합쳐둠)
    search_blob = html.escape(
        " ".join(filter(None, [row["title"], row.get("agency"), row["source"], row["reason"]])).lower(),
        quote=True,
    )
    return (
        f'<tr data-status="{status}" data-id="{row_id}" data-search="{search_blob}">'
        f'<td>{html.escape(row["collected_date"])}</td>'
        f'<td><span class="badge" style="background:{color}">{status}</span></td>'
        f'<td>{html.escape(row["source"])}</td>'
        f"<td>{title_cell}</td>"
        f'<td class="deadline" data-end="{html.escape(end_date, quote=True)}">{html.escape(end_date)}</td>'
        f'<td>{html.escape(row["reason"])}</td>'
        f'<td class="actions">'
        f'<button class="act-btn need" data-act="지원필요" onclick="setReview(\'{row_id}\',\'지원필요\')">지원 필요</button>'
        f'<button class="act-btn drop" data-act="지원제외" onclick="setReview(\'{row_id}\',\'지원제외\')">지원 제외</button>'
        f'</td>'
        "</tr>"
    )


def _build_month_page(month, rows):
    rows_sorted = sorted(
        rows,
        key=lambda r: (r["collected_date"], STATUS_ORDER.get(r["status"], 9)),
        reverse=True,
    )
    counts = {"적합": 0, "모호": 0, "부적합": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    body_rows = "\n".join(_row_html(r) for r in rows_sorted)
    stats = "".join(
        f'<div class="stat {s}"><div class="num">{counts.get(s, 0)}</div><div class="lbl">{s}</div></div>'
        for s in ("적합", "모호", "부적합")
    )
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{month} 정부지원사업 공고</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<nav><a href="index.html">&larr; 월별 목록</a></nav>
<h1>{month} 정부지원사업 공고</h1>
<div class="stats">{stats}</div>
<div class="search-wrap">
  <input id="search" type="search" placeholder="🔍 공고명·기관·출처·사유로 검색" autocomplete="off">
</div>
<div class="filter-group">
  <span class="filter-label">검토 상태</span>
  <button class="rev-btn active" data-rev="대기">검토 대기<span class="c"></span></button>
  <button class="rev-btn" data-rev="지원필요">지원 필요<span class="c"></span></button>
  <button class="rev-btn" data-rev="지원제외">지원 제외<span class="c"></span></button>
  <button class="rev-btn" data-rev="전체">전체<span class="c"></span></button>
</div>
<div class="filter-group">
  <span class="filter-label">1차 판단</span>
  <button class="stat-btn active" data-status="적합">적합</button>
  <button class="stat-btn" data-status="모호">모호</button>
  <button class="stat-btn" data-status="부적합">부적합</button>
  <button class="stat-btn" data-status="전체">전체</button>
  <span id="count"></span>
  <label class="sort-wrap">정렬
    <select id="sort">
      <option value="collected">수집일 최신순</option>
      <option value="deadline">마감일 임박순</option>
    </select>
  </label>
</div>
<div class="table-wrap">
<table>
<thead><tr><th>수집일</th><th>1차 판단</th><th>출처</th><th>공고명</th><th>마감일</th><th>판단 이유</th><th>검토 상태</th></tr></thead>
<tbody>
{body_rows}
</tbody>
</table>
</div>
<div id="empty-row" class="empty" style="display:none">조건에 맞는 공고가 없습니다.</div>
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
    items = []
    for m in months:
        try:
            with open(os.path.join(DATA_DIR, f"{m}.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            fit = sum(1 for r in data if r["status"] == "적합")
            meta = f'<span class="month-meta">적합 {fit}건 · 전체 {len(data)}건</span>'
        except Exception:
            meta = ""
        items.append(f'<li><a href="{m}.html">{m}</a> {meta}</li>')
    items_html = "\n".join(items)
    page = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>정부지원사업 알림</title>
<style>{PAGE_CSS}
ul {{ list-style: none; padding: 0; }}
li {{ padding: 12px 14px; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 8px; }}
li a {{ font-size: 1.05rem; font-weight: 600; }}
.month-meta {{ color: var(--muted); font-size: 13px; margin-left: 8px; }}
</style>
</head>
<body>
<h1>정부지원사업 알림 — 월별 목록</h1>
<ul>
{items_html}
</ul>
</body>
</html>
"""
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
