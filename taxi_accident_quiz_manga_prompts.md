# マンガ用 画像生成プロンプト集（タクシー事故クイズ動画）

対象：`taxi_accident_quiz_scenario.md` の6問＋オープニング／クロージング。
画像生成AI（Midjourney / DALL·E / Stable Diffusion / Firefly など）にそのまま貼れる英語プロンプトと、日本語の意図メモを並べています。

## 使い方のコツ

1. 最初に「共通スタイル」と「キャラクターシート」を毎回プロンプトの先頭に貼る（画風と主人公の顔を揃えるため）。
2. 画像内に文字は入れない。文字化けするので、吹き出し・テロップ・正解の文言は動画編集側で後から載せる。
3. 比率は 16:9（Midjourney なら `--ar 16:9`）。動画の下端に字幕が入るので、**重要な被写体は画面の上〜中央に置く**よう指定済み。
4. 日本の道路は**左側通行・右ハンドル**。生成結果で逆（左ハンドル／右側通行）になったら、`right-hand-drive, left-hand traffic` を強調して再生成するか、画像を左右反転せず再生成する（反転すると標識や文字が崩れるため）。
5. 各問題は「問題用（事故の直前）」と「答え用（同じ構図で危険を強調）」の2枚セット。**同じシード／同じ構図指定**で作ると、動画で切り替えたときに見比べやすい。
6. 実在のタクシー会社や車種のロゴ・ナンバーは入れない。

---

## 共通スタイル（STYLE）

```
Japanese manga illustration, clean black ink linework, flat cel-shaded colors with light screentone shading, slightly semi-realistic proportions, expressive but restrained, warm daylight palette, high readability, cinematic 16:9 composition, no text, no letters, no logos, no watermark
```

## ネガティブプロンプト（NEGATIVE）

```
text, letters, captions, speech bubbles, watermark, logo, brand name, readable license plate, gore, blood, injury, crash in progress, distorted hands, extra fingers, left-hand-drive car, right-side traffic, western street signs
```

> 事故の瞬間・流血・衝突は描かない方針です。動画は「事故になる**直前**」を見せるクイズで、再現映像ではないため。

## キャラクターシート（CHARACTER）

**ゲンさん（主人公）**

```
Gen-san: 60-year-old Japanese male taxi driver, kind but sharp eyes, short neat grey hair under a navy blue taxi driver cap with a small gold badge, thick grey mustache, light wrinkles around the eyes, navy uniform jacket, white shirt, thin red necktie, white driving gloves, calm and observant expression
```

**タクシー（愛車）**

```
Japanese taxi: compact yellow sedan with a small white roof lamp, right-hand-drive, clean and well maintained, generic design with no brand logo, no readable text
```

表情バリエーション（ゲンさんに足す）

| 用途 | 追記する英語 |
|---|---|
| 通常運転 | `calm focused expression` |
| 危険に気づいた | `eyes wide, sharp alert expression, slight sweat drop` |
| 解説・語り | `gentle teaching smile, slightly raised eyebrow` |
| 反省・真剣 | `serious grave expression, eyes lowered` |
| ラスト決め | `proud quiet smile, looking at camera` |

---

## オープニング（OP）

### OP-1　車庫の朝
```
[STYLE] [CHARACTER Gen-san] Early morning taxi garage, Gen-san standing beside his yellow taxi, resting one gloved hand on the hood, a framed certificate for "20 years without accident" hanging on the wall behind him (no readable text, just a decorative frame with gold border), soft sunrise light through the garage door, calm proud mood, medium shot, subject centered in the upper two thirds of the frame
```
意図：「事故は“いつもの一回”で起きる」のナレーション用。

### OP-2　ハンドルを握る手
```
[STYLE] Close-up of a gloved hand gripping a taxi steering wheel (right-hand-drive interior), meter display glowing softly, city street blurred through the windshield, morning light, sense of routine and responsibility, shallow depth of field
```

### OP-3　タイトル用（背景のみ）
```
[STYLE] Dynamic manga speed-line background in warm yellow and white radiating from the center, Gen-san in the lower left giving a confident smile, small yellow taxi at the lower right, large empty space in the center for title text, no text
```

---

## 第1問　左折　＜歩行者を見送ったあと、左から自転車＞

根拠：歩行者に気を取られ右を見て発進し、左側の自転車に気づかなかった事例（運輸局資料）。

### Q1-問題用
```
[STYLE] [CHARACTER Gen-san] Driver's-eye view from the right-hand-drive seat, a Japanese city intersection at noon with a green traffic light, about to turn left. The last pedestrian has just finished crossing the crosswalk in front. On the far right, an oncoming car waiting. Gen-san's hands on the wheel at the bottom of the frame. In the LEFT door mirror, a small bicycle with a cyclist is just visible (subtle, easy to overlook). Natural bright light, realistic Japanese street details, no text
```

### Q1-答え用
```
[STYLE] Same intersection and same composition as the question image, but the left door mirror reflection is enlarged and highlighted with a soft glowing red outline: a cyclist riding straight along the left side of the car, entering the crosswalk. A faint translucent cone shows the blind spot at the rear-left of the taxi. The driver's head is turned slightly to the left toward the mirror. Clear educational diagram feeling, no text
```

### Q1-ゲンさんカット
```
[STYLE] [CHARACTER Gen-san] Close-up of Gen-san glancing at the left door mirror with an alert look, hand on the steering wheel, gentle teaching smile fading into focus, warm light
```

---

## 第2問　右折　＜譲られたトラックの陰のバイク＞

根拠：道を譲られて対向車線を確認せず右折／歩行者信号に気を取られ対向直進の二輪車に気づかなかった事例（運輸局資料）。

### Q2-問題用
```
[STYLE] [CHARACTER Gen-san] Driver's-eye view from a right-hand-drive taxi waiting in the middle of a big Japanese intersection at dusk, about to turn right. An oncoming large white delivery truck has stopped and is flashing its headlights to let the taxi go. Beyond the truck's side, the lane is hidden from view. On the far crosswalk a pedestrian is waiting. Evening orange light, tense but quiet mood, no motorcycle visible yet, no text
```

### Q2-答え用
```
[STYLE] Same composition, but a semi-transparent "x-ray" effect reveals a motorcycle with a rider hidden behind the stopped truck, speeding straight ahead in the next lane. The hidden area behind the truck is shaded by a translucent purple overlay to show the blind spot. Gen-san's eyes in the rear-view mirror area are looking carefully to the right. Educational manga diagram feeling, no text
```

### Q2-ゲンさんカット
```
[STYLE] [CHARACTER Gen-san] Gen-san holding his foot on the brake with an alert, slightly sweaty expression, looking past the truck, dusk light on his face
```

---

## 第3問　乗客の降車　＜ドアを開ける直前の後方の自転車＞

根拠：開いたドアに自転車が衝突する事故の報道、JAF「ダッチリーチ」。

### Q3-問題用
```
[STYLE] [CHARACTER Gen-san] Night street in a Japanese city, the yellow taxi stopped at the left curb after arrival. Interior view from the front seat looking toward the rear-view mirror: in the mirror, a cyclist's front light is approaching from behind in the dark. In the rear seat, a passenger (a woman in a coat, face not shown) is putting her hand on the door handle. Warm cabin light, cold blue night outside, no text
```

### Q3-答え用
```
[STYLE] Exterior high-angle view from behind the taxi: the rear-left door is shown about to open, with a translucent red arc on the ground showing the door's swing area, and a cyclist riding in a thin lane between the taxi and the curb, approaching the red arc. Gen-san's hand is raised toward the passenger in a "please wait" gesture visible through the window. Night city, no collision, no text
```

### Q3-解説カット（ダッチリーチ）
```
[STYLE] Clean instructional manga panel: a driver reaching across his body to open the door with the far hand (the "Dutch reach"), which naturally turns his upper body toward the rear window, so he can look behind. Arrows are not needed; show body twist clearly. Side-cutaway of the car interior, no text
```

---

## 第4問　乗車後の転回　＜ハザード点灯のままUターン＞

根拠：ハザードを点灯したまま転回し、後方の原付と衝突した事例（関東運輸局 2015年事例）。

### Q4-問題用
```
[STYLE] [CHARACTER Gen-san] A lively Japanese entertainment district at night with neon lights, the yellow taxi stopped at the left edge of the road with its orange hazard lights on, a passenger just seated in the back. Interior view from the driver's seat: in the rear-view mirror a scooter's headlight is approaching. On the opposite side of the road, a person is raising a hand to hail a taxi. Gen-san's finger is on the turn signal, about to U-turn. Neon reflections on wet pavement, no text
```

### Q4-答え用
```
[STYLE] Same composition, but a translucent white arrow curves across the road showing the planned U-turn path, and a translucent red band shows the scooter's straight path crossing it. The scooter is brightly highlighted in the rear-view mirror. A small thought-bubble-like empty cloud above the driver suggests "assuming the other will yield", with a faint red cross over it (no text). Educational manga feeling
```

### Q4-ゲンさんカット
```
[STYLE] [CHARACTER Gen-san] Gen-san looking into the rear-view mirror, then deliberately lifting his hand off the turn signal and shaking his head slightly, calm firm expression, neon light on his face
```

---

## 第5問　雨の夜　＜停車車両の陰からの歩行者＞

根拠：夜間の横断歩行者との死亡事故の増加（国交省・運輸局の注意喚起）、停車車両の陰から横断してきた歩行者の発見遅れ。

### Q5-問題用
```
[STYLE] [CHARACTER Gen-san] Driver's-eye view from a right-hand-drive taxi at night in light rain, on a two-lane Japanese road with a large white van stopped in the left lane with its hazard lights blinking. Wet asphalt reflecting streetlights, windshield wipers mid-sweep, dashboard speedometer glowing at about 40 km/h. No pedestrian visible. Moody blue and amber palette, no text
```

### Q5-答え用
```
[STYLE] Same composition, but a translucent x-ray effect reveals a pedestrian in dark clothing with a clear umbrella, hidden behind the stopped van and stepping out into the road. The shadow area behind the van is shaded in translucent purple. The taxi's headlight beam is shown as a soft cone. Rain streaks visible, no collision, no text
```

### Q5-ゲンさんカット
```
[STYLE] [CHARACTER Gen-san] Gen-san's eyes under the cap brim reflecting the red and amber lights on a rainy night, one foot easing off the accelerator, serious grave expression
```

---

## 第6問　信号のない交差点　＜見通しの悪い十字路の出会い頭＞

根拠：ハイタクの事故類型で出会い頭が最多（2012年統計 23.0％）。通り慣れた交差点で一時停止を軽視しがち。

### Q6-問題用
```
[STYLE] [CHARACTER Gen-san] Driver's-eye view from a right-hand-drive taxi approaching a narrow residential crossroads in Japan, late morning. A red inverted-triangle stop sign with no readable text and a faded white stop line. High concrete block walls and hedges on both corners block the view of the side road. Quiet suburban atmosphere, bright sunlight, no vehicles or people visible, no text
```

### Q6-答え用
```
[STYLE] Same composition, but a translucent x-ray effect through the block wall reveals a person riding a bicycle toward the crossroads from the right side road, hidden by the wall. A translucent purple shape marks the blind spot. A bright white stop line is emphasized in the road in front of the taxi. Educational manga feeling, no collision, no text
```

### Q6-ゲンさんカット
```
[STYLE] [CHARACTER Gen-san] Gen-san leaning slightly forward at the stop line, turning his head to look carefully left and right, calm vigilant expression, sunlight through the windshield
```

---

## クロージング（ED）

### ED-1　夕暮れの車庫
```
[STYLE] [CHARACTER Gen-san] Dusk at the taxi garage, Gen-san stepping out of the yellow taxi at the end of his shift, gently patting the hood with a gloved hand, golden-hour light, quiet proud smile, long soft shadows, medium shot, subject in the upper two thirds
```

### ED-2　ラストカット
```
[STYLE] [CHARACTER Gen-san] Gen-san turned toward the camera, looking straight at the viewer with a warm confident smile, the yellow taxi's headlights glowing behind him in the evening, bokeh city lights, empty space on the right for the end card, no text
```

---

## 枚数まとめ

| 区分 | 枚数 |
|---|---|
| オープニング | 3 |
| 第1〜第6問（各 問題・答え・ゲンさん） | 18（＋Q3の解説1） |
| クロージング | 2 |
| **合計** | **24枚** |

## 動画への組み込み順（案）

各問題：`Qn-問題用`（状況説明＋3秒カウント）→ `Qn-答え用`（正解発表）→ `Qn-ゲンさんカット`（ゲンさんの一言）。
文字（問題番号、正解テロップ、字幕）は、動画編集側で `taxi_accident_quiz_scenario.md` の文言を載せてください。
