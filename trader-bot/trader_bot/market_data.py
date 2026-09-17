"""Market data sources.

`MarketDataSource` is the interface the bot depends on. Two
implementations are provided:

- `SimulatedMarketData`: a synthetic random-walk price feed. Needs no
  Windows, no DLL, no broker account. Use this to validate the strategy
  and risk logic end-to-end before touching real infrastructure.
- `ProfitDLLMarketData` (in profit_dll_gateway.py): wraps the real
  ProfitDLL trade callback. Windows-only.
"""

from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Callable

from trader_bot.strategy import Bar

OnBar = Callable[[Bar], None]


class MarketDataSource(ABC):
    @abstractmethod
    def subscribe(self, ticker: str, on_bar: OnBar) -> None:
        """Start streaming bars for `ticker`, invoking `on_bar` for each."""

    @abstractmethod
    def stop(self) -> None:
        ...


class SimulatedMarketData(MarketDataSource):
    """Generates a synthetic price series via a bounded random walk.

    Deterministic when given a `seed`, which makes bot behavior
    reproducible in tests and dry runs.
    """

    def __init__(
        self,
        start_price: float = 130000.0,
        tick_size: float = 5.0,
        interval_seconds: float = 1.0,
        seed: int | None = None,
    ):
        self.price = start_price
        self.tick_size = tick_size
        self.interval_seconds = interval_seconds
        self._rng = random.Random(seed)
        self._running = False

    def subscribe(self, ticker: str, on_bar: OnBar) -> None:
        self._running = True
        while self._running:
            step = self._rng.choice([-1, 1]) * self.tick_size
            self.price = max(self.tick_size, self.price + step)
            on_bar(Bar(timestamp=time.time(), price=self.price))
            time.sleep(self.interval_seconds)

    def stop(self) -> None:
        self._running = False
