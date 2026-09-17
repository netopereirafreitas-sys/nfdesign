"""Trading strategy logic, decoupled from any broker or data source.

Pure functions/classes here so they can be unit tested without Windows,
without the ProfitDLL, and without a real or simulated broker connection.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    HOLD = "HOLD"
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Bar:
    """One aggregated price observation (e.g. last trade or candle close)."""

    timestamp: float
    price: float


class MovingAverageCrossoverStrategy:
    """Classic fast/slow simple-moving-average crossover.

    Emits BUY when the fast MA crosses above the slow MA, SELL when it
    crosses below, HOLD otherwise. Only reacts to crossovers (not the
    ongoing state) so it won't repeat the same signal every tick.
    """

    def __init__(self, fast_period: int, slow_period: int):
        if fast_period <= 0 or slow_period <= 0:
            raise ValueError("periods must be positive")
        if fast_period >= slow_period:
            raise ValueError("fast_period must be smaller than slow_period")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self._prices: deque[float] = deque(maxlen=slow_period)
        self._prev_fast_above_slow: bool | None = None

    def _sma(self, period: int) -> float:
        window = list(self._prices)[-period:]
        return sum(window) / len(window)

    def on_bar(self, bar: Bar) -> Signal:
        self._prices.append(bar.price)

        if len(self._prices) < self.slow_period:
            return Signal.HOLD

        fast_ma = self._sma(self.fast_period)
        slow_ma = self._sma(self.slow_period)
        fast_above_slow = fast_ma > slow_ma

        signal = Signal.HOLD
        if self._prev_fast_above_slow is not None:
            if fast_above_slow and not self._prev_fast_above_slow:
                signal = Signal.BUY
            elif not fast_above_slow and self._prev_fast_above_slow:
                signal = Signal.SELL

        self._prev_fast_above_slow = fast_above_slow
        return signal
