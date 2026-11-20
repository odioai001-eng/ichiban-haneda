# 記録ツールの使い方（かんたん手順）

羽田空港タクシー乗り場のライブカメラの写真を、1分ごとに記録するツールです。**日本国内の回線につながった、つけっぱなしのパソコン**で動かします（海外のサーバーからは、カメラのサイトに届きません）。

## 用意するもの

- つけっぱなしにできるパソコン（Windows または Mac）。**スリープしない設定**にしてください。
- Python（無料）。パソコンに入っているか確認するには、コマンドプロンプト（Macは「ターミナル」）で `python --version` と入力します。バージョンが出れば入っています（3.8以上）。`python` で動かないときは `py`（Windows）や `python3`（Mac）で試してください。

## 手順（Windows）

1. **Pythonを入れる**（入っていなければ）: https://www.python.org/downloads/ → 「Download Python」→ ダウンロードしたものを開く → **「Add python.exe to PATH」にチェックを入れて**から「Install Now」。
2. **2つのファイルを、同じフォルダに保存する**（例: デスクトップに `haneda` フォルダを作る）。GitHubの次の2つのページを開き、右上のダウンロードのアイコンで保存します。
   - `.claude/skills/haneda-stand-monitor/scripts/capture.py`
   - `.claude/skills/haneda-stand-monitor/scripts/selftest.py`
3. **コマンドプロンプトを開いて、そのフォルダに移る**: `cd Desktop\haneda`
4. **道具が動くか確かめる**: `python selftest.py` → 最後に「すべて合格」と出ればOKです（インターネットには出ません）。
5. **本物のサイトで、1回だけ確かめる**: `python capture.py --diagnose` → 出てきた内容を、**そのままClaudeに貼り付けてください**（写真は貼らなくて大丈夫です）。ここで読み取りがずれていれば、Claudeが直します。
6. **記録を始める**: `python capture.py` → 1分ごとに記録します。**このウィンドウは閉じないでください**。止めるときは `Ctrl` + `C`。

## どこに保存される？

`C:\Users\（あなたの名前）\haneda-stand-data` の中です。

- `captures.csv` … 記録の一覧（Excelで開けます。開いたままでも大丈夫です。書けない間はためておいて、あとでまとめて書きます）
- `images\日付\…` … 写真
- 古い写真（30日より前）は自動で消えます。CSVは消えません。

## 注意

- パソコンがスリープすると、記録が止まります。電源の設定で「スリープしない」にしてください。
- 海外向けのVPNは切ってください（国内の回線でないと、サイトに届きません）。
- 写真は、**個人的な分析のためだけ**に使ってください。人に配る・ネットに載せる・GitHubに入れることはしないでください（東京タクシーセンターの著作権の決まりのためです）。チームと共有するのは、数（台数など）だけにします。
- 空き容量: 写真は1日に数百MBほどになります（2ページ・4カメラの場合）。

## Mac・Linux・Raspberry Pi

- `python3 selftest.py` → `python3 capture.py --diagnose` → `python3 capture.py` の順です。
- 画面を閉じても動かし続けるには: `nohup python3 capture.py > capture.log 2>&1 &`
- 再起動したときに自動で始めたい場合は、Claudeに頼んでください。
