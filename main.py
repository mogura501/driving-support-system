#!/usr/bin/env python3
"""運転サポートシステム - エントリーポイント

PC 専用の居眠り検知システム。
MediaPipe Face Landmarker を使用して目の開閉を判定し、
1秒以上の閉眼でアラームを鳴動する。
"""

import os
import sys
import argparse
import urllib.request

# プロジェクトルートを特定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from src.config import Config
from src.sound_generator import ensure_sounds


def check_dependencies():
    """必要なライブラリがインストールされているか確認する"""
    missing = []
    for module in ("cv2", "numpy", "pygame", "PIL"):
        try:
            __import__(module)
        except ImportError:
            if module == "PIL":
                missing.append("Pillow")
            elif module == "cv2":
                missing.append("opencv-python")
            else:
                missing.append(module)

    try:
        import mediapipe
    except ImportError:
        missing.append("mediapipe")

    if missing:
        print("=" * 50)
        print("[ERROR] 以下のライブラリが不足しています:")
        for m in missing:
            print(f"  - {m}")
        print()
        print("以下のコマンドでインストールしてください:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 50)
        return False
    return True


def ensure_model(config: Config):
    """MediaPipe モデルファイルが存在しなければダウンロードする"""
    model_path = config.model_path
    model_dir = os.path.dirname(model_path)
    os.makedirs(model_dir, exist_ok=True)

    if os.path.exists(model_path):
        return True

    print("=" * 50)
    print("[INFO] MediaPipe モデルファイルが見つかりません。")
    print(f"  パス: {model_path}")
    print()

    url = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
    )

    try:
        answer = input("自動ダウンロードしますか？ [Y/n]: ").strip().lower()
        if answer in ("", "y", "yes"):
            print(f"ダウンロード中... ({url})")
            urllib.request.urlretrieve(url, model_path, _download_progress)
            print("\nダウンロード完了！")
            return True
        else:
            print("手動で以下の URL からダウンロードし、")
            print(f"  {model_dir}/ に配置してください。")
            print(f"  URL: {url}")
            return False
    except Exception as e:
        print(f"[ERROR] ダウンロード失敗: {e}")
        print("手動でモデルファイルをダウンロードしてください。")
        print(f"  URL: {url}")
        print(f"  保存先: {model_path}")
        return False


def _download_progress(block_num, block_size, total_size):
    """ダウンロード進捗表示"""
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100, downloaded * 100 // total_size)
        bar = "#" * (percent // 2) + "-" * (50 - percent // 2)
        sys.stdout.write(f"\r  [{bar}] {percent}%")
        sys.stdout.flush()


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(description="運転サポートシステム")
    parser.add_argument(
        "--config", type=str, default=None,
        help="使用する設定ファイル名 (例: config.json)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  運転サポートシステム")
    print("  Driving Support System")
    print("=" * 50)

    # 1. 依存チェック
    if not check_dependencies():
        sys.exit(1)

    # 2. 設定読み込み
    config = Config(BASE_DIR, config_file=args.config)
    platform_name = config.get_platform()
    print(f"[INFO] プラットフォーム: {platform_name}")

    # 3. サウンドファイル生成（なければ）
    ensure_sounds(BASE_DIR)

    # 4. モデルファイルチェック
    if not ensure_model(config):
        print("[WARN] モデルなしで起動します（目検出機能は無効）。")

    # 5. GUI 起動
    from src.gui import DrivingSupportApp
    print("[INFO] アプリケーションを起動中...")
    app = DrivingSupportApp(config)
    app.run()

    print("[INFO] アプリケーションを終了しました。")


if __name__ == "__main__":
    main()
