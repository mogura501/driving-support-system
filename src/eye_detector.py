"""目検出モジュール

MediaPipe Face Landmarker (Tasks API) を使用して
顔のランドマークを検出し、EAR (Eye Aspect Ratio) を算出する。
"""

import cv2
import numpy as np

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# =====================================================================
# Eye Aspect Ratio (EAR) 用ランドマークインデックス
# 参考: https://zenn.dev/ykesamaru/articles/f10804a8fcc81d
# =====================================================================
LEFT_EYE_EAR = {"p1": 33, "p2": 159, "p3": 145, "p4": 133, "p5": 153, "p6": 144}
RIGHT_EYE_EAR = {"p1": 263, "p2": 386, "p3": 374, "p4": 362, "p5": 380, "p6": 373}

# 目の輪郭描画用インデックス（閉じた多角形として描画）
LEFT_EYE_OUTLINE = [
    33, 246, 161, 160, 159, 158, 157, 173,   # 上まぶた
    133, 155, 154, 153, 145, 144, 163, 7,     # 下まぶた
]
RIGHT_EYE_OUTLINE = [
    263, 466, 388, 387, 386, 385, 384, 398,   # 上まぶた
    362, 382, 381, 380, 374, 373, 390, 249,   # 下まぶた
]


class EyeDetectionResult:
    """1フレーム分の目検出結果"""

    __slots__ = (
        "face_detected", "ear", "left_ear", "right_ear",
        "left_contour", "right_contour",
    )

    def __init__(self):
        self.face_detected: bool = False
        self.ear: float = 0.0
        self.left_ear: float = 0.0
        self.right_ear: float = 0.0
        self.left_contour: list = []   # [(x, y), ...]
        self.right_contour: list = []


class EyeDetector:
    """MediaPipe Face Landmarker を使った目検出器"""

    def __init__(self, model_path: str):
        if not MEDIAPIPE_AVAILABLE:
            raise RuntimeError(
                "mediapipe がインストールされていません。\n"
                "  pip install mediapipe\n"
                "で導入してください。"
            )

        # 日本語パス対策: ファイルをバイト列として読み込み model_asset_buffer に渡す
        with open(model_path, "rb") as f:
            model_data = f.read()

        BaseOptions = mp.tasks.BaseOptions
        FaceLandmarker = mp.tasks.vision.FaceLandmarker
        FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=model_data),
            running_mode=VisionRunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = FaceLandmarker.create_from_options(options)
        self._timestamp_ms = 0

    # -----------------------------------------------------------------
    # 公開メソッド
    # -----------------------------------------------------------------
    def process_frame(self, frame: np.ndarray) -> EyeDetectionResult:
        """BGR フレームを受け取り、目の検出結果を返す"""
        result = EyeDetectionResult()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        self._timestamp_ms += 33  # 単調増加を保証
        detection = self._landmarker.detect_for_video(mp_image, self._timestamp_ms)

        if not detection.face_landmarks:
            return result

        landmarks = detection.face_landmarks[0]
        h, w = frame.shape[:2]

        # EAR 算出
        result.left_ear = self._compute_ear(landmarks, LEFT_EYE_EAR, w, h)
        result.right_ear = self._compute_ear(landmarks, RIGHT_EYE_EAR, w, h)
        result.ear = (result.left_ear + result.right_ear) / 2.0
        result.face_detected = True

        # 描画用の輪郭座標
        result.left_contour = self._get_contour(landmarks, LEFT_EYE_OUTLINE, w, h)
        result.right_contour = self._get_contour(landmarks, RIGHT_EYE_OUTLINE, w, h)

        return result

    def close(self):
        """リソースを解放する"""
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None

    # -----------------------------------------------------------------
    # 描画ヘルパー
    # -----------------------------------------------------------------
    @staticmethod
    def draw_eye_contours(frame: np.ndarray, result: EyeDetectionResult,
                          color=(0, 255, 0), thickness=2):
        """フレーム上に目の輪郭を緑色で描画する"""
        if not result.face_detected:
            return frame
        for contour in (result.left_contour, result.right_contour):
            if contour:
                pts = np.array(contour, dtype=np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], isClosed=True,
                              color=color, thickness=thickness)
        return frame

    # -----------------------------------------------------------------
    # 内部メソッド
    # -----------------------------------------------------------------
    @staticmethod
    def _compute_ear(landmarks, eye_idx: dict, w: int, h: int) -> float:
        """EAR (Eye Aspect Ratio) を計算する"""
        def pt(idx):
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        p1 = pt(eye_idx["p1"])
        p2 = pt(eye_idx["p2"])
        p3 = pt(eye_idx["p3"])
        p4 = pt(eye_idx["p4"])
        p5 = pt(eye_idx["p5"])
        p6 = pt(eye_idx["p6"])

        vert1 = np.linalg.norm(p2 - p6)
        vert2 = np.linalg.norm(p3 - p5)
        horiz = np.linalg.norm(p1 - p4)

        if horiz < 1e-6:
            return 0.0

        return (vert1 + vert2) / (2.0 * horiz)

    @staticmethod
    def _get_contour(landmarks, indices: list, w: int, h: int) -> list:
        """ランドマークからピクセル座標のリストを生成する"""
        points = []
        for idx in indices:
            lm = landmarks[idx]
            points.append((int(lm.x * w), int(lm.y * h)))
        return points
