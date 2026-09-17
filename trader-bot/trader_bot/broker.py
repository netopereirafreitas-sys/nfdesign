"""Broker execution gateway.

`BrokerGateway` is the interface the bot depends on. `SimulatedBroker`
fills orders instantly at the requested price and tracks nothing beyond
a fill log — real P&L accounting lives in RiskManager. The real
ProfitDLL-backed gateway lives in profit_dll_gateway.py (Windows-only).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("trader_bot.broker")


@dataclass
class Fill:
    side: str
    quantity: int
    price: float


class BrokerGateway(ABC):
    @abstractmethod
    def send_order(self, ticker: str, side: str, quantity: int, price: float) -> Fill:
        """Send a market order. Returns the resulting fill.

        `price` is used as a reference/limit price; simulated fills use
        it directly. Real implementations should use it for logging and
        slippage checks, not assume an exact fill price.
        """


class SimulatedBroker(BrokerGateway):
    def __init__(self):
        self.fills: list[Fill] = []

    def send_order(self, ticker: str, side: str, quantity: int, price: float) -> Fill:
        fill = Fill(side=side, quantity=quantity, price=price)
        self.fills.append(fill)
        logger.info("[SIMULATED FILL] %s %d %s @ %.2f", side, quantity, ticker, price)
        return fill
