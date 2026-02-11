"""カメラ制御モジュール

OpenCV VideoCapture のラッパー。
カメラの初期化・フレーム取得・解放を担当する。（PC専用版）
"""

import platform
import threading

import cv2


class Camera:
    """OpenCV カメラキャプチャのラッパークラス"""

    def __init__(self, config):
        self.device_id = config.camera.get("device_id", 0)
        self.width = config.camera.get("width", 640)
        self.height = config.camera.get("height", 480)
        self.fps = config.camera.get("fps", 30)
        self.cap = None

    def open(self, timeout_sec: float = 8.0) -> bool:
        """カメラを開く。成功したら True を返す。
        プラットフォーム毎に最適なバックエンドを選択し、タイムアウトを設ける。
        """
        result = [False]

        def _try_open():
            if platform.system() == "Windows":
                # Windows: DirectShow バックエンドでハング回避
                self.cap = cv2.VideoCapture(self.device_id, cv2.CAP_DSHOW)
            else:
                self.cap = cv2.VideoCapture(self.device_id)
            result[0] = self.cap is not None and self.cap.isOpened()

        t = threading.Thread(target=_try_open, daemon=True)
        t.start()
        t.join(timeout=timeout_sec)

        if t.is_alive():
            print("[WARN] カメラのオープンがタイムアウトしました。")
            self.cap = None
            return False

        if not result[0]:
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 実際に取得できた解像度を表示
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(f"[INFO] カメラ: {actual_w}x{actual_h} @ {actual_fps:.0f}fps")
        return True

    def read(self):
        """フレームを1枚取得する。(success, frame) を返す"""
        if self.cap is None or not self.cap.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        """カメラリソースを解放する"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @property
    def is_opened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()
