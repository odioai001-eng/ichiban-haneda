# 一時的な接続確認用（確認後に削除します）。標準ライブラリ・curl・Chromeだけを使います。
import html
import os
import re
import shutil
import subprocess
import urllib.parse

BROWSER_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36")
PLAIN_UA = "ttc-probe/1.0 (one-time connectivity check)"
BASE = os.environ.get("TTC_BASE", "https://ttc.taxi-inf.jp")
OFFICIAL = os.environ.get("TTC_OFFICIAL", "https://www.tokyo-tc.or.jp/driver/stand/haneda-stand/")
MAXPRINT = 60000


def sh(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:  # noqa
        return -1, b"", str(e).encode()


def to_text(b):
    for enc in ("utf-8", "cp932", "euc-jp"):
        try:
            return b.decode(enc), enc
        except Exception:
            pass
    return b.decode("utf-8", "replace"), "utf-8(replace)"


def fetch(url, ua=BROWSER_UA, name="f"):
    out, hdr = f"/tmp/{name}.bin", f"/tmp/{name}.hdr"
    for p in (out, hdr):
        if os.path.exists(p):
            os.remove(p)
    fmt = "%{http_code}|%{size_download}|%{content_type}|%{remote_ip}|%{ssl_verify_result}|%{time_total}|%{url_effective}"
    base = ["curl", "-sS", "-m", "30", "-L", "--max-redirs", "3", "-A", ua, "-o", out, "-D", hdr, "-w", fmt]
    rc, o, e = sh(base + [url])
    print(f"[fetch] {url}  ua={'browser' if ua == BROWSER_UA else 'plain'}\n"
          f"  curl_rc={rc}  info={o.decode('utf-8', 'replace')}\n  stderr={e.decode('utf-8', 'replace').strip()[:300]}")
    if rc in (35, 51, 58, 60):
        rc2, o2, e2 = sh(["curl", "-k"] + base[1:] + [url])
        print(f"  (診断: 証明書の確認を外して再試行) rc={rc2} info={o2.decode('utf-8', 'replace')} "
              f"stderr={e2.decode('utf-8', 'replace').strip()[:300]}")
    body = open(out, "rb").read() if os.path.exists(out) else b""
    headers = open(hdr, "rb").read().decode("latin-1", "replace") if os.path.exists(hdr) else ""
    return body, headers


def strip_tags(t):
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", "\n", t)
    t = html.unescape(t)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def structure(url, text):
    absu = lambda u: urllib.parse.urljoin(url, html.unescape(u))  # noqa
    imgs = [absu(u) for u in re.findall(r"""<img[^>]+src=["']([^"']+)["']""", text, re.I)]
    scripts = [absu(u) for u in re.findall(r"""<script[^>]+src=["']([^"']+)["']""", text, re.I)]
    metas = re.findall(r"""<meta[^>]+http-equiv=["']refresh["'][^>]*>""", text, re.I)
    links = [(absu(h), re.sub(r"\s+", " ", strip_tags(t)).strip())
             for h, t in re.findall(r"""<a[^>]+href=["']([^"']+)["'][^>]*>(.*?)</a>""", text, re.I | re.S)]
    print(f"  <img> {len(imgs)}件:"); [print("   ", u) for u in imgs[:40]]
    print(f"  <script src> {len(scripts)}件:"); [print("   ", u) for u in scripts[:20]]
    print(f"  meta refresh: {metas}")
    print(f"  <a> {len(links)}件:"); [print("   ", t[:40], "->", h) for h, t in links[:40]]
    return imgs, links


def show_page(label, url):
    print("\n" + "#" * 20, label, url)
    body, headers = fetch(url, name=label)
    print("--- headers\n" + headers[:1500])
    if not body:
        return [], [], ""
    text, enc = to_text(body)
    print(f"--- encoding={enc} chars={len(text)}")
    imgs, links = structure(url, text)
    print("--- body (先頭)\n" + text[:MAXPRINT])
    return imgs, links, text


def dump_dom(chrome, url):
    """Chromeで開いて、JavaScript実行後のHTMLを取り出す（うまくいかない時は別の起動方法も試す）"""
    rc, o, e = -1, b"", b""
    for flags in (["--headless=new", "--virtual-time-budget=8000"], ["--headless", "--virtual-time-budget=8000"]):
        rc, o, e = sh([chrome, *flags, "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
                       "--disable-background-networking", "--disable-component-update", "--disable-sync",
                       "--user-agent=" + BROWSER_UA, "--dump-dom", url], timeout=60)
        if rc == 0 and o:
            return rc, o, e
        print(f"[chrome] 失敗 flags={flags} rc={rc} stderr={e.decode('utf-8', 'replace')[-200:].strip()}")
    return rc, o, e


def main():
    print("### 環境:", os.uname().sysname, os.uname().release)
    all_imgs = []
    for p in ("hnd1.php", "hnd2.php"):
        imgs, _, _ = show_page(p.replace(".php", ""), f"{BASE}/{p}")
        all_imgs += imgs
    # 取り決めの違い（ブラウザらしくない名乗りで）が結果を変えるか
    print("\n### 名乗り（UA）による違いの確認")
    fetch(f"{BASE}/hnd1.php", ua=PLAIN_UA, name="hnd1_plain")
    show_page("robots_ttc", f"{BASE}/robots.txt")

    # 画面を実際に動かした後の中身（JavaScriptで作られる部分を含む）
    chrome = None if os.environ.get("NO_CHROME") else (os.environ.get("CHROME") or shutil.which("google-chrome") or shutil.which("chromium-browser") or shutil.which("chromium"))
    print("\n### Chromeで開いた後の画面の中身:", chrome)
    if chrome:
        for p in ("hnd1.php", "hnd2.php"):
            rc, o, e = dump_dom(chrome, f"{BASE}/{p}")
            text, _ = to_text(o)
            print(f"[chrome] {p} rc={rc} chars={len(text)} stderr={e.decode('utf-8', 'replace')[-200:].strip()}")
            imgs, _ = structure(f"{BASE}/{p}", text)
            all_imgs += imgs
            print("--- DOM (先頭)\n" + text[:MAXPRINT])

    # 写真そのものの性質（大きさ・更新のしかた）。写真の中身は表示しません
    print("\n### 写真の性質")
    seen = []
    for u in all_imgs:
        if u not in seen and not u.startswith("data:"):
            seen.append(u)
    for i, u in enumerate(seen[:6]):
        body, headers = fetch(u, name=f"img{i}")
        keep = [ln for ln in headers.splitlines() if re.match(r"(?i)(HTTP/|content-type|content-length|last-modified|cache-control|expires|etag|age|server|date)", ln)]
        print("  " + "\n  ".join(keep[-12:]))
        if body:
            rc, o, _ = sh(["file", "-b", f"/tmp/img{i}.bin"])
            print("  file:", o.decode("utf-8", "replace").strip()[:200])

    # 公式の案内ページ（利用上の注意・規約の確認用）
    imgs, links, text = show_page("official", OFFICIAL)
    if text:
        print("\n--- 案内ページの本文（文字だけ）\n" + strip_tags(text)[:9000])
        kw = re.compile(r"利用規約|サイトポリシー|サイトのご利用|ご利用にあたって|著作権|免責|プライバシー|個人情報|リンク|policy|terms|copyright|privacy", re.I)
        pol = []
        for h, t in links:
            if (kw.search(t) or kw.search(h)) and "tokyo-tc.or.jp" in h and h not in pol:
                pol.append(h)
        for i, h in enumerate(pol[:3]):
            b, _ = fetch(h, name=f"pol{i}")
            if b:
                print(f"\n--- 規約系ページ {h}\n" + strip_tags(to_text(b)[0])[:6000])
    show_page("robots_official", "https://www.tokyo-tc.or.jp/robots.txt" if OFFICIAL.startswith("https://www.tokyo-tc") else OFFICIAL.rsplit("/", 1)[0] + "/robots.txt")
    print("\n### 完了")


if __name__ == "__main__":
    main()
