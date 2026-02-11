# 🚗 運転サポートシステム — Driving Support System

MediaPipe Face Landmarker を使用した**居眠り検知システム**です。  
カメラ映像からリアルタイムに目の開閉を判定し、**1 秒以上の閉眼でアラームを鳴動**して居眠り運転を防止します。

![Python](https://img.shields.io/badge/Python-3.9--3.12-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 主な機能

| 機能 | 説明 |
|---|---|
| **居眠り検知** | EAR（Eye Aspect Ratio）アルゴリズムで目の開閉を判定。1秒以上閉じるとアラーム |
| **キャリブレーション** | 個人の目の大きさに合わせて閾値を自動調整（開眼→閉眼の2段階測定） |
| **検知モード ON/OFF** | ボタンでアラーム検知の有効/無効を切替。運転中のみ ON にする運用 |
| **カウンター** | +/−/リセット付きカウンター（任意の用途に使用可能） |
| **終了** | アプリケーションを安全に終了 |
| **ステータスバー** | 現在のモード（待機中/検知中/校正中/アラーム）と日時をリアルタイム表示 |
| **目の輪郭表示** | 検知中は緑色のポリラインで両目の輪郭をオーバーレイ描画 |

---

## デモ画面イメージ

```
┌─────────────────────────────── 800×480 ──────────────────────────────────┐
│ ■ 待機中                                           2026/02/10 12:34:56  │  ← ステータスバー
├──────────────────────────────────────────┬────────────────────────────────┤
│                                          │  [🔴 検知開始]                │
│          カメラ映像                       │                              │
│       (目の輪郭を緑で表示)                │  [📐 キャリブレーション]       │
│                                          │                              │
│                                          │  EAR: 0.28  閾値: 0.21       │
│                                          │                              │
│                                          │  カウンター: 0                │
│                                          │  [＋] [−] [Reset]            │
│                                          │                              │
│                                          │  [⏻ 終了]                    │
└──────────────────────────────────────────┴────────────────────────────────┘
```

---

## 動作環境

| 項目 | 要件 |
|---|---|
| OS | Windows 10/11, macOS, Linux |
| Python | 3.9〜3.12 |
| mediapipe | 0.10.9 以上 |
| カメラ | USB Web カメラ / 内蔵カメラ |

---

## セットアップ

### Windows

```powershell
# 1. 仮想環境の作成
cd "driving suport system"
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. パッケージのインストール
pip install -r requirements.txt

# 3. 起動（初回はモデルファイルのダウンロード確認あり）
python main.py
```

### macOS / Linux

```bash
cd "driving suport system"
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

python main.py
```

> **💡 GitHub にアップロードする際の注意**  
> 以下のファイル/フォルダは `.gitignore` で除外されます（サイズが大きい or 環境依存）：
> - `venv/` — 仮想環境
> - `models/` — MediaPipe モデル（初回起動時に自動ダウンロード）
> - `sounds/` — 音声ファイル（初回起動時に自動生成）
> - `__pycache__/`
> - `calibration_data.json` — 個人のキャリブレーションデータ

---

## プロジェクト構成

```
driving suport system/
├── main.py                  # エントリーポイント
├── config.json              # 設定ファイル
├── requirements.txt         # パッケージ一覧
├── 要件定義書.md              # 要件仕様書
├── README.md                # このファイル
├── .gitignore               # Git 除外設定
├── models/
│   └── face_landmarker.task # MediaPipe モデル (初回起動時にDL)
├── sounds/
│   ├── alarm.wav            # アラーム音 (自動生成)
│   └── beep.wav             # ビープ音 (自動生成)
└── src/
    ├── __init__.py
    ├── config.py            # 設定管理
    ├── camera.py            # カメラ制御 (Windows DSHOW / その他デフォルト)
    ├── eye_detector.py      # MediaPipe 目検出・EAR 算出
    ├── calibration.py       # キャリブレーション状態管理
    ├── alarm.py             # アラーム・ビープ音再生
    ├── counter.py           # カウンター
    ├── sound_generator.py   # サウンドファイル自動生成
    └── gui.py               # tkinter メイン GUI
```

---

## 設定ファイル

### config.json

| 設定 | 値 | 説明 |
|---|---|---|
| camera.device_id | 0 | カメラデバイス番号 |
| camera.width | 640 | キャプチャ幅 |
| camera.height | 480 | キャプチャ高さ |
| camera.fps | 30 | フレームレート |
| eye_detection.default_ear_threshold | 0.2 | デフォルト EAR 閾値 |
| eye_detection.closed_duration_threshold_sec | 1.0 | アラーム発動までの閉眼秒数 |
| ui.fullscreen | false | フルスクリーンモード |
| ui.window_width | 800 | ウィンドウ幅 |
| ui.window_height | 480 | ウィンドウ高さ |

```bash
# 設定ファイルを明示的に指定して起動
python main.py --config config.json
```

---

## 技術詳細

### EAR（Eye Aspect Ratio）アルゴリズム

MediaPipe の 478 点フェイスメッシュから目周辺の 6 点を取得し、  
縦横比で目の開閉度を算出します。

```
       p2
      / \
p1 ─      ─ p4
      \ /
       p3
        p5
       p6

EAR = (||p2 - p6|| + ||p3 - p5||) / (2 × ||p1 - p4||)
```

- **開眼時**: EAR ≈ 0.25〜0.35
- **閉眼時**: EAR ≈ 0.05〜0.15
- **閾値**: キャリブレーションで (開眼平均 + 閉眼平均) / 2 を自動算出

### 使用ランドマークインデックス

| 目 | p1 | p2 | p3 | p4 | p5 | p6 |
|---|---|---|---|---|---|---|
| 左目 | 33 | 159 | 145 | 133 | 153 | 144 |
| 右目 | 263 | 386 | 374 | 362 | 380 | 373 |

### プラットフォーム別のカメラバックエンド

| プラットフォーム | バックエンド | 補足 |
|---|---|---|
| Windows | `cv2.CAP_DSHOW` | DirectShow でハング回避 |
| macOS / Linux | `cv2.VideoCapture()` デフォルト | |

---

## トラブルシューティング

### カメラが認識されない

- `config.json` の `device_id` を 0, 1, 2 ... と変更して試す
- 他のアプリがカメラを使用していないか確認する

### アラームが鳴らない

```bash
# pygame の音声バックエンドを確認
python -c "import pygame; pygame.mixer.init(); print('OK')"
```

### mediapipe インストール失敗

```bash
# Python バージョン確認（3.9〜3.12 が必要）
python --version

# 最新版をインストール
pip install mediapipe --upgrade
```

---

## ライセンス

MIT License

## 謝辞

- [MediaPipe](https://github.com/google-ai-edge/mediapipe) — Google AI Edge
- [EAR アルゴリズム参考](https://zenn.dev/ykesamaru/articles/f10804a8fcc81d)
