#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""羽田空港タクシー乗り場ライブカメラの記録ツール（個人利用・第1版）

東京タクシーセンターが公開している羽田空港のタクシー乗り場ライブカメラ
（https://ttc.taxi-inf.jp/hnd1.php など。写真は1分ごとに更新）から、
写真と、写真に添えられた時刻を、1分ごとに記録します。

使い方（詳しくは references/quickstart_ja.md）:
    python capture.py --diagnose   # まず1回だけ。ページの作りと、写真が取れるかを確かめる
    python capture.py              # 1分ごとの記録を続ける（止めるときは Ctrl+C）
    python capture.py --once       # 1回だけ記録して終わる

標準ライブラリだけで動きます（Python 3.8 以上。追加のインストールは不要）。
日本国内の回線から実行してください（海外のサーバーからは届かない作りです）。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as htmlmod
import http.client
import os
import platform
import random
import re
import shutil
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1"
JST = dt.timezone(dt.timedelta(hours=9), "JST")
DEFAULT_PAGES = ["https://ttc.taxi-inf.jp/hnd1.php", "https://ttc.taxi-inf.jp/hnd2.php"]
DEFAULT_DATA_DIR = os.path.join("~", "haneda-stand-data")
CSV_NAME = "captures.csv"
CSV_FIELDS = ["captured_at", "page", "cam", "label", "page_time", "status",
              "image_url", "bytes", "width", "height", "sha1", "file", "error"]
MIN_W, MIN_H = 160, 90      # これより小さい画像は、ロゴ・アイコンとみなして除く
MIN_BYTES = 2000            # これより小さいデータは、写真ではないとみなす

TS_RE = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?")
LIT_RE = re.compile(r"""["']([^"'<>\s]+?\.(?:jpe?g|png)(?:\?[^"'<>\s]*)?)["']""", re.I)
SKIP_WORDS = ("logo", "icon", "btn", "button", "arrow", "spacer", "blank", "banner", "pixel", "sprite")


# ---------------------------------------------------------------- 通信

class FetchError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def http_get(url, ua, timeout, referer=None, no_cache=False):
    """(状態コード, ヘッダー(小文字キー), 中身, 最終URL) を返す。失敗したら FetchError。"""
    headers = {"User-Agent": ua, "Accept": "*/*", "Accept-Language": "ja,en;q=0.5"}
    if referer:
        headers["Referer"] = referer
    if no_cache:
        headers["Cache-Control"] = "no-cache"
        headers["Pragma"] = "no-cache"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return r.status, {k.lower(): v for k, v in r.headers.items()}, data, r.geturl()
    except urllib.error.HTTPError as e:
        raise FetchError("HTTP %s" % e.code, e.code)
    except urllib.error.URLError as e:
        raise FetchError("接続できません（%s）" % (e.reason,))
    except (http.client.HTTPException, OSError) as e:      # 時間切れ・切断など
        raise FetchError("通信エラー（%s）" % (e,))
    except ValueError as e:
        raise FetchError("URLが正しくありません（%s）" % (e,))


def decode_html(data, content_type=""):
    """HTMLの文字コードを見分けて文字列にする。(文字列, 文字コード名)"""
    cands = []
    m = re.search(r"charset=([\w\-]+)", content_type or "", re.I)
    if m:
        cands.append(m.group(1))
    m = re.search(rb"charset\s*=\s*[\"']?([\w\-]+)", data[:4000], re.I)
    if m:
        cands.append(m.group(1).decode("ascii", "ignore"))
    cands += ["utf-8", "cp932", "euc-jp"]
    for enc in cands:
        if enc.lower().replace("_", "-") in ("shift-jis", "sjis", "x-sjis", "windows-31j"):
            enc = "cp932"
        try:
            return data.decode(enc), enc
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", "replace"), "utf-8(replace)"


# ---------------------------------------------------------------- 画像

def image_info(data):
    """(形式, 幅, 高さ)。JPEG/PNGとして読めなければ None。標準ライブラリだけで大きさを読む。"""
    if data[:3] == b"\xff\xd8\xff":
        i, n = 2, len(data)
        while i + 9 < n:
            if data[i] != 0xFF:
                i += 1
                continue
            while i < n and data[i] == 0xFF:        # 詰め物の FF を飛ばす
                i += 1
            if i >= n:
                break
            marker = data[i]
            i += 1
            if marker in (0x01, 0xD8) or 0xD0 <= marker <= 0xD7:
                continue
            if marker in (0xD9, 0xDA):              # 画像の終わり／画像データの始まり
                break
            if i + 2 > n:
                break
            seglen = struct.unpack(">H", data[i:i + 2])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                if i + 7 > n:
                    break
                h, w = struct.unpack(">HH", data[i + 3:i + 7])
                return "jpg", w, h
            i += seglen
        return None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return "png", w, h
    return None


# ---------------------------------------------------------------- ページの読み取り

def attr(tag, name):
    """タグの文字列から、属性の値を取り出す（data-src と src を取り違えない）。"""
    m = re.search(r"""(?is)(?<![\w:-])""" + re.escape(name) + r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", tag)
    if not m:
        return None
    return htmlmod.unescape(next(g for g in m.groups() if g is not None)).strip()


def plausible_camera_src(src):
    s = (src or "").lower().split("?")[0]
    if not s or s.startswith("data:") or s.endswith((".svg", ".ico", ".gif")):
        return False
    name = s.rsplit("/", 1)[-1]
    return not any(w in name for w in SKIP_WORDS)


def norm_time(m):
    y, mo, d, h, mi, s = m.groups()
    return "%04d-%02d-%02d %02d:%02d:%02d" % (int(y), int(mo), int(d), int(h), int(mi), int(s or 0))


def page_lines(page_html):
    """HTMLを、1行ずつの文字と画像の並びにする。画像は '\\x00IMG\\x00<src>' の行になる。"""
    body = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1\s*>", " ", page_html)

    def img_repl(m):
        tag = m.group(0)
        cands = [attr(tag, n) for n in ("src", "data-src", "data-original", "data-lazy-src")]
        cands = [c for c in cands if c]
        # 遅延読み込みでは src が空白画像になっていることがある。写真らしいものを優先して選ぶ
        src = next((c for c in cands if plausible_camera_src(c)), cands[0] if cands else None)
        return "\n\x00IMG\x00%s\n" % src if src else "\n"

    body = re.sub(r"(?is)<img\b[^>]*>", img_repl, body)
    body = re.sub(r"(?is)<br\s*/?>", "\n", body)
    body = re.sub(r"(?s)<[^>]+>", "\n", body)
    body = htmlmod.unescape(body)
    lines = [re.sub(r"[ \t　]+", " ", ln).strip() for ln in body.split("\n")]
    return [ln for ln in lines if ln]


def parse_sections(page_html):
    """見出し（【第１ターミナル】第１乗り場の状況 など）・写真・時刻の組を、ページの順に取り出す。"""
    sections, cur = [], None
    for ln in page_lines(page_html):
        if ln.startswith("\x00IMG\x00"):
            src = ln[5:]
            if not plausible_camera_src(src):
                continue
            if cur is None or cur["src"]:
                cur = {"label": "", "src": None, "page_time": ""}
                sections.append(cur)
            cur["src"] = src
            continue
        if "【" in ln and "】" in ln:                      # 見出しの始まり
            cur = {"label": ln, "src": None, "page_time": ""}
            sections.append(cur)
            continue
        m = TS_RE.search(ln)
        if m and cur is not None and cur["src"] and not cur["page_time"]:
            cur["page_time"] = norm_time(m)
            continue
        if cur is not None and cur["label"] and not cur["src"] and len(ln) <= 40:
            cur["label"] += " " + ln                       # 見出しが改行で分かれている場合の続き
    return [s for s in sections if s["src"]]


def fallback_sections(page_html):
    """<img> が見つからないとき、スクリプトの中の「〜.jpg」という文字列から写真を探す。"""
    seen, out = set(), []
    for m in LIT_RE.finditer(page_html):
        src = htmlmod.unescape(m.group(1))
        if src in seen or not plausible_camera_src(src):
            continue
        seen.add(src)
        out.append({"label": "", "src": src, "page_time": ""})
    return out


def page_stem(url):
    name = os.path.basename(urllib.parse.urlparse(url).path) or "page"
    return re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(name)[0]) or "page"


# ---------------------------------------------------------------- 記録

def bust(url):
    """写真の再取得用に、URLの末尾へ時刻を付ける（古い写真が使い回されるのを避ける）。"""
    return url + ("&" if "?" in url else "?") + str(int(time.time()))


def make_row(now, page, cam="", label="", page_time="", status="", image_url="",
             nbytes="", width="", height="", sha1="", file="", error=""):
    return {"captured_at": now.strftime("%Y-%m-%d %H:%M:%S"), "page": page, "cam": cam, "label": label,
            "page_time": page_time, "status": status, "image_url": image_url, "bytes": nbytes,
            "width": width, "height": height, "sha1": sha1, "file": file, "error": error}


def process_page(page_url, cfg, state, now, log):
    """1ページ分を記録して、CSVの行のリストを返す。"""
    stem = page_stem(page_url)
    try:
        _, headers, data, final = http_get(page_url, cfg.ua, cfg.timeout)
    except FetchError as e:
        log("  %s: ページを取得できません: %s" % (stem, e))
        return [make_row(now, stem, status="error", error="ページを取得できません: %s" % e)]
    page_html, _ = decode_html(data, headers.get("content-type", ""))
    sections = parse_sections(page_html) or fallback_sections(page_html)
    if not sections:
        msg = "写真が見つかりません（ページの作りが想定と違う可能性。python capture.py --diagnose を実行してください）"
        log("  %s: %s" % (stem, msg))
        return [make_row(now, stem, status="error", error=msg)]
    rows, seen = [], set()
    for idx, sec in enumerate(sections, 1):
        url = urllib.parse.urljoin(final, sec["src"])
        if url in seen or url in state["small"]:
            continue
        seen.add(url)
        cam = "%s_%d" % (stem, idx)
        base = dict(page=stem, cam=cam, label=sec["label"], page_time=sec["page_time"], image_url=url)
        try:
            _, ih, img, _ = http_get(bust(url), cfg.ua, cfg.timeout, referer=final, no_cache=True)
        except FetchError as e:
            rows.append(make_row(now, status="error", error="写真を取得できません: %s" % e, **base))
            log("  %s: 写真を取得できません: %s" % (cam, e))
            continue
        info = image_info(img)
        if info is None or len(img) < MIN_BYTES:
            err = "写真として読めません（%s, %dバイト）" % (ih.get("content-type", "?"), len(img))
            rows.append(make_row(now, status="error", error=err, **base))
            log("  %s: %s" % (cam, err))
            continue
        fmt, w, h = info
        if w < MIN_W or h < MIN_H:                       # ロゴ・アイコン。次回からは見ない
            state["small"].add(url)
            continue
        sha = hashlib.sha1(img).hexdigest()
        same = state["last_sha"].get(cam) == sha
        state["last_sha"][cam] = sha
        rel = ""
        if same:
            status = "same"                              # 前回から更新されていない
        elif cfg.no_images:
            status = "new"
        else:
            rel = "/".join(["images", now.strftime("%Y%m%d"), cam, "%s_%s.%s" % (cam, now.strftime("%H%M%S"), fmt)])
            full = os.path.join(cfg.data_dir, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(img)
            status = "saved"
        rows.append(make_row(now, status=status, nbytes=len(img), width=w, height=h, sha1=sha, file=rel, **base))
        log("  %s: %s %dx%d %s%s" % (cam, status, w, h, sec["page_time"] or "(ページ上の時刻なし)",
                                     " [%s]" % sec["label"] if sec["label"] else ""))
    return rows


class CsvLog:
    """CSVへ追記する。Excelなどで開いていて書けないときは、次の回にまとめて書く。"""

    def __init__(self, path):
        self.path, self.buffer = path, []

    def add(self, rows):
        self.buffer.extend(rows)
        if len(self.buffer) > 20000:
            del self.buffer[:10000]

    def flush(self):
        if not self.buffer:
            return True
        new = not os.path.exists(self.path)
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                if new:
                    w.writeheader()
                w.writerows(self.buffer)
            self.buffer.clear()
            return True
        except OSError as e:
            print("  ! 記録ファイルに書けません（Excelで開いたままではありませんか？）。次の回にまとめて書きます: %s" % e)
            return False


def prune_old_images(data_dir, keep_days, today):
    """keep_days日より古い日付フォルダ（images/YYYYMMDD）だけを消す。CSVは消さない。"""
    root = os.path.join(data_dir, "images")
    if keep_days <= 0 or not os.path.isdir(root):
        return 0
    cutoff = (today - dt.timedelta(days=keep_days)).strftime("%Y%m%d")
    removed = 0
    for name in sorted(os.listdir(root)):
        if re.fullmatch(r"\d{8}", name) and name < cutoff:
            shutil.rmtree(os.path.join(root, name), ignore_errors=True)
            removed += 1
    return removed


# ---------------------------------------------------------------- 実行

def next_tick(now_ts, interval, offset):
    """次に記録する時刻（秒）。毎分 offset 秒目（interval=60の場合）に取る。"""
    t = int(now_ts // interval) * interval + offset
    return t if t > now_ts else t + interval


def log_line(msg):
    print("%s %s" % (dt.datetime.now(JST).strftime("%H:%M:%S"), msg), flush=True)


def run_loop(cfg):
    csvlog = CsvLog(os.path.join(cfg.data_dir, CSV_NAME))
    state = {"last_sha": {}, "small": set()}
    log_line("記録を始めます。保存先: %s（止めるときは Ctrl+C）" % cfg.data_dir)
    log_line("ページ: %s / %d秒ごと / 写真は%s" % (", ".join(page_stem(p) for p in cfg.pages), cfg.interval,
                                                  "保存しない" if cfg.no_images else "保存する（%s）" % (
                                                      "%d日分を残す" % cfg.keep_days if cfg.keep_days > 0 else "消さない")))
    last_day, fail_streak, cycle = None, 0, 0
    try:
        while True:
            now = dt.datetime.now(JST)
            if last_day != now.date():
                last_day = now.date()
                n = prune_old_images(cfg.data_dir, cfg.keep_days, now.date())
                if n:
                    log_line("古い写真のフォルダを %d 日分、消しました（%d日より前）" % (n, cfg.keep_days))
            rows = []
            for page in cfg.pages:
                try:
                    rows += process_page(page, cfg, state, now, log_line)
                except Exception as e:                    # 想定外でも、記録は止めない
                    rows.append(make_row(now, page_stem(page), status="error", error="想定外のエラー: %r" % (e,)))
                    log_line("  %s: 想定外のエラー: %r" % (page_stem(page), e))
            csvlog.add(rows)
            csvlog.flush()
            ok = sum(1 for r in rows if r["status"] in ("saved", "same", "new"))
            fail_streak = 0 if ok else fail_streak + 1
            if fail_streak == 3:
                log_line("  ! 3回続けて、写真が1枚も取れていません。日本国内の回線（VPNなし）から実行していますか？ "
                         "python capture.py --diagnose で確かめられます。")
            cycle += 1
            if cfg.once or (cfg.cycles and cycle >= cfg.cycles):
                return 0 if ok else 1
            t = next_tick(time.time(), cfg.interval, cfg.offset + random.uniform(0, min(3.0, cfg.interval / 4.0)))
            while time.time() < t:
                time.sleep(min(5.0, max(0.05, t - time.time())))
    except KeyboardInterrupt:
        csvlog.flush()
        log_line("止めました。記録は %s にあります。" % cfg.data_dir)
        return 0


def diagnose(cfg):
    out_dir = os.path.join(cfg.data_dir, "diag")
    os.makedirs(out_dir, exist_ok=True)
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    say("haneda-stand-monitor %s / Python %s / %s" % (VERSION, platform.python_version(), platform.platform()))
    say("実行時刻: %s" % dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"))
    ok_pages = 0
    for page in cfg.pages:
        stem = page_stem(page)
        say("")
        say("■ %s" % page)
        try:
            status, headers, data, final = http_get(page, cfg.ua, cfg.timeout)
        except FetchError as e:
            say("  × 取得できません: %s" % e)
            say("    → 日本国内の回線（自宅のWi-Fi・日本のモバイル回線）から実行していますか？ VPNは切ってください。")
            continue
        ok_pages += 1
        page_html, enc = decode_html(data, headers.get("content-type", ""))
        with open(os.path.join(out_dir, stem + ".html"), "w", encoding="utf-8") as f:
            f.write(page_html)
        say("  HTTP %s / %s / %dバイト / 文字コード %s" % (status, headers.get("content-type", "?"), len(data), enc))
        if final != page:
            say("  最終URL: %s" % final)
        sections = parse_sections(page_html)
        fb = False
        if not sections:
            sections, fb = fallback_sections(page_html), True
        say("  写真の候補: %d件%s" % (len(sections), "（<img>が無く、スクリプト内の文字列から拾いました）" if fb else ""))
        usable = small = 0
        for i, sec in enumerate(sections, 1):
            url = urllib.parse.urljoin(final, sec["src"])
            say("  [%d] 見出し: %s / ページ上の時刻: %s" % (i, sec["label"] or "（なし）", sec["page_time"] or "（なし）"))
            say("      写真のURL: %s" % url)
            try:
                st, ih, img, _ = http_get(bust(url), cfg.ua, cfg.timeout, referer=final, no_cache=True)
            except FetchError as e:
                say("      × 写真を取得できません: %s" % e)
                continue
            info = image_info(img)
            if info is None:
                say("      × 写真として読めません（%s, %dバイト）" % (ih.get("content-type", "?"), len(img)))
                continue
            fmt, w, h = info
            is_small = w < MIN_W or h < MIN_H
            usable, small = usable + (not is_small), small + is_small
            say("      → HTTP %s / %s %dx%d / %dバイト / 写真ファイルの更新時刻: %s%s" % (
                st, fmt, w, h, len(img), ih.get("last-modified", "（なし）"),
                "  ※小さいので、普段の記録では除外されます" if is_small else ""))
            with open(os.path.join(out_dir, "%s_%d.%s" % (stem, i, fmt)), "wb") as f:
                f.write(img)
        say("  記録の対象になる写真: %d件（小さくて除外: %d件）" % (usable, small))
        say("  --- ページの文字と画像の並び（先頭40行）---")
        for ln in page_lines(page_html)[:40]:
            say("  | " + (ln.replace("\x00IMG\x00", "[画像] ") if ln.startswith("\x00IMG\x00") else ln[:80]))
    say("")
    say("診断の結果を %s に保存しました。" % os.path.join(out_dir, "summary.txt"))
    say("この画面の内容を、そのまま Claude に貼り付けてください（写真は貼らなくて大丈夫です）。")
    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok_pages else 2


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="羽田空港タクシー乗り場ライブカメラの記録ツール（個人利用）")
    p.add_argument("--pages", nargs="+", default=DEFAULT_PAGES, help="記録するページのURL（初期値: hnd1.php と hnd2.php）")
    p.add_argument("--interval", type=int, default=60, help="何秒ごとに記録するか（60秒以上。初期値60）")
    p.add_argument("--offset", type=int, default=8, help="毎分、何秒目に取りに行くか（初期値8）")
    p.add_argument("--data-dir", default=DEFAULT_DATA_DIR, help="保存先（初期値: ホームフォルダの haneda-stand-data）")
    p.add_argument("--keep-days", type=int, default=30, help="写真を何日分残すか。0なら消さない（初期値30）")
    p.add_argument("--no-images", action="store_true", help="写真は保存せず、記録（CSV）だけにする")
    p.add_argument("--ua", default="Mozilla/5.0 (compatible; haneda-stand-monitor/%s; personal use)" % VERSION,
                   help="サイトに伝える名乗り")
    p.add_argument("--timeout", type=int, default=20, help="1回の通信を待つ秒数（初期値20）")
    p.add_argument("--once", action="store_true", help="1回だけ記録して終わる")
    p.add_argument("--cycles", type=int, default=0, help="指定した回数だけ記録して終わる（0なら止めるまで続ける）")
    p.add_argument("--diagnose", action="store_true", help="ページの作りと、写真が取れるかを確かめる")
    a = p.parse_args(argv)
    a.data_dir = os.path.abspath(os.path.expanduser(a.data_dir))
    if a.interval < 60 and not os.environ.get("HSM_ALLOW_FAST"):
        p.error("--interval は60秒以上にしてください（サイトの写真は1分ごとの更新で、それより短くしても意味がなく、"
                "サイトに負担をかけるだけです）")
    return a


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")      # コンソールで表示できない文字があっても、止まらないようにする
        except Exception:
            pass
    cfg = parse_args(argv)
    if cfg.diagnose:
        return diagnose(cfg)
    return run_loop(cfg)


if __name__ == "__main__":
    sys.exit(main())
