"""アラーム・サウンド制御モジュール

pygame.mixer を使用してアラーム音・ビープ音を再生する。
"""

import os
import pygame


class AlarmManager:
    """アラーム音・ビープ音の再生を管理するクラス"""

    def __init__(self, config):
        # pygame mixer 初期化
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
        except pygame.error:
            pygame.mixer.init()

        self._alarm_sound = None
        self._beep_sound = None
        self.is_alarming = False

        base_dir = config.base_dir
        volume = config.alarm.get("volume", 0.8)

        # サウンドファイル読み込み
        alarm_path = config.resolve_path(config.alarm.get("sound_file", "sounds/alarm.wav"))
        beep_path = config.resolve_path(config.alarm.get("beep_file", "sounds/beep.wav"))

        if os.path.exists(alarm_path):
            self._alarm_sound = pygame.mixer.Sound(alarm_path)
            self._alarm_sound.set_volume(volume)
        else:
            print(f"[WARN] アラーム音ファイルが見つかりません: {alarm_path}")

        if os.path.exists(beep_path):
            self._beep_sound = pygame.mixer.Sound(beep_path)
            self._beep_sound.set_volume(volume)
        else:
            print(f"[WARN] ビープ音ファイルが見つかりません: {beep_path}")

    def start_alarm(self):
        """アラーム音をループ再生する"""
        if not self.is_alarming and self._alarm_sound:
            self._alarm_sound.play(loops=-1)
            self.is_alarming = True

    def stop_alarm(self):
        """アラーム音を停止する"""
        if self.is_alarming and self._alarm_sound:
            self._alarm_sound.stop()
        self.is_alarming = False

    def play_beep(self):
        """ビープ音を1回再生する（カウントダウン等に使用）"""
        if self._beep_sound:
            self._beep_sound.play()

    def set_volume(self, volume: float):
        """音量を設定（0.0 〜 1.0）"""
        volume = max(0.0, min(1.0, volume))
        if self._alarm_sound:
            self._alarm_sound.set_volume(volume)
        if self._beep_sound:
            self._beep_sound.set_volume(volume)

    def cleanup(self):
        """リソース解放"""
        self.stop_alarm()
        pygame.mixer.quit()
