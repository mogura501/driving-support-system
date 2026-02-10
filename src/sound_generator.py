"""サウンド生成ユーティリティ

sounds/ フォルダに alarm.wav / beep.wav が存在しない場合に
Python 標準ライブラリだけで簡易的な WAV ファイルを生成する。
"""

import math
import os
import struct
import wave


def _generate_wav(filepath: str, frequency: float, duration: float,
                  volume: float = 0.5, sample_rate: int = 44100,
                  modulate: bool = False):
    """正弦波 WAV ファイルを生成する"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    n_samples = int(sample_rate * duration)

    with wave.open(filepath, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(n_samples):
            t = i / sample_rate
            if modulate:
                # アラーム用: 2つの周波数を交互に切り替え
                freq = frequency if (t % 0.5) < 0.25 else frequency * 0.75
            else:
                freq = frequency
            value = int(volume * 32767 * math.sin(2 * math.pi * freq * t))
            value = max(-32767, min(32767, value))
            wav.writeframes(struct.pack("<h", value))


def ensure_sounds(base_dir: str):
    """sounds/ 配下にサウンドファイルが無ければ生成する"""
    sounds_dir = os.path.join(base_dir, "sounds")
    os.makedirs(sounds_dir, exist_ok=True)

    alarm_path = os.path.join(sounds_dir, "alarm.wav")
    beep_path = os.path.join(sounds_dir, "beep.wav")

    if not os.path.exists(beep_path):
        print("[INFO] beep.wav を生成中...")
        _generate_wav(beep_path, frequency=1000, duration=0.15, volume=0.5)

    if not os.path.exists(alarm_path):
        print("[INFO] alarm.wav を生成中...")
        _generate_wav(alarm_path, frequency=880, duration=2.0,
                      volume=0.7, modulate=True)
