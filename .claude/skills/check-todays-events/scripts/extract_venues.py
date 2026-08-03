#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
event_hub.html の「🚕 長距離が狙える会場」セクションから、
会場名・公式リンク・エリア・サブカテゴリを抽出する。

このセクションは日付に関係ない固定リストなので、決定的に（LLMの読み取りに頼らず）
抽出できる。check-todays-events スキルはこのスクリプトの出力を使って
各会場の公式リンクを回り、今日のイベント有無を調べる。

Usage: python extract_venues.py [path/to/event_hub.html]
Output: JSON array on stdout: [{"name", "href", "area", "category"}, ...]
"""
import json
import re
import sys

START_MARKER = "長距離が狙える会場"
END_MARKER = 'class="note warn"'

CARD_BLOCK_RE = re.compile(r'<a class="card" href="([^"]+)"[^>]*>(.*?)</a>', re.S)
VENUE_NAME_RE = re.compile(r'<span class="venue-name">([^<]+)</span>')
EVENT_NAME_RE = re.compile(r'<div class="event-name">([^<]*)</div>')
SUBCAT_RE = re.compile(r'<div class="subcat">([^<]+)</div>')


def extract(html: str):
    """会場カードを <a class="card">...</a> ブロック単位で切り出してから中身を読む。
    event-name の有無やフィールドの並び順に依存しないようにするため、
    「タグの並びを一気に正規表現でマッチさせる」方式ではなく2段階で処理する。"""
    start = html.find(START_MARKER)
    if start == -1:
        raise ValueError(f"開始マーカーが見つかりません: {START_MARKER!r}")
    end = html.find(END_MARKER, start)
    if end == -1:
        raise ValueError(f"終了マーカーが見つかりません: {END_MARKER!r}")
    section = html[start:end]

    tokens = []
    for m in SUBCAT_RE.finditer(section):
        tokens.append((m.start(), "subcat", m.group(1).strip()))
    for m in CARD_BLOCK_RE.finditer(section):
        href, body = m.group(1).strip(), m.group(2)
        name_m = VENUE_NAME_RE.search(body)
        if not name_m:
            continue  # venue-name が無いカードは会場カードとみなさない
        event_m = EVENT_NAME_RE.search(body)
        area = event_m.group(1).strip() if event_m else ""
        tokens.append((m.start(), "card", (href, name_m.group(1).strip(), area)))
    tokens.sort(key=lambda t: t[0])

    venues = []
    current_subcat = None
    for _, kind, payload in tokens:
        if kind == "subcat":
            current_subcat = payload
        else:
            href, name, area = payload
            venues.append({"name": name, "href": href, "area": area, "category": current_subcat})
    return venues


def main():
    # Windows環境ではstdout/stderrの既定エンコーディングがcp932(Shift-JIS)になり、
    # 日本語のJSON出力が文字化けするため、明示的にUTF-8へ切り替える。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    path = sys.argv[1] if len(sys.argv) > 1 else "event_hub.html"
    try:
        with open(path, encoding="utf-8") as f:
            html = f.read()
        venues = extract(html)
    except (OSError, ValueError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    if not venues:
        print(json.dumps({"error": "会場が1件も抽出できませんでした（HTML構造が変わった可能性）"},
                          ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(venues, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
