"""カウンター機能モジュール"""


class Counter:
    """プラス・マイナス・リセットが出来る汎用カウンター"""

    def __init__(self, initial: int = 0):
        self._value = initial

    @property
    def value(self) -> int:
        return self._value

    def increment(self) -> int:
        self._value += 1
        return self._value

    def decrement(self) -> int:
        self._value -= 1
        return self._value

    def reset(self) -> int:
        self._value = 0
        return self._value
