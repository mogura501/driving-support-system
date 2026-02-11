"""設定管理モジュール

config.json の読み込みを担当する。（PC専用版）
"""

import json
import os
import platform


class Config:
    """アプリケーション設定を管理するクラス"""

    def __init__(self, base_dir: str, config_file: str = None):
        self.base_dir = base_dir

        # 設定ファイルの選択
        if config_file:
            config_path = os.path.join(base_dir, config_file)
        else:
            config_path = os.path.join(base_dir, "config.json")

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            print(f"[INFO] 設定ファイル: {os.path.basename(config_path)}")
        else:
            self._data = {}
            print("[WARN] 設定ファイルが見つかりません。デフォルト値を使用します。")

        # 各セクションをプロパティとして展開
        self.camera = self._data.get("camera", {
            "device_id": 0, "width": 640, "height": 480, "fps": 30
        })
        self.eye_detection = self._data.get("eye_detection", {
            "default_ear_threshold": 0.2,
            "closed_duration_threshold_sec": 1.0,
            "ear_smoothing_frames": 3,
        })
        self.calibration = self._data.get("calibration", {
            "countdown_sec": 3, "measurement_frames": 15
        })
        self.alarm = self._data.get("alarm", {
            "sound_file": "sounds/alarm.wav",
            "beep_file": "sounds/beep.wav",
            "volume": 0.8,
        })
        self.ui = self._data.get("ui", {
            "fullscreen": False, "window_width": 800,
            "window_height": 480, "show_fps": True,
        })

    # --- パス解決ユーティリティ ---
    def resolve_path(self, relative: str) -> str:
        """base_dir 基準で相対パスを解決する"""
        return os.path.join(self.base_dir, relative)

    @property
    def model_path(self) -> str:
        return os.path.normpath(self.resolve_path("models/face_landmarker.task"))

    @staticmethod
    def get_platform() -> str:
        """プラットフォーム文字列を返す"""
        return platform.system().lower()  # 'windows', 'darwin', 'linux'


class CalibrationData:
    """校正データの保存・読み込みを管理するクラス"""

    def __init__(self, base_dir: str, default_threshold: float = 0.2):
        self.path = os.path.join(base_dir, "calibration_data.json")
        self.threshold = default_threshold
        self.open_ear = 0.0
        self.close_ear = 0.0
        self.calibrated = False
        self._load()

    def _load(self):
        """ファイルから校正データを読み込む"""
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.threshold = data.get("threshold", self.threshold)
                self.open_ear = data.get("open_ear", 0.0)
                self.close_ear = data.get("close_ear", 0.0)
                self.calibrated = data.get("calibrated", False)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save(self, open_ear: float, close_ear: float, threshold: float):
        """校正データを保存する"""
        self.open_ear = open_ear
        self.close_ear = close_ear
        self.threshold = threshold
        self.calibrated = True
        data = {
            "threshold": self.threshold,
            "open_ear": self.open_ear,
            "close_ear": self.close_ear,
            "calibrated": self.calibrated,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
