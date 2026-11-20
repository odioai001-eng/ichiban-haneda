#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capture.py の動作確認（自己診断）。インターネットには出ず、このパソコンの中だけで動きます。

    python selftest.py

パソコン内に「疑似の乗り場カメラのサイト」を立てて、capture.py が
・見出し／時刻／写真を正しく読み取るか
・ロゴなどの小さな画像を除くか
・文字コード（UTF-8／Shift_JIS）の違いを扱えるか
・サイトの不調（500エラー・写真でないデータ）でも止まらないか
・写真が更新されていないとき "same" と記録するか
などを確かめます。最後に「すべて合格」と出れば、道具そのものは正しく動いています。
（本物のサイトに届くかどうかは、python capture.py --diagnose で確かめます。）
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import os
import struct
import sys
import tempfile
import threading
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ["HSM_ALLOW_FAST"] = "1"
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass
import capture  # noqa: E402

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    (PASSED if cond else FAILED).append(name)
    print(("  ○ " if cond else "  × ") + name + ("" if cond else "   ← %s" % detail))


def fake_jpeg(w, h, seed):
    """大きさの情報だけ持つ、試験用のJPEG風データ（中身は画像ではない）。"""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">H", 17) + b"\x08" + struct.pack(">HH", h, w) + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    pad = hashlib.sha256(str(seed).encode()).digest() * 100
    return b"\xff\xd8" + app0 + sof + b"\xff\xda" + pad + b"\xff\xd9"


def fake_png(w, h):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + b"\x00" * 3000


STATE = {"counter": 0}

PAGE_A = """<!doctype html><html><head><meta charset="utf-8"><title>羽田空港TPシステム</title></head><body>
<h1>羽田空港TPシステム</h1>
<button>再読み込み</button><button>待機所選択</button><button>乗り場選択</button>
<img src="/a/img/logo.png">
<div class="hd">【第１ターミナル】<br>第１乗り場の状況</div>
<img src="cam/Real101.jpg"><div>2026/11/20 14:24:13</div>
<div class="hd">【第１ターミナル】<br>第２乗り場の状況</div>
<img src="/a/cam/Real102.jpg"><div>2026/11/20 14:24:15</div>
<img src="thumb.jpg"><img src="icon.svg">
<div class="popup"><button>第１乗り場</button><button>第２乗り場</button><button>閉じる</button></div>
</body></html>"""

PAGE_B = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS"></head><body>
<div>【第２ターミナル】<br>第３乗り場の状況</div>
<img src="/b/blank.gif" data-src="Real201.jpg"><div>2026/11/20 14:25:01</div>
</body></html>"""

PAGE_C = """<html><body><script>var cams=["Real301.jpg?x=1","Real302.jpg"]; var logo="/c/logo.png";</script></body></html>"""

PAGE_E = """<html><body><div>【試験】壊れた写真</div><img src="notimage.jpg"></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/a/hnd1.php":
            return self.send(200, PAGE_A.encode("utf-8"), "text/html; charset=UTF-8")
        if path == "/b/hnd2.php":
            return self.send(200, PAGE_B.encode("cp932"), "text/html")
        if path == "/c/page.php":
            return self.send(200, PAGE_C.encode("utf-8"), "text/html; charset=UTF-8")
        if path == "/d/err.php":
            return self.send(500, b"error", "text/plain")
        if path == "/e/bad.php":
            return self.send(200, PAGE_E.encode("utf-8"), "text/html; charset=UTF-8")
        if path == "/e/notimage.jpg":
            return self.send(200, b"<html>" + b"x" * 3000 + b"</html>", "text/html")
        if path == "/f/redirect.php":
            self.send_response(302)
            self.send_header("Location", "/a/hnd1.php")
            self.end_headers()
            return
        if path == "/a/cam/Real101.jpg":                      # いつも同じ写真（更新されない）
            return self.send(200, fake_jpeg(640, 360, "fixed101"), "image/jpeg")
        if path in ("/a/cam/Real102.jpg", "/b/Real201.jpg", "/c/Real301.jpg", "/c/Real302.jpg"):
            STATE["counter"] += 1                              # 毎回ちがう写真
            return self.send(200, fake_jpeg(640, 360, STATE["counter"]), "image/jpeg")
        if path == "/a/thumb.jpg":
            return self.send(200, fake_jpeg(32, 32, "thumb") + b"\x00" * 3000, "image/jpeg")
        self.send(404, b"not found", "text/plain")


def read_csv(data_dir):
    with open(os.path.join(data_dir, capture.CSV_NAME), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def quiet_main(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = capture.main(args)
    return code, buf.getvalue()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    base = "http://127.0.0.1:%d" % server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    A, B, C, D, E, F = (base + p for p in ("/a/hnd1.php", "/b/hnd2.php", "/c/page.php", "/d/err.php", "/e/bad.php", "/f/redirect.php"))

    print("■ 読み取り（1回の記録）")
    with tempfile.TemporaryDirectory() as tmp:
        code, out = quiet_main(["--once", "--pages", A, B, C, D, E, "--data-dir", tmp])
        rows = read_csv(tmp)
        by = {}
        for r in rows:
            by.setdefault(r["page"], []).append(r)
        check("ページAで写真2枚を保存", [r["status"] for r in by["hnd1"]] == ["saved", "saved"], str(by.get("hnd1")))
        a1 = by["hnd1"][0]
        check("見出しを読み取る（改行で分かれていても1つにつなぐ）", a1["label"] == "【第１ターミナル】 第１乗り場の状況", a1["label"])
        check("ページ上の時刻を読み取る", a1["page_time"] == "2026-11-20 14:24:13", a1["page_time"])
        check("写真の大きさを読み取る", (a1["width"], a1["height"]) == ("640", "360"), "%s x %s" % (a1["width"], a1["height"]))
        check("写真のファイルが保存されている", os.path.isfile(os.path.join(tmp, *a1["file"].split("/"))), a1["file"])
        check("相対URL・絶対パスのURLをどちらも扱える", by["hnd1"][1]["image_url"].endswith("/a/cam/Real102.jpg"), by["hnd1"][1]["image_url"])
        check("ロゴ・小さな画像・svgは記録しない", len(by["hnd1"]) == 2 and not any("logo" in r["image_url"] or "thumb" in r["image_url"] for r in rows))
        check("Shift_JISのページを読める（遅延読み込み画像も）", [r["status"] for r in by["hnd2"]] == ["saved"] and by["hnd2"][0]["label"] == "【第２ターミナル】 第３乗り場の状況", str(by.get("hnd2")))
        check("<img>が無いページは、スクリプト内の文字列から拾う", [r["status"] for r in by["page"]] == ["saved", "saved"], str(by.get("page")))
        check("500エラーでも止まらず、記録に残す", by["err"][0]["status"] == "error" and "HTTP 500" in by["err"][0]["error"], str(by.get("err")))
        check("写真でないデータは、エラーとして記録する", by["bad"][0]["status"] == "error" and "写真として読めません" in by["bad"][0]["error"], str(by.get("bad")))
        check("1枚でも取れていれば終了コード0", code == 0, str(code))

    print("■ 写真の更新の判定（2回続けて記録）")
    with tempfile.TemporaryDirectory() as tmp:
        quiet_main(["--cycles", "2", "--interval", "1", "--offset", "0", "--pages", A, "--data-dir", tmp])
        rows = read_csv(tmp)
        seq101 = [r["status"] for r in rows if r["cam"] == "hnd1_1"]
        seq102 = [r["status"] for r in rows if r["cam"] == "hnd1_2"]
        check("更新されない写真は2回目に same", seq101 == ["saved", "same"], str(seq101))
        check("更新された写真は2回とも saved", seq102 == ["saved", "saved"], str(seq102))
        same_row = [r for r in rows if r["status"] == "same"][0]
        check("same の行は、写真ファイルを増やさない", same_row["file"] == "" and same_row["sha1"], str(same_row))

    print("■ その他")
    with tempfile.TemporaryDirectory() as tmp:
        code, _ = quiet_main(["--once", "--no-images", "--pages", A, "--data-dir", tmp])
        rows = read_csv(tmp)
        check("--no-images: 写真を保存せず記録だけ", all(r["status"] == "new" and r["file"] == "" for r in rows) and not os.path.exists(os.path.join(tmp, "images")), str(rows))
    with tempfile.TemporaryDirectory() as tmp:
        quiet_main(["--once", "--pages", F, "--data-dir", tmp])
        rows = read_csv(tmp)
        check("転送（リダイレクト）されても、転送先を基準に写真を読める", [r["status"] for r in rows] == ["saved", "saved"], str(rows))
    with tempfile.TemporaryDirectory() as tmp:
        code, out = quiet_main(["--diagnose", "--pages", A, D, "--data-dir", tmp])
        summary = open(os.path.join(tmp, "diag", "summary.txt"), encoding="utf-8").read()
        check("--diagnose: 結果の要約が保存される", "記録の対象になる写真: 2件（小さくて除外: 1件）" in summary and "× 取得できません: HTTP 500" in summary, summary[:300])
        check("--diagnose: ページのHTMLと写真が保存される", os.path.isfile(os.path.join(tmp, "diag", "hnd1.html")) and os.path.isfile(os.path.join(tmp, "diag", "hnd1_1.jpg")))
        check("--diagnose: 1ページでも読めれば終了コード0", code == 0, str(code))
    with tempfile.TemporaryDirectory() as tmp:
        code, out = quiet_main(["--diagnose", "--pages", D, "--data-dir", tmp])
        check("--diagnose: どのページも読めなければ終了コード2（国内の回線かどうかの案内つき）", code == 2 and "日本国内の回線" in out, "%s %s" % (code, out[:200]))

    print("■ 部品")
    check("JPEGの大きさを読める", capture.image_info(fake_jpeg(640, 360, 1)) == ("jpg", 640, 360))
    check("PNGの大きさを読める", capture.image_info(fake_png(320, 240)) == ("png", 320, 240))
    check("画像でないデータは None", capture.image_info(b"<html>" + b"x" * 100) is None and capture.image_info(b"") is None)
    s = "【第１ターミナル】第１乗り場"
    check("文字コード: UTF-8 / Shift_JIS / EUC-JP", all(capture.decode_html(s.encode(enc), "")[0] == s for enc in ("utf-8", "cp932", "euc-jp")))
    check("次の記録時刻（毎分8秒目）", capture.next_tick(1000.5, 60, 8) == 1028 and capture.next_tick(1020, 60, 8) == 1028 and capture.next_tick(1030, 60, 8) == 1088)
    with tempfile.TemporaryDirectory() as tmp:
        for d in ("20200101", "20261101", "20261120", "notadate"):
            os.makedirs(os.path.join(tmp, "images", d, "cam"))
        n = capture.prune_old_images(tmp, 30, dt.date(2026, 11, 20))
        left = sorted(os.listdir(os.path.join(tmp, "images")))
        check("古い日付のフォルダだけを消す（30日より前）", n == 1 and left == ["20261101", "20261120", "notadate"], str(left))
        check("keep-days=0 なら何も消さない", capture.prune_old_images(tmp, 0, dt.date(2030, 1, 1)) == 0)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "captures.csv")
        os.makedirs(path)                                      # 書けない状態（Excelで開いているのに近い）をつくる
        log = capture.CsvLog(path)
        log.add([capture.make_row(dt.datetime.now(capture.JST), "x", status="same")])
        with redirect_stdout(io.StringIO()):
            ok = log.flush()
        check("CSVに書けない間は、記録をためておく", ok is False and len(log.buffer) == 1)
        os.rmdir(path)
        ok = log.flush()
        check("書けるようになったら、まとめて書く", ok is True and len(log.buffer) == 0 and os.path.isfile(path))
    os.environ.pop("HSM_ALLOW_FAST", None)                     # 試験用の例外を外して、本来の動きを確かめる
    try:
        with redirect_stdout(io.StringIO()), open(os.devnull, "w") as devnull:
            real_stderr, sys.stderr = sys.stderr, devnull
            try:
                capture.parse_args(["--interval", "30"])
            finally:
                sys.stderr = real_stderr
        check("--interval 60未満は断る", False, "断られなかった")
    except SystemExit:
        check("--interval 60未満は断る", True)
    os.environ["HSM_ALLOW_FAST"] = "1"

    server.shutdown()
    print()
    if FAILED:
        print("× %d 件が不合格です:" % len(FAILED))
        for n in FAILED:
            print("   - " + n)
        return 1
    print("○ すべて合格（%d項目）。道具そのものは、このパソコンで正しく動いています。" % len(PASSED))
    return 0


if __name__ == "__main__":
    sys.exit(main())
