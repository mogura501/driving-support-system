"""校正（キャリブレーション）モジュール

開眼時・閉眼時の EAR を測定し、最適な閾値を自動算出する。
状態遷移は GUI 側のタイマーで駆動する。
"""

from enum import Enum, auto


class CalibrationPhase(Enum):
    """校正の各フェーズ"""
    IDLE = auto()                 # 待機中
    OPEN_COUNTDOWN = auto()       # 「目を開けてください」カウントダウン
    OPEN_MEASURING = auto()       # 開眼 EAR 測定中
    CLOSE_COUNTDOWN = auto()      # 「目を閉じてください」カウントダウン
    CLOSE_MEASURING = auto()      # 閉眼 EAR 測定中
    COMPLETED = auto()            # 校正完了


class CalibrationManager:
    """校正処理の状態管理クラス

    使い方:
        1. start() で校正開始
        2. GUI 側のタイマーで tick() を毎秒呼ぶ（カウントダウン用）
        3. フレームごとに add_sample(ear) を呼ぶ
        4. phase が COMPLETED になったら get_result() で結果取得
    """

    def __init__(self, countdown_sec: int = 3, measurement_frames: int = 15):
        self.countdown_sec = countdown_sec
        self.measurement_frames = measurement_frames

        self.phase = CalibrationPhase.IDLE
        self.countdown = 0
        self._open_samples: list[float] = []
        self._close_samples: list[float] = []
        self._result_threshold: float = 0.0

    # -----------------------------------------------------------------
    # 公開メソッド
    # -----------------------------------------------------------------
    def start(self):
        """校正を開始する"""
        self.phase = CalibrationPhase.OPEN_COUNTDOWN
        self.countdown = self.countdown_sec
        self._open_samples.clear()
        self._close_samples.clear()
        self._result_threshold = 0.0

    def cancel(self):
        """校正をキャンセルする"""
        self.phase = CalibrationPhase.IDLE

    def tick(self) -> bool:
        """1秒ごとに呼ばれるカウントダウン処理。
        ビープ音を鳴らすべきなら True を返す。
        """
        if self.phase in (CalibrationPhase.OPEN_COUNTDOWN,
                          CalibrationPhase.CLOSE_COUNTDOWN):
            self.countdown -= 1
            if self.countdown <= 0:
                # カウントダウン終了 → 測定フェーズへ
                if self.phase == CalibrationPhase.OPEN_COUNTDOWN:
                    self.phase = CalibrationPhase.OPEN_MEASURING
                else:
                    self.phase = CalibrationPhase.CLOSE_MEASURING
            return True  # ビープ音を鳴らす
        return False

    def add_sample(self, ear: float):
        """EAR サンプルを追加する（フレームごとに呼ぶ）"""
        if self.phase == CalibrationPhase.OPEN_MEASURING:
            self._open_samples.append(ear)
            if len(self._open_samples) >= self.measurement_frames:
                # 開眼測定完了 → 閉眼カウントダウンへ
                self.phase = CalibrationPhase.CLOSE_COUNTDOWN
                self.countdown = self.countdown_sec

        elif self.phase == CalibrationPhase.CLOSE_MEASURING:
            self._close_samples.append(ear)
            if len(self._close_samples) >= self.measurement_frames:
                # 閉眼測定完了 → 閾値算出
                self._calculate_threshold()
                self.phase = CalibrationPhase.COMPLETED

    def get_result(self) -> dict:
        """校正結果を返す"""
        open_avg = (sum(self._open_samples) / len(self._open_samples)
                    if self._open_samples else 0.0)
        close_avg = (sum(self._close_samples) / len(self._close_samples)
                     if self._close_samples else 0.0)
        return {
            "threshold": self._result_threshold,
            "open_ear": open_avg,
            "close_ear": close_avg,
        }

    def finish(self):
        """完了表示後に IDLE に戻す"""
        self.phase = CalibrationPhase.IDLE

    # -----------------------------------------------------------------
    # 表示用プロパティ
    # -----------------------------------------------------------------
    @property
    def instruction_text(self) -> str:
        """現在のフェーズに対応する指示テキスト"""
        if self.phase == CalibrationPhase.OPEN_COUNTDOWN:
            return "目を開けてください"
        elif self.phase == CalibrationPhase.OPEN_MEASURING:
            return "測定中... (目を開けたまま)"
        elif self.phase == CalibrationPhase.CLOSE_COUNTDOWN:
            return "目を閉じてください"
        elif self.phase == CalibrationPhase.CLOSE_MEASURING:
            return "測定中... (目を閉じたまま)"
        elif self.phase == CalibrationPhase.COMPLETED:
            return "校正完了！"
        return ""

    @property
    def is_active(self) -> bool:
        return self.phase != CalibrationPhase.IDLE

    @property
    def is_countdown(self) -> bool:
        return self.phase in (CalibrationPhase.OPEN_COUNTDOWN,
                              CalibrationPhase.CLOSE_COUNTDOWN)

    # -----------------------------------------------------------------
    # 内部メソッド
    # -----------------------------------------------------------------
    def _calculate_threshold(self):
        """開眼・閉眼の EAR 中間値を閾値として算出"""
        open_avg = sum(self._open_samples) / len(self._open_samples)
        close_avg = sum(self._close_samples) / len(self._close_samples)
        self._result_threshold = (open_avg + close_avg) / 2.0
