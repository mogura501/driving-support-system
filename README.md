# 🚗 運転サポートシステム — Driving Support System

MediaPipe Face Landmarker を使用した**居眠り検知システム**です。  
カメラ映像からリアルタイムに目の開閉を判定し、**1 秒以上の閉眼でアラームを鳴動**して居眠り運転を防止します。

![Python](https://img.shields.io/badge/Python-3.9--3.12-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Raspberry%20Pi-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 主な機能

| 機能 | 説明 |
|---|---|
| **居眠り検知** | EAR（Eye Aspect Ratio）アルゴリズムで目の開閉を判定。1秒以上閉じるとアラーム |
| **キャリブレーション** | 個人の目の大きさに合わせて閾値を自動調整（開眼→閉眼の2段階測定） |
| **検知モード ON/OFF** | ボタンでアラーム検知の有効/無効を切替。運転中のみ ON にする運用 |
| **カウンター** | +/−/リセット付きカウンター（任意の用途に使用可能） |
| **シャットダウン** | PC ではアプリ終了、Raspberry Pi では `sudo shutdown` を実行 |
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
│                                          │  [⏻ シャットダウン]           │
└──────────────────────────────────────────┴────────────────────────────────┘
```

---

## 動作環境

### PC（開発・テスト用）

| 項目 | 要件 |
|---|---|
| OS | Windows 10/11, macOS, Linux |
| Python | 3.9〜3.12 |
| mediapipe | **0.10.9 以上** （PC では最新版が使用可能） |
| カメラ | USB Web カメラ |

### Raspberry Pi（本番運用）

| 項目 | 要件 |
|---|---|
| ハードウェア | **Raspberry Pi 4 (4 GB 以上推奨)** |
| OS | **Raspberry Pi OS 64-bit (Bookworm)** |
| Python | 3.9〜3.12（Bookworm 標準は 3.11） |
| mediapipe | **⚠️ 0.10.18 固定**（後述） |
| カメラ | USB Web カメラ推奨（Logicool C270 等） |
| ディスプレイ | 7 インチタッチモニタ 800×480 |

---

## ⚠️ mediapipe Raspberry Pi 版の注意事項

**PyPI 上の mediapipe は 0.10.18 が aarch64 (ARM64) wheel を提供する最終バージョンです。**

| バージョン | aarch64 wheel | 備考 |
|---|---|---|
| 0.10.9 〜 0.10.18 | ✅ あり | Python 3.9〜3.12 対応 |
| 0.10.20 以降 | ❌ なし | x86_64 のみ。Pi にインストール不可 |

Google 公式ドキュメントでは「Raspberry OS 64-bit サポート」と記載されていますが、  
実際のパッケージ配布は 0.10.18 で止まっています（2026年2月現在）。

本プロジェクトで使用している API（`FaceLandmarker`, `detect_for_video`, `model_asset_buffer`）は  
0.10.9 で導入済みの安定 API のため、**0.10.18 でも全機能が動作します**。

Raspberry Pi 向けには `requirements_raspi.txt` と `setup_raspi.sh` で  
`mediapipe==0.10.18` に固定しています。

---

## セットアップ

### PC（Windows）

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

### Raspberry Pi

```bash
# 1. GitHub からクローン
git clone https://github.com/mogura501/driving-support-system.git
cd driving-support-system

# 2. セットアップスクリプトを実行（全自動）
chmod +x setup_raspi.sh
./setup_raspi.sh

# 3. 起動
source venv/bin/activate
python main.py
```

> **💡 GitHub にアップロードする際の注意**  
> 以下のファイル/フォルダは `.gitignore` で除外してください（サイズが大きい or 環境依存）：
> - `venv/` — 仮想環境（Pi 側で `setup_raspi.sh` が作り直します）
> - `models/` — MediaPipe モデル（初回起動時 or `setup_raspi.sh` で自動ダウンロード）
> - `sounds/` — 音声ファイル（初回起動時に自動生成）
> - `__pycache__/`
> - `calibration_data.json` — 個人のキャリブレーションデータ

`setup_raspi.sh` が自動で行うこと：

1. システムパッケージ更新・必要パッケージのインストール
2. Python 仮想環境の作成（`--system-site-packages` で apt の OpenCV を共有）
3. `mediapipe==0.10.18` + その他パッケージのインストール
4. MediaPipe モデルファイル（`face_landmarker.task`）のダウンロード
5. **自動起動用の `.desktop` エントリを作成**（再起動でアプリが自動起動）

自動起動を無効にする場合：
```bash
rm ~/.config/autostart/driving-support.desktop
```

---

## プロジェクト構成

```
driving suport system/
├── main.py                  # エントリーポイント
├── config.json              # PC 用設定
├── config_raspi.json        # Raspberry Pi 用設定
├── requirements.txt         # PC 用パッケージ一覧
├── requirements_raspi.txt   # Pi 用パッケージ一覧 (mediapipe==0.10.18)
├── setup_raspi.sh           # Pi セットアップスクリプト
├── 要件定義書.md              # 要件仕様書
├── README.md                # このファイル
├── models/
│   └── face_landmarker.task # MediaPipe モデル (初回起動時にDL)
├── sounds/
│   ├── alarm.wav            # アラーム音 (自動生成)
│   └── beep.wav             # ビープ音 (自動生成)
└── src/
    ├── __init__.py
    ├── config.py            # 設定管理・プラットフォーム判定
    ├── camera.py            # カメラ制御 (Windows DSHOW / Pi V4L2)
    ├── eye_detector.py      # MediaPipe 目検出・EAR 算出
    ├── calibration.py       # キャリブレーション状態管理
    ├── alarm.py             # アラーム・ビープ音再生
    ├── counter.py           # カウンター
    ├── sound_generator.py   # サウンドファイル自動生成
    └── gui.py               # tkinter メイン GUI
```

---

## 設定ファイル

プラットフォームに応じて自動選択されます（`--config` で明示的に指定も可能）。

```bash
python main.py                          # 自動: PC→config.json / Pi→config_raspi.json
python main.py --config config.json     # 明示的に PC 用設定を使用
```

### config.json（PC 用）

| 設定 | 値 | 説明 |
|---|---|---|
| camera.fps | 30 | フレームレート |
| ui.fullscreen | false | ウィンドウモード |
| calibration.measurement_frames | 15 | キャリブレーション測定フレーム数 |

### config_raspi.json（Pi 用）

| 設定 | 値 | 説明 |
|---|---|---|
| camera.fps | **15** | CPU 負荷軽減 |
| ui.fullscreen | **true** | 7 インチモニタ全画面 |
| calibration.measurement_frames | **10** | 測定時間短縮 |

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
| Raspberry Pi | `cv2.CAP_V4L2` → `cv2.CAP_ANY` | V4L2 を優先、失敗時フォールバック |
| その他 Linux/macOS | `cv2.VideoCapture()` デフォルト | |

---

## トラブルシューティング

### カメラが認識されない

```bash
# Linux/Pi: カメラデバイスの確認
ls /dev/video*
# → /dev/video0 が存在すれば OK

# config.json の device_id を変更して試す
```

### mediapipe インストール失敗（Raspberry Pi）

```bash
# Python バージョン確認（3.9〜3.12 が必要）
python3 --version

# 明示的にバージョン固定
pip install mediapipe==0.10.18
```

### 日本語フォントが表示されない（Raspberry Pi）

```bash
sudo apt install fonts-noto-cjk
```

### アラームが鳴らない

```bash
# pygame の音声バックエンドを確認
python -c "import pygame; pygame.mixer.init(); print('OK')"

# SDL2 がインストールされているか
sudo apt install libsdl2-mixer-2.0-0
```

### Pi Camera Module を使いたい場合

USB カメラが推奨ですが、Pi Camera Module を使う場合は `libcamera` の V4L2 互換レイヤーが必要です。

```bash
# V4L2 互換モードでカメラを有効化
sudo modprobe bcm2835-v4l2
# または /boot/config.txt に以下を追記:
# start_x=1
# gpu_mem=128
```

---

## ライセンス

MIT License

## 謝辞

- [MediaPipe](https://github.com/google-ai-edge/mediapipe) — Google AI Edge
- [EAR アルゴリズム参考](https://zenn.dev/ykesamaru/articles/f10804a8fcc81d)
