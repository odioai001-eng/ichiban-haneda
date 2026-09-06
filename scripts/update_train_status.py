#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Yahoo!路線情報の運行情報（関東エリア）ページを取得し、
train_status_hub.html を自動生成するスクリプト。
GitHub Actionsから15分おきに自動実行される想定。

人身事故・車両故障等による遅延・運転見合わせは発生してから解消するまでの
時間が短いことが多いため、首都高の交通規制情報（1日3回更新）よりも
高い頻度で更新する。

サイトの構造は今後変わる可能性があるため、特定のCSSクラス名に頼らず、
「平常運転」以外のステータス文言を含む行を本文から広く拾う作りにしてある。
"""
import re
import sys
import datetime
import requests
from bs4 import BeautifulSoup

URL = "https://transit.yahoo.co.jp/diainfo/area/4"
DETAIL_BASE_URL = "https://transit.yahoo.co.jp/diainfo/area/4"
OUTPUT_PATH = "train_status_hub.html"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# 平常運転とみなし、一覧からは除外する文言
NORMAL_WORDS = ("平常運転", "運転情報", "情報はありません")
# 遅延・運休等とみなすキーワード（本文にこのいずれかを含む行を「異常あり」として拾う）
TROUBLE_WORDS = ("見合わせ", "運休", "遅延", "折返し運転", "順次", "計画運休", "運転再開")


def fetch_lines():
    """運行情報ページから、路線名とステータス文言の組を取得する。
    ページ構造の変化に強くするため、特定のクラス名を前提にせず、
    路線一覧として繰り返し出現するリンク要素（路線名）と、その近くの
    ステータス文言をペアにして拾う。"""
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    results = []
    seen = set()

    # 路線名を含むリンク（例: 「JR山手線」「東急東横線」等、末尾が「線」）を手がかりに、
    # そのリンクを含む行全体（li/tr/div等の直近の繰り返し単位）のテキストから
    # ステータス文言を抜き出す
    line_links = [a for a in soup.find_all("a") if a.get_text(strip=True).endswith("線")]
    for a in line_links:
        line_name = a.get_text(strip=True)
        if line_name in seen:
            continue
        # aタグを含む「1路線ぶんの行」とみなせる直近の親要素を探す
        row = a
        row_text = ""
        for _ in range(4):
            if row.parent is None:
                break
            row = row.parent
            row_text = row.get_text(" ", strip=True)
            # 行の中に路線名以外のテキスト（ステータス）も含まれていれば、それで確定する
            if len(row_text) > len(line_name) + 1:
                break
        if not row_text:
            continue
        status_text = row_text.replace(line_name, "", 1).strip()
        if not status_text:
            continue
        seen.add(line_name)
        results.append({"line": line_name, "status": status_text})

    return results


def classify(status_text):
    """ステータス文言から、一覧に載せるべき「異常あり」かどうかを判定する"""
    if any(w in status_text for w in NORMAL_WORDS):
        return False
    return any(w in status_text for w in TROUBLE_WORDS)


def escape_html(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_item_html(item):
    return f"""<div class="item" data-line="{escape_html(item['line'])}">
  <div class="route">🚃 {escape_html(item['line'])}</div>
  <div class="status">{escape_html(item['status'])}</div>
</div>"""


def build_page(trouble_items, fetched_at, error_message=None):
    cards = "\n".join(build_item_html(it) for it in trouble_items)

    error_banner = ""
    if error_message:
        error_banner = f'''<div class="updated" style="border-color:#ef4444;color:#f87171;background:rgba(239,68,68,.1)">
  ⚠️ 自動更新に失敗しました（{escape_html(error_message)}）。前回取得分を表示しています。最新情報は下のリンクから直接ご確認ください。
</div>'''

    empty_html = '<div class="empty-msg">現在、遅延・運転見合わせ等が報告されている路線はありません</div>' if not trouble_items else ''

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>運行情報ハブ</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Hiragino Kaku Gothic ProN',sans-serif;
  background:#0d0d1a;color:#e8e8f4;min-height:100vh;padding:20px 16px 40px;max-width:480px;margin:0 auto}}
h1{{font-size:19px;font-weight:800;margin-bottom:4px;display:flex;align-items:center;gap:8px}}
.sub{{font-size:12px;color:#7878a0;margin-bottom:8px}}
.updated{{font-size:11px;color:#fbbf24;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
  border-radius:8px;padding:8px 12px;margin-bottom:14px;line-height:1.6}}
.linkbtn{{display:block;background:#161628;border:2px solid #4f8ef7;border-radius:12px;
  padding:13px 16px;margin-bottom:20px;text-decoration:none;color:#e8e8f4;text-align:center;
  font-size:14px;font-weight:700}}
.item{{background:#161628;border:1px solid #2a2a4a;border-left:4px solid #ef4444;border-radius:10px;
  padding:13px 14px;margin-bottom:10px}}
.route{{font-size:14px;font-weight:700;margin-bottom:5px}}
.status{{font-size:12px;color:#f87171;line-height:1.5;font-weight:600}}
.footer-note{{background:#161628;border:1px solid #2a2a4a;border-radius:12px;padding:14px 16px;
  font-size:11px;color:#7878a0;line-height:1.7;margin-top:24px}}
.empty-msg{{text-align:center;color:#7878a0;font-size:13px;padding:30px 10px}}
.backbtn{{display:block;width:100%;background:#161628;border:1px solid #2a2a4a;
  border-radius:10px;padding:11px;margin-bottom:14px;color:#e8e8f4;font-size:14px;font-weight:700;cursor:pointer}}
</style>
</head>
<body>

<button class="backbtn" onclick="history.back()">← アプリに戻る</button>

<h1>🚨 運行情報ハブ</h1>
<div class="sub">人身事故・車両故障等による遅延・運転見合わせが出ている路線を先読み</div>
<div class="updated">🔄 自動更新：{escape_html(fetched_at)} 時点（15分おきに自動更新されます）</div>
{error_banner}

<div id="items-container">
{cards}
</div>
{empty_html}

<a class="linkbtn" href="{DETAIL_BASE_URL}" target="_blank" style="margin-top:20px">
  📋 最新の一覧をサイトで直接見る
</a>

<div class="footer-note">
  出典：Yahoo!路線情報（運行情報）。表示内容は自動取得のため、実際の状況と一時的にずれる場合があります。出庫前・迂回判断の前に必ずリンク先で最新情報をご確認ください。<br>
  このページは自動更新スクリプトにより生成されています。
</div>

</body>
</html>
"""
    return html


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    fetched_at = now.strftime("%Y年%m月%d日 %H:%M")

    error_message = None
    trouble_items = []
    try:
        lines = fetch_lines()
        if not lines:
            raise RuntimeError("路線データが0件でした（サイト構造が変わった可能性）")
        trouble_items = [l for l in lines if classify(l["status"])]
    except Exception as e:  # noqa: BLE001
        error_message = str(e)
        try:
            with open(OUTPUT_PATH, "r", encoding="utf-8"):
                pass
            print(f"取得失敗のため既存ファイルを維持します: {error_message}", file=sys.stderr)
            sys.exit(0)
        except FileNotFoundError:
            trouble_items = []

    html = build_page(trouble_items, fetched_at, error_message=error_message)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"更新完了: {OUTPUT_PATH}（異常あり{len(trouble_items)}路線）")


if __name__ == "__main__":
    main()
