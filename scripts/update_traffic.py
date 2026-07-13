#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首都高「大規模・長期の交通規制」ページを取得し、
shutoko_hub.html を自動生成するスクリプト。
GitHub Actionsから1日3回（11時・17時・21時）自動実行される。
"""
import re
import sys
import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://www.shutoko.jp/traffic/control/largeScale/list/?sType=1"
CONSTRUCTION_MAP_URL = "https://www.shutoko-construction.jp/"
LARGESCALE_URL = "https://www.shutoko.jp/traffic/control/largeScale/list/?sType=1"
OUTPUT_PATH = "shutoko_hub.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def fetch_table_rows():
    """首都高サイトから規制情報テーブルの行データを取得する"""
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    target_table = None
    for table in soup.find_all("table"):
        header_text = table.get_text()
        if "規制箇所" in header_text and "実施日時" in header_text:
            target_table = table
            break

    if target_table is None:
        raise RuntimeError("規制情報テーブルが見つかりませんでした（サイト構造が変わった可能性）")

    rows = []
    trs = target_table.find_all("tr")
    for tr in trs:
        cells = tr.find_all(["td"])
        if not cells:
            continue
        texts = [c.get_text(" ", strip=True) for c in cells]
        if len(texts) < 5:
            continue
        rows.append(texts)

    return rows


def parse_row(cells):
    """1行分のセル配列を辞書に変換する。列数のブレに対して多少頑健にする。"""
    # 想定列順: 規制箇所, 方向, 実施日時, 規制種別, 規制理由, 備考, (詳細)
    d = {
        "route": cells[0] if len(cells) > 0 else "",
        "direction": cells[1] if len(cells) > 1 else "",
        "datetime": cells[2] if len(cells) > 2 else "",
        "kind": cells[3] if len(cells) > 3 else "",
        "reason": cells[4] if len(cells) > 4 else "",
        "note": cells[5] if len(cells) > 5 else "",
    }
    return d


def extract_group_date(datetime_text):
    """実施日時テキストから、グループ化用の開始日を抽出する"""
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\(([^)]+)\)", datetime_text)
    if not m:
        return "日付不明", datetime.date(2100, 1, 1)
    year, month, day, weekday = m.groups()
    try:
        key_date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        key_date = datetime.date(2100, 1, 1)
    label = f"{int(month)}月{int(day)}日({weekday})"
    return label, key_date


DATE_TOKEN_RE = re.compile(r"(?:(\d{4})[年/])?(\d{1,2})[月/](\d{1,2})日?\(([^)]+)\)")


def parse_date_range(datetime_text, base_year):
    """実施日時テキストから、開始日・終了日（データ属性用のISO文字列）を抽出する。
    年の記載がない日付（例: 7/14(火)）は base_year を補い、
    12月→1月をまたぐ場合はできるだけ自然になるよう年を+1する。"""
    tokens = DATE_TOKEN_RE.findall(datetime_text)
    dates = []
    prev_month = None
    for y, m, d, _wd in tokens:
        month, day = int(m), int(d)
        year = int(y) if y else base_year
        if not y and prev_month is not None and month < prev_month - 6:
            # 月が急に巻き戻ったように見える＝年をまたいでいる可能性
            year += 1
        try:
            dates.append(datetime.date(year, month, day))
        except ValueError:
            continue
        prev_month = month
    if not dates:
        return None, None
    start = min(dates)
    end = max(dates)
    return start.isoformat(), end.isoformat()


def build_item_html(item, base_year):
    is_iriguchi = "出入口" in item["kind"]
    cls = "item iriguchi" if is_iriguchi else "item"
    tag_cls = "tag iri" if is_iriguchi else "tag honsen"
    route_label = item["route"]
    if item["direction"]:
        route_label += f"（{item['direction']}）"
    note_parts = [p for p in [item["reason"], item["note"]] if p]
    note_text = "　".join(note_parts)
    start_iso, end_iso = parse_date_range(item["datetime"], base_year)
    data_attrs = ""
    if start_iso:
        data_attrs = f' data-start="{start_iso}" data-end="{end_iso}"'
    return f"""<div class="{cls}"{data_attrs}>
  <div class="route">{escape_html(route_label)}</div>
  <div class="time">{escape_html(item['datetime'])}</div>
  <div class="tags"><span class="{tag_cls}">{escape_html(item['kind'] or '規制')}</span></div>
  <div class="note">{escape_html(note_text)}</div>
</div>"""


def escape_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_page(items_by_date, fetched_at, base_year, error_message=None):
    date_sections = []
    for label, items in items_by_date:
        cards = "\n".join(build_item_html(it, base_year) for it in items)
        date_sections.append(f'<div class="date-head">📅 {escape_html(label)}</div>\n{cards}')
    body_sections = "\n\n".join(date_sections)

    error_banner = ""
    if error_message:
        error_banner = f'''<div class="updated" style="border-color:#ef4444;color:#f87171;background:rgba(239,68,68,.1)">
  ⚠️ 自動更新に失敗しました（{escape_html(error_message)}）。前回取得分を表示しています。最新情報は下のリンクから直接ご確認ください。
</div>'''

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>首都高 工事・規制情報</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Hiragino Kaku Gothic ProN',sans-serif;
  background:#0d0d1a;color:#e8e8f4;min-height:100vh;padding:20px 16px 40px;max-width:520px;margin:0 auto}}
h1{{font-size:19px;font-weight:800;margin-bottom:4px;display:flex;align-items:center;gap:8px}}
.sub{{font-size:12px;color:#7878a0;margin-bottom:8px}}
.updated{{font-size:11px;color:#fbbf24;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
  border-radius:8px;padding:8px 12px;margin-bottom:14px;line-height:1.6}}
.filter-row{{display:flex;gap:8px;margin-bottom:20px}}
.filter-btn{{flex:1;padding:10px;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;
  border:2px solid #2a2a4a;background:#161628;color:#9999b8}}
.filter-btn.active{{border-color:#4f8ef7;background:rgba(79,142,247,.15);color:#e8e8f4}}
.linkbtn{{display:block;background:#161628;border:2px solid #4f8ef7;border-radius:12px;
  padding:13px 16px;margin-bottom:20px;text-decoration:none;color:#e8e8f4;text-align:center;
  font-size:14px;font-weight:700}}
.linkbtn .small{{display:block;font-size:11px;font-weight:400;color:#9999b8;margin-top:3px}}
.date-head{{font-size:16px;font-weight:800;color:#e8e8f4;margin:22px 0 10px;
  display:flex;align-items:center;gap:6px;position:sticky;top:0;background:#0d0d1a;padding:8px 0;z-index:5}}
.item{{background:#161628;border:1px solid #2a2a4a;border-left:4px solid #ef4444;border-radius:10px;
  padding:13px 14px;margin-bottom:10px}}
.item.iriguchi{{border-left-color:#f59e0b}}
.route{{font-size:14px;font-weight:700;margin-bottom:6px}}
.time{{font-size:12px;color:#67e8f9;font-weight:600;margin-bottom:5px}}
.tags{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px}}
.tag{{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px}}
.tag.honsen{{background:rgba(239,68,68,.18);color:#f87171}}
.tag.iri{{background:rgba(245,158,11,.18);color:#fbbf24}}
.note{{font-size:12px;color:#9999b8;line-height:1.5}}
.footer-note{{background:#161628;border:1px solid #2a2a4a;border-radius:12px;padding:14px 16px;
  font-size:11px;color:#7878a0;line-height:1.7;margin-top:24px}}
.empty-msg{{text-align:center;color:#7878a0;font-size:13px;padding:30px 10px}}
</style>
</head>
<body>

<button onclick="history.back()" style="display:block;width:100%;background:#161628;border:1px solid #2a2a4a;
  border-radius:10px;padding:11px;margin-bottom:14px;color:#e8e8f4;font-size:14px;font-weight:700;cursor:pointer">
  ← アプリに戻る
</button>

<h1>🚧 首都高 工事・規制情報</h1>
<div class="sub">大規模・長期規制の一覧＋日別工事マップへのリンク</div>
<div class="updated">🔄 自動更新：{escape_html(fetched_at)} 時点（1日3回・11時/17時/21時ごろに自動更新されます）</div>
{error_banner}

<div class="filter-row">
  <button class="filter-btn active" id="filter-today" onclick="setFilter('today')">📍 本日・夜勤帯のみ</button>
  <button class="filter-btn" id="filter-all" onclick="setFilter('all')">📋 全期間表示</button>
</div>

<a class="linkbtn" href="{CONSTRUCTION_MAP_URL}" target="_blank">
  📅 日別・時間帯別の工事マップを見る
  <span class="small">今日・明日など、特定の日時の工事箇所をピンポイントで確認</span>
</a>

<div id="items-container">
{body_sections}
</div>
<div class="empty-msg" id="empty-msg" style="display:none">本日に関係する規制はありません</div>

<a class="linkbtn" href="{LARGESCALE_URL}" target="_blank" style="margin-top:20px">
  📋 最新の一覧をサイトで直接見る
</a>

<div class="footer-note">
  出典：首都高ドライバーズサイト・首都高工事情報マップ（首都高速道路株式会社）。緊急工事等により予告なく変更される場合があります。おでかけ前に必ずリンク先で最新情報をご確認ください。<br>
  このページは自動更新スクリプトにより生成されています。
</div>

<script>
function shiftDayWindow(){{
  // 深夜0時〜午前5時は「まだ前日の勤務中」とみなし、前日〜当日の2日間を対象にする
  const now=new Date(new Date().toLocaleString('en-US',{{timeZone:'Asia/Tokyo'}}));
  if(now.getHours()<5) now.setDate(now.getDate()-1);
  const toISO=d=>{{const y=d.getFullYear(),m=String(d.getMonth()+1).padStart(2,'0'),dd=String(d.getDate()).padStart(2,'0');return y+'-'+m+'-'+dd;}};
  const day1=toISO(now);
  const tomorrow=new Date(now);tomorrow.setDate(tomorrow.getDate()+1);
  const day2=toISO(tomorrow);
  return [day1,day2];
}}
function setFilter(mode){{
  const [day1,day2]=shiftDayWindow();
  const items=document.querySelectorAll('#items-container .item');
  let visibleCount=0;
  items.forEach(el=>{{
    const start=el.getAttribute('data-start');
    const end=el.getAttribute('data-end');
    let show=true;
    if(mode==='today'){{
      if(start&&end){{
        show=!(end<day1||start>day2); // [day1,day2]の範囲と少しでも重なればtrue（夜勤の2日またぎに対応）
      }}else{{
        show=false; // 日付が読み取れないものは「本日分」からは除外
      }}
    }}
    el.style.display=show?'block':'none';
    if(show)visibleCount++;
  }});
  document.querySelectorAll('#items-container .date-head').forEach(head=>{{
    let sib=head.nextElementSibling,anyVisible=false;
    while(sib&&!sib.classList.contains('date-head')){{
      if(sib.classList.contains('item')&&sib.style.display!=='none')anyVisible=true;
      sib=sib.nextElementSibling;
    }}
    head.style.display=(mode==='today'&&!anyVisible)?'none':'flex';
  }});
  document.getElementById('empty-msg').style.display=(mode==='today'&&visibleCount===0)?'block':'none';
  document.getElementById('filter-today').classList.toggle('active',mode==='today');
  document.getElementById('filter-all').classList.toggle('active',mode==='all');
}}
setFilter('today');
</script>

</body>
</html>
"""
    return html


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    fetched_at = now.strftime("%Y年%m月%d日 %H:%M")
    base_year = now.year

    error_message = None
    try:
        rows = fetch_table_rows()
        items = [parse_row(r) for r in rows]

        grouped = {}
        for it in items:
            label, key_date = extract_group_date(it["datetime"])
            grouped.setdefault((key_date, label), []).append(it)

        items_by_date = [
            (label, grouped[(key_date, label)])
            for (key_date, label) in sorted(grouped.keys(), key=lambda x: x[0])
        ]

        if not items_by_date:
            raise RuntimeError("データが0件でした")

    except Exception as e:  # noqa: BLE001
        error_message = str(e)
        # 取得失敗時は既存ファイルを保持し、エラーバナーだけ追記して終了
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing = f.read()
            print(f"取得失敗のため既存ファイルを維持します: {error_message}", file=sys.stderr)
            sys.exit(0)
        except FileNotFoundError:
            items_by_date = []

    html = build_page(items_by_date, fetched_at, base_year, error_message=error_message)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"更新完了: {OUTPUT_PATH}（{len(items_by_date)}日分のグループ）")


if __name__ == "__main__":
    main()
