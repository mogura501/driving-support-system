"""メイン GUI モジュール

tkinter を使用した 800×480 UI。（PC専用版）
カメラ映像の表示、検知モード制御、校正、カウンターを統合する。
"""

import os
import platform
import threading
import time
import tkinter as tk
from collections import deque
from datetime import datetime
from tkinter import messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

from .alarm import AlarmManager
from .calibration import CalibrationManager, CalibrationPhase
from .camera import Camera
from .config import CalibrationData, Config
from .counter import Counter
from .eye_detector import EyeDetectionResult, EyeDetector

# =====================================================================
# プラットフォーム別フォント
# =====================================================================
_SYSTEM = platform.system()
if _SYSTEM == "Windows":
    _FONT = "Yu Gothic UI"
elif _SYSTEM == "Darwin":
    _FONT = "Hiragino Sans"
else:
    _FONT = "Noto Sans CJK JP"

# =====================================================================
# カラーパレット（ダークテーマ）
# =====================================================================
COLOR_BG = "#1a1a2e"
COLOR_BG_LIGHT = "#16213e"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_DIM = "#888888"
COLOR_ACCENT = "#e94560"
COLOR_BTN = "#0f3460"
COLOR_BTN_HOVER = "#1a5276"
COLOR_GREEN = "#228B22"
COLOR_ORANGE = "#FF8C00"
COLOR_RED = "#CC0000"
COLOR_GRAY = "#555555"
COLOR_SHUTDOWN = "#8B0000"

# ステータスバーの高さ
STATUS_BAR_H = 34
# カメラ表示サイズ
CAM_DISPLAY_W = 420
CAM_DISPLAY_H = 315  # 4:3 比


class DrivingSupportApp:
    """運転サポートシステム メインアプリケーション"""

    def __init__(self, config: Config):
        self.config = config
        self.running = True

        # --- コンポーネント初期化 ---
        self.camera = Camera(config)
        self.alarm = AlarmManager(config)
        self.counter = Counter()
        self.calib_data = CalibrationData(
            config.base_dir,
            config.eye_detection.get("default_ear_threshold", 0.2),
        )
        self.calib_mgr = CalibrationManager(
            countdown_sec=config.calibration.get("countdown_sec", 3),
            measurement_frames=config.calibration.get("measurement_frames", 15),
        )

        # EyeDetector（モデルファイルチェック）
        self.eye_detector = None
        if os.path.exists(config.model_path):
            try:
                self.eye_detector = EyeDetector(config.model_path)
            except Exception as e:
                print(f"[ERROR] EyeDetector 初期化失敗: {e}")

        # --- 状態変数 ---
        self.detecting = False           # 検知モード ON/OFF
        self.eye_closed_since = None     # 閉眼開始時刻
        self.ear_threshold = self.calib_data.threshold
        ear_buf_size = config.eye_detection.get("ear_smoothing_frames", 3)
        self.ear_buffer = deque(maxlen=ear_buf_size)
        self.closed_duration_sec = config.eye_detection.get(
            "closed_duration_threshold_sec", 1.0
        )
        self.latest_result = EyeDetectionResult()

        # FPS 計算
        self._frame_times = deque(maxlen=30)
        self._fps = 0.0

        # カメラスレッド用
        self._lock = threading.Lock()
        self._latest_frame = None
        self._camera_thread = None

        # --- tkinter ルート構築 ---
        self.root = tk.Tk()
        self.root.title("運転サポートシステム")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        win_w = config.ui.get("window_width", 800)
        win_h = config.ui.get("window_height", 480)
        self.root.geometry(f"{win_w}x{win_h}")

        if config.ui.get("fullscreen", False):
            self.root.attributes("-fullscreen", True)

        # ウィンドウ閉じる処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- UI 構築 ---
        self._build_status_bar()
        self._build_main_area()
        self._build_calibration_overlay()

        # --- カメラ起動 ---
        if self.camera.open():
            self._start_camera_thread()
        else:
            print("[WARN] カメラが見つかりません。映像なしで起動します。")

        # --- 定期更新タイマー ---
        self._schedule_ui_update()
        self._schedule_clock_update()

    # =================================================================
    # UI 構築
    # =================================================================
    def _build_status_bar(self):
        """ステータスバーを構築する"""
        self.status_bar = tk.Frame(self.root, bg=COLOR_GRAY, height=STATUS_BAR_H)
        self.status_bar.pack(fill=tk.X, side=tk.TOP)
        self.status_bar.pack_propagate(False)

        # モード表示（左）
        self.lbl_mode = tk.Label(
            self.status_bar, text="● 待機中", font=(_FONT, 13, "bold"),
            bg=COLOR_GRAY, fg=COLOR_TEXT, anchor="w", padx=10,
        )
        self.lbl_mode.pack(side=tk.LEFT)

        # 日時表示（右）
        self.lbl_clock = tk.Label(
            self.status_bar, text="", font=(_FONT, 12),
            bg=COLOR_GRAY, fg=COLOR_TEXT, anchor="e", padx=10,
        )
        self.lbl_clock.pack(side=tk.RIGHT)

        # 目の状態（中央右）
        self.lbl_eye_state = tk.Label(
            self.status_bar, text="👁 ---", font=(_FONT, 12),
            bg=COLOR_GRAY, fg=COLOR_TEXT, padx=10,
        )
        self.lbl_eye_state.pack(side=tk.RIGHT)

        # EAR 値（中央左）
        self.lbl_ear = tk.Label(
            self.status_bar, text="EAR: ---", font=(_FONT, 12),
            bg=COLOR_GRAY, fg=COLOR_TEXT, padx=10,
        )
        self.lbl_ear.pack(side=tk.RIGHT)

    def _build_main_area(self):
        """メインエリア（カメラ + コントロール）を構築する"""
        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill=tk.BOTH, expand=True)

        # ---- 左パネル: カメラ映像 ----
        left = tk.Frame(main, bg=COLOR_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 4), pady=4)

        # カメラ表示ラベル
        self.lbl_camera = tk.Label(left, bg="#000000", width=CAM_DISPLAY_W,
                                   height=CAM_DISPLAY_H)
        self.lbl_camera.pack(pady=(4, 2))
        # 初期画像（黒）
        self._photo_image = None
        self._set_black_frame()

        # 情報バー
        info_frame = tk.Frame(left, bg=COLOR_BG_LIGHT, height=26)
        info_frame.pack(fill=tk.X, pady=(2, 0))
        info_frame.pack_propagate(False)

        self.lbl_face = tk.Label(
            info_frame, text="顔検出: ---", font=(_FONT, 10),
            bg=COLOR_BG_LIGHT, fg=COLOR_TEXT_DIM, padx=8,
        )
        self.lbl_face.pack(side=tk.LEFT)

        self.lbl_fps = tk.Label(
            info_frame, text="FPS: --", font=(_FONT, 10),
            bg=COLOR_BG_LIGHT, fg=COLOR_TEXT_DIM, padx=8,
        )
        self.lbl_fps.pack(side=tk.RIGHT)

        # ---- 右パネル: コントロール ----
        right_width = 310
        right = tk.Frame(main, bg=COLOR_BG, width=right_width)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(4, 8), pady=4)
        right.pack_propagate(False)

        # -- 検知ボタン --
        self.btn_detect = tk.Button(
            right, text="▶  検知開始", font=(_FONT, 16, "bold"),
            bg=COLOR_GREEN, fg=COLOR_TEXT, activebackground="#1B7A1B",
            activeforeground=COLOR_TEXT, relief=tk.FLAT, bd=0,
            height=2, command=self._toggle_detection,
        )
        self.btn_detect.pack(fill=tk.X, pady=(4, 6))

        # -- 校正ボタン --
        self.btn_calib = tk.Button(
            right, text="🎯  校正", font=(_FONT, 13, "bold"),
            bg=COLOR_BTN, fg=COLOR_TEXT, activebackground=COLOR_BTN_HOVER,
            activeforeground=COLOR_TEXT, relief=tk.FLAT, bd=0,
            height=1, command=self._start_calibration,
        )
        self.btn_calib.pack(fill=tk.X, pady=(0, 8))

        # -- カウンター セクション --
        sep = tk.Frame(right, bg=COLOR_TEXT_DIM, height=1)
        sep.pack(fill=tk.X, pady=(0, 6))

        tk.Label(right, text="カウンター", font=(_FONT, 11),
                 bg=COLOR_BG, fg=COLOR_TEXT_DIM).pack()

        self.lbl_counter = tk.Label(
            right, text="0", font=(_FONT, 44, "bold"),
            bg=COLOR_BG_LIGHT, fg=COLOR_ACCENT, relief=tk.FLAT,
            padx=10, pady=2,
        )
        self.lbl_counter.pack(fill=tk.X, pady=(2, 4))

        btn_row = tk.Frame(right, bg=COLOR_BG)
        btn_row.pack(fill=tk.X, pady=(0, 6))

        btn_style = dict(
            font=(_FONT, 16, "bold"), fg=COLOR_TEXT, relief=tk.FLAT,
            bd=0, activeforeground=COLOR_TEXT, height=1, width=5,
        )
        self.btn_plus = tk.Button(
            btn_row, text="＋", bg="#2E86C1", activebackground="#2471A3",
            command=self._counter_plus, **btn_style,
        )
        self.btn_plus.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

        self.btn_minus = tk.Button(
            btn_row, text="−", bg="#2E86C1", activebackground="#2471A3",
            command=self._counter_minus, **btn_style,
        )
        self.btn_minus.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        self.btn_reset = tk.Button(
            btn_row, text="Reset", bg=COLOR_GRAY, activebackground="#444444",
            command=self._counter_reset, **btn_style,
        )
        self.btn_reset.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # -- スペーサー --
        spacer = tk.Frame(right, bg=COLOR_BG)
        spacer.pack(fill=tk.BOTH, expand=True)

        # -- 終了ボタン（最下部） --
        self.btn_quit = tk.Button(
            right, text="⏻  終了", font=(_FONT, 11),
            bg=COLOR_SHUTDOWN, fg="#ffcccc", activebackground="#660000",
            activeforeground=COLOR_TEXT, relief=tk.FLAT, bd=0,
            height=1, command=self._quit_confirm,
        )
        self.btn_quit.pack(fill=tk.X, pady=(6, 2))

    def _build_calibration_overlay(self):
        """校正用のオーバーレイフレーム（非表示で生成）"""
        self.overlay = tk.Frame(self.root, bg="#000000")
        # place で全画面覆う（初期は非表示）

        self.lbl_calib_instruction = tk.Label(
            self.overlay, text="", font=(_FONT, 22, "bold"),
            bg="#000000", fg=COLOR_TEXT,
        )
        self.lbl_calib_instruction.pack(expand=True, pady=(80, 0))

        self.lbl_calib_countdown = tk.Label(
            self.overlay, text="", font=(_FONT, 72, "bold"),
            bg="#000000", fg=COLOR_ORANGE,
        )
        self.lbl_calib_countdown.pack(expand=True)

        self.btn_calib_cancel = tk.Button(
            self.overlay, text="✕  キャンセル", font=(_FONT, 14, "bold"),
            bg=COLOR_GRAY, fg=COLOR_TEXT, activebackground="#444444",
            relief=tk.FLAT, bd=0, padx=20, pady=8,
            command=self._cancel_calibration,
        )
        self.btn_calib_cancel.pack(pady=(0, 40))

    # =================================================================
    # カメラスレッド
    # =================================================================
    def _start_camera_thread(self):
        """バックグラウンドでカメラ映像を取得・処理するスレッドを起動"""
        self._camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._camera_thread.start()

    def _camera_loop(self):
        """カメラ読み取り + MediaPipe 処理のメインループ"""
        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                time.sleep(0.01)
                continue

            # FPS 計算
            now = time.time()
            self._frame_times.append(now)
            if len(self._frame_times) >= 2:
                elapsed = self._frame_times[-1] - self._frame_times[0]
                if elapsed > 0:
                    self._fps = (len(self._frame_times) - 1) / elapsed

            # MediaPipe 処理
            result = EyeDetectionResult()
            if self.eye_detector is not None:
                try:
                    result = self.eye_detector.process_frame(frame)
                except Exception:
                    pass

            # EAR スムージング
            if result.face_detected:
                self.ear_buffer.append(result.ear)
                if self.ear_buffer:
                    result.ear = sum(self.ear_buffer) / len(self.ear_buffer)

            with self._lock:
                self._latest_frame = frame.copy()
                self.latest_result = result

    # =================================================================
    # UI 定期更新
    # =================================================================
    def _schedule_ui_update(self):
        """~30fps で UI を更新するタイマー"""
        if not self.running:
            return
        self._update_display()
        self.root.after(33, self._schedule_ui_update)

    def _schedule_clock_update(self):
        """時計を毎秒更新"""
        if not self.running:
            return
        now = datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y/%m/%d %H:%M:%S"))
        self.root.after(1000, self._schedule_clock_update)

    def _update_display(self):
        """共有状態からカメラ映像と検出結果を読み取り、UIを更新する"""
        with self._lock:
            frame = self._latest_frame
            result = self.latest_result

        if frame is None:
            return

        # --- 映像に描画 ---
        display_frame = frame.copy()

        # 検知モード ON：目の輪郭を緑で描画
        if self.detecting and result.face_detected and self.eye_detector:
            EyeDetector.draw_eye_contours(display_frame, result)

        # フレームをリサイズして表示
        display_frame = cv2.resize(display_frame, (CAM_DISPLAY_W, CAM_DISPLAY_H))
        display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(display_frame)
        self._photo_image = ImageTk.PhotoImage(image=img)
        self.lbl_camera.config(image=self._photo_image)

        # --- ステータスバー更新 ---
        if result.face_detected:
            ear_text = f"EAR: {result.ear:.2f}"
            is_closed = result.ear < self.ear_threshold
            eye_text = "👁 CLOSED" if is_closed else "👁 OPEN"
            face_text = "顔検出: OK"
        else:
            ear_text = "EAR: ---"
            eye_text = "👁 ---"
            face_text = "顔検出: なし"
            is_closed = False

        self.lbl_ear.config(text=ear_text)
        self.lbl_eye_state.config(text=eye_text)
        self.lbl_face.config(text=face_text)

        # FPS 表示
        if self.config.ui.get("show_fps", True):
            self.lbl_fps.config(text=f"FPS: {self._fps:.1f}")

        # --- アラーム判定（検知モード ON のみ） ---
        self._process_alarm(result, is_closed)

        # --- 校正サンプル収集 ---
        if self.calib_mgr.is_active and result.face_detected:
            if self.calib_mgr.phase in (CalibrationPhase.OPEN_MEASURING,
                                         CalibrationPhase.CLOSE_MEASURING):
                self.calib_mgr.add_sample(result.ear)
                self._update_calibration_display()

        # --- ステータスバー色更新 ---
        self._update_status_bar_color(is_closed)

    def _process_alarm(self, result: EyeDetectionResult, is_closed: bool):
        """アラーム鳴動判定"""
        if not self.detecting:
            # 検知モード OFF → アラーム停止してリセット
            if self.alarm.is_alarming:
                self.alarm.stop_alarm()
            self.eye_closed_since = None
            return

        if not result.face_detected:
            self.eye_closed_since = None
            if self.alarm.is_alarming:
                self.alarm.stop_alarm()
            return

        if is_closed:
            if self.eye_closed_since is None:
                self.eye_closed_since = time.time()
            elapsed = time.time() - self.eye_closed_since
            if elapsed >= self.closed_duration_sec:
                self.alarm.start_alarm()
        else:
            self.eye_closed_since = None
            if self.alarm.is_alarming:
                self.alarm.stop_alarm()

    def _update_status_bar_color(self, is_closed: bool):
        """モードに応じてステータスバーの背景色とテキストを更新"""
        if self.calib_mgr.is_active:
            color = COLOR_ORANGE
            mode_text = "● 校正中"
        elif self.detecting:
            if self.alarm.is_alarming:
                color = COLOR_RED
                mode_text = "● ⚠ 警告！"
            else:
                color = COLOR_GREEN
                mode_text = "● 検知中"
        else:
            color = COLOR_GRAY
            mode_text = "● 待機中"

        self.lbl_mode.config(text=mode_text, bg=color)
        for widget in (self.status_bar, self.lbl_ear,
                       self.lbl_eye_state, self.lbl_clock):
            widget.config(bg=color)

    # =================================================================
    # 検知モード操作
    # =================================================================
    def _toggle_detection(self):
        """検知モードの ON/OFF を切り替える"""
        self.detecting = not self.detecting
        if self.detecting:
            self.btn_detect.config(text="■  検知停止", bg=COLOR_RED,
                                   activebackground="#AA0000")
            self.alarm.play_beep()
        else:
            self.btn_detect.config(text="▶  検知開始", bg=COLOR_GREEN,
                                   activebackground="#1B7A1B")
            self.alarm.stop_alarm()
            self.eye_closed_since = None
            self.alarm.play_beep()

    # =================================================================
    # カウンター操作
    # =================================================================
    def _counter_plus(self):
        val = self.counter.increment()
        self.lbl_counter.config(text=str(val))

    def _counter_minus(self):
        val = self.counter.decrement()
        self.lbl_counter.config(text=str(val))

    def _counter_reset(self):
        val = self.counter.reset()
        self.lbl_counter.config(text=str(val))

    # =================================================================
    # 校正操作
    # =================================================================
    def _start_calibration(self):
        """校正を開始する"""
        if self.eye_detector is None:
            messagebox.showwarning("エラー", "MediaPipeモデルが読み込めていません。")
            return

        # 検知モードを一旦 OFF
        if self.detecting:
            self._toggle_detection()

        self.calib_mgr.start()
        self._show_calibration_overlay()
        self._calibration_tick()

    def _cancel_calibration(self):
        """校正をキャンセルする"""
        self.calib_mgr.cancel()
        self._hide_calibration_overlay()

    def _show_calibration_overlay(self):
        """校正オーバーレイを表示"""
        self.overlay.place(x=0, y=STATUS_BAR_H, relwidth=1.0,
                           height=self.root.winfo_height() - STATUS_BAR_H)
        self._update_calibration_display()

    def _hide_calibration_overlay(self):
        """校正オーバーレイを非表示"""
        self.overlay.place_forget()

    def _update_calibration_display(self):
        """オーバーレイの表示を更新"""
        self.lbl_calib_instruction.config(text=self.calib_mgr.instruction_text)
        if self.calib_mgr.is_countdown and self.calib_mgr.countdown > 0:
            self.lbl_calib_countdown.config(text=str(self.calib_mgr.countdown))
        elif self.calib_mgr.phase == CalibrationPhase.COMPLETED:
            result = self.calib_mgr.get_result()
            self.lbl_calib_countdown.config(
                text=f"閾値: {result['threshold']:.3f}"
            )
        else:
            self.lbl_calib_countdown.config(text="...")

    def _calibration_tick(self):
        """校正カウントダウンを1秒ごとに処理"""
        if not self.calib_mgr.is_active:
            return

        if self.calib_mgr.phase == CalibrationPhase.COMPLETED:
            # 完了処理
            result = self.calib_mgr.get_result()
            self.ear_threshold = result["threshold"]
            self.calib_data.save(
                result["open_ear"], result["close_ear"], result["threshold"]
            )
            self._update_calibration_display()
            # 2秒後にオーバーレイを閉じる
            self.root.after(2000, self._finish_calibration)
            return

        should_beep = self.calib_mgr.tick()
        if should_beep:
            self.alarm.play_beep()

        self._update_calibration_display()

        # 次の tick をスケジュール
        if self.calib_mgr.is_active:
            self.root.after(1000, self._calibration_tick)

    def _finish_calibration(self):
        """校正完了後にオーバーレイを閉じる"""
        self.calib_mgr.finish()
        self._hide_calibration_overlay()

    # =================================================================
    # 終了
    # =================================================================
    def _quit_confirm(self):
        """終了確認ダイアログ"""
        answer = messagebox.askyesno(
            "終了",
            "アプリケーションを終了しますか？",
            icon="warning",
        )
        if answer:
            self._cleanup()
            self.root.destroy()

    # =================================================================
    # ユーティリティ
    # =================================================================
    def _set_black_frame(self):
        """カメラ未接続時の黒フレームを表示"""
        black = np.zeros((CAM_DISPLAY_H, CAM_DISPLAY_W, 3), dtype=np.uint8)
        img = Image.fromarray(black)
        self._photo_image = ImageTk.PhotoImage(image=img)
        self.lbl_camera.config(image=self._photo_image)

    def _cleanup(self):
        """全リソースを解放する"""
        self.running = False
        if self._camera_thread and self._camera_thread.is_alive():
            self._camera_thread.join(timeout=2.0)
        self.camera.release()
        if self.eye_detector:
            self.eye_detector.close()
        self.alarm.cleanup()

    def _on_close(self):
        """ウィンドウ閉じるボタンの処理"""
        self._cleanup()
        self.root.destroy()

    # =================================================================
    # メインループ
    # =================================================================
    def run(self):
        """tkinter メインループを開始する"""
        self.root.mainloop()
