#!/bin/bash
# =====================================================
# 運転サポートシステム - Raspberry Pi セットアップスクリプト
# Raspberry Pi OS 64bit (Bookworm) 対応
# =====================================================

set -e

echo "========================================"
echo "  運転サポートシステム セットアップ"
echo "  Raspberry Pi 4 用"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# --- 1. システムパッケージ更新 ---
echo "[1/7] システムパッケージを更新中..."
sudo apt update && sudo apt upgrade -y

# --- 2. 必要なシステムパッケージ ---
echo "[2/7] 必要なシステムパッケージをインストール中..."
sudo apt install -y \
    python3-venv \
    python3-pip \
    python3-dev \
    python3-tk \
    python3-numpy \
    python3-opencv \
    libatlas-base-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    fonts-noto-cjk \
    libsdl2-mixer-2.0-0 \
    libsdl2-2.0-0 \
    libcamera-dev \
    libcap-dev \
    wget

# --- 3. Python 仮想環境作成 ---
echo "[3/7] Python 仮想環境を作成中..."

if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
    echo "  仮想環境を作成しました: venv/"
else
    echo "  仮想環境は既に存在します: venv/"
fi

source venv/bin/activate
pip install --upgrade pip setuptools wheel

# --- 4. Python パッケージインストール ---
echo "[4/7] Python パッケージをインストール中..."

# OpenCV — apt のシステムパッケージを使用 (--system-site-packages で共有)
sudo apt install -y python3-opencv 2>/dev/null || true
if python3 -c "import cv2" 2>/dev/null; then
    echo "  opencv はシステムパッケージを使用します"
else
    echo "  opencv-python-headless を pip でインストール中..."
    pip install opencv-python-headless
fi

# numpy
pip install "numpy>=1.24.0"
# Pillow
pip install "Pillow>=10.0.0"
# pygame
pip install "pygame>=2.5.0"

# MediaPipe — aarch64 wheel が提供されている最新版を固定
# 注意: 0.10.20 以降は aarch64 wheel が無いため Pi では使えない
echo "  mediapipe をインストール中 (0.10.18, aarch64対応最終版)..."
if ! pip install "mediapipe==0.10.18" 2>/dev/null; then
    echo ""
    echo "[WARN] pip install mediapipe==0.10.18 が失敗しました。"
    echo "  Python バージョンを確認してください (3.9〜3.12 が必要)。"
    echo "  python3 --version"
    echo ""
fi

# --- 5. MediaPipe モデルダウンロード ---
echo "[5/7] MediaPipe モデルファイルを確認中..."
MODEL_DIR="$SCRIPT_DIR/models"
MODEL_FILE="$MODEL_DIR/face_landmarker.task"
mkdir -p "$MODEL_DIR"

if [ ! -f "$MODEL_FILE" ]; then
    echo "  モデルファイルをダウンロード中..."
    wget -q --show-progress -O "$MODEL_FILE" \
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
    echo "  ダウンロード完了: $MODEL_FILE"
else
    echo "  モデルファイルは既に存在します。"
fi

# --- 6. サウンドディレクトリ準備 ---
echo "[6/7] サウンドディレクトリを準備中..."
mkdir -p "$SCRIPT_DIR/sounds"

# --- 7. 自動起動スクリプト ---
echo "[7/7] 自動起動用デスクトップエントリを作成中..."

DESKTOP_DIR="$HOME/.config/autostart"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/driving-support.desktop" << EOF
[Desktop Entry]
Type=Application
Name=DrivingSupportSystem
Comment=居眠り検知 運転サポートシステム
Exec=bash -c 'cd $SCRIPT_DIR && source venv/bin/activate && python main.py'
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "  自動起動エントリを作成しました。"

# --- 完了 ---
echo ""
echo "========================================"
echo "  セットアップ完了！"
echo ""
echo "  起動方法:"
echo "    cd $SCRIPT_DIR"
echo "    source venv/bin/activate"
echo "    python main.py"
echo ""
echo "  再起動すると自動的にアプリが起動します。"
echo "  自動起動を無効にするには:"
echo "    rm $DESKTOP_DIR/driving-support.desktop"
echo "========================================"
