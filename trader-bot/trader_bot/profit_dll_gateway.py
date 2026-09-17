"""Windows-only gateway to the real market via Nelogica's ProfitDLL.

*** READ THIS BEFORE USING ***

ProfitDLL's exact exported function names, parameter order and struct
layouts differ between DLL versions (32/64-bit builds, and revisions
released over the years). This module implements the shape of the API
as documented in Nelogica's "Manual ProfitDLL" and mirrored by several
open-source community wrappers, but it is NOT guaranteed to match the
exact .dll file you receive from XP/Nelogica. Before running this
against a real account:

  1. Get the "Manual ProfitDLL" PDF that matches your DLL's version
     (ask XP/Nelogica support, or check the DLL's file properties).
  2. Compare every `WINFUNCTYPE` signature and struct below against
     that manual. Fix any mismatch — a wrong signature can silently
     corrupt the call stack or send an unintended order.
  3. Test exhaustively against Nelogica's simulator account (ambiente
     de simulação) — a real demo environment with live-ish data but no
     real money — before ever pointing this at a real account.
  4. Only import/run this module on Windows, with the matching
     ProfitDLL64.dll placed next to this project and the Profit Pro
     terminal installed (the DLL talks to Nelogica's infrastructure
     using your XP login).

This module intentionally does NOT run at import time on non-Windows
platforms so the rest of the bot (strategy, risk manager, simulated
mode) stays testable anywhere.
"""

from __future__ import annotations

import ctypes
import logging
import platform
import time
from ctypes import wintypes
from typing import Callable

from trader_bot.broker import BrokerGateway, Fill
from trader_bot.market_data import MarketDataSource, OnBar
from trader_bot.strategy import Bar

logger = logging.getLogger("trader_bot.profit_dll")

if platform.system() != "Windows":
    raise ImportError(
        "profit_dll_gateway can only be imported on Windows, where the "
        "ProfitDLL and the Profit Pro terminal are available. Use "
        "trader_bot.market_data.SimulatedMarketData and "
        "trader_bot.broker.SimulatedBroker on other platforms."
    )


# --- Callback signatures -----------------------------------------------
# TODO(verify): confirm against your Manual ProfitDLL. These mirror the
# commonly documented v4/v5 signatures (ticker, exchange, price, qty,
# ... , buy/sell aggressor flag) but field order/count varies by version.

TStateCallback = ctypes.WINFUNCTYPE(None, ctypes.c_int, ctypes.c_int)

TNewTradeCallback = ctypes.WINFUNCTYPE(
    None,
    wintypes.LPCWSTR,  # ticker
    wintypes.LPCWSTR,  # exchange
    ctypes.c_double,  # price
    ctypes.c_int,  # quantity
    ctypes.c_longlong,  # trade id / timestamp, depends on version
    ctypes.c_int,  # buy/sell aggressor flag
)

TOrderChangeCallback = ctypes.WINFUNCTYPE(
    None,
    wintypes.LPCWSTR,  # ticker
    ctypes.c_int,  # order id
    ctypes.c_int,  # status
    ctypes.c_double,  # filled price
    ctypes.c_int,  # filled quantity
)


class ProfitDLLClient:
    """Thin ctypes wrapper. Owns the DLL handle and callback lifetimes.

    Kept separate from MarketDataSource/BrokerGateway so both can share
    a single DLL connection (the DLL does not support multiple logins).
    """

    def __init__(self, dll_path: str, activation_key: str, login: str, password: str):
        self.dll = ctypes.WinDLL(dll_path)
        self.activation_key = activation_key
        self.login = login
        self.password = password
        self._connected = False

        # Keep references so ctypes doesn't garbage-collect the callback
        # trampolines while the DLL still holds function pointers to them.
        self._state_cb = TStateCallback(self._on_state)
        self._trade_cb = TNewTradeCallback(self._on_trade)
        self._order_cb = TOrderChangeCallback(self._on_order_change)

        self._bar_subscribers: dict[str, list[OnBar]] = {}
        self._fill_waiters: dict[int, Callable[[Fill], None]] = {}

        # TODO(verify): exact exported name and argument order.
        # Commonly: DLLInitializeLogin(activation_key, login, password,
        #   state_callback, ..., trade_callback, ..., order_callback, ...)
        self.dll.DLLInitializeLogin.restype = ctypes.c_int
        self.dll.SubscribeTicker.restype = ctypes.c_int
        self.dll.SendBuyOrder.restype = ctypes.c_int
        self.dll.SendSellOrder.restype = ctypes.c_int

    def connect(self, timeout_seconds: float = 15.0) -> None:
        result = self.dll.DLLInitializeLogin(
            ctypes.c_wchar_p(self.activation_key),
            ctypes.c_wchar_p(self.login),
            ctypes.c_wchar_p(self.password),
            self._state_cb,
            self._trade_cb,
            self._order_cb,
        )
        if result != 0:
            raise RuntimeError(f"DLLInitializeLogin failed with code {result}")

        deadline = time.time() + timeout_seconds
        while not self._connected and time.time() < deadline:
            time.sleep(0.2)
        if not self._connected:
            raise TimeoutError("ProfitDLL did not report a connected state in time")

    def _on_state(self, state_type: int, state_value: int) -> None:
        logger.info("ProfitDLL state callback: type=%s value=%s", state_type, state_value)
        # TODO(verify): the specific (type, value) pair meaning "logged in
        # and market-data connected" per your manual. 0/0 is a common
        # placeholder in sample code, not a verified constant.
        if state_type == 0 and state_value == 0:
            self._connected = True

    def _on_trade(
        self,
        ticker: str,
        exchange: str,
        price: float,
        quantity: int,
        trade_id: int,
        aggressor: int,
    ) -> None:
        bar = Bar(timestamp=time.time(), price=price)
        for callback in self._bar_subscribers.get(ticker, []):
            callback(bar)

    def _on_order_change(
        self, ticker: str, order_id: int, status: int, filled_price: float, filled_qty: int
    ) -> None:
        waiter = self._fill_waiters.pop(order_id, None)
        if waiter is not None:
            waiter(Fill(side="", quantity=filled_qty, price=filled_price))

    def subscribe_ticker(self, ticker: str, on_bar: OnBar) -> None:
        self._bar_subscribers.setdefault(ticker, []).append(on_bar)
        result = self.dll.SubscribeTicker(ctypes.c_wchar_p(ticker))
        if result != 0:
            raise RuntimeError(f"SubscribeTicker({ticker}) failed with code {result}")

    def send_order(self, ticker: str, side: str, quantity: int, price: float) -> Fill:
        fn = self.dll.SendBuyOrder if side == "BUY" else self.dll.SendSellOrder
        order_id = fn(ctypes.c_wchar_p(ticker), ctypes.c_int(quantity), ctypes.c_double(price))
        if order_id < 0:
            raise RuntimeError(f"{side} order for {ticker} rejected, code {order_id}")

        result: dict[str, Fill] = {}

        def waiter(fill: Fill) -> None:
            result["fill"] = fill

        self._fill_waiters[order_id] = waiter

        deadline = time.time() + 10.0
        while "fill" not in result and time.time() < deadline:
            time.sleep(0.1)

        if "fill" not in result:
            raise TimeoutError(f"Order {order_id} for {ticker} was not confirmed in time")

        fill = result["fill"]
        fill.side = side
        return fill

    def disconnect(self) -> None:
        if hasattr(self.dll, "DLLFinalize"):
            self.dll.DLLFinalize()


class ProfitDLLMarketData(MarketDataSource):
    def __init__(self, client: ProfitDLLClient):
        self.client = client

    def subscribe(self, ticker: str, on_bar: OnBar) -> None:
        self.client.subscribe_ticker(ticker, on_bar)

    def stop(self) -> None:
        self.client.disconnect()


class ProfitDLLBroker(BrokerGateway):
    def __init__(self, client: ProfitDLLClient):
        self.client = client

    def send_order(self, ticker: str, side: str, quantity: int, price: float) -> Fill:
        return self.client.send_order(ticker, side, quantity, price)
