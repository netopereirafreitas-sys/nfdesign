"""Loads bot configuration from environment variables (.env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _get_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


@dataclass
class Settings:
    mode: str  # "simulated" or "real"
    ticker: str
    ma_fast: int
    ma_slow: int
    order_qty: int
    max_position: int
    max_daily_loss: float
    stop_loss_points: float
    take_profit_points: float
    max_consecutive_losses: int

    # ProfitDLL / XP credentials, only required when mode == "real"
    profit_dll_path: str
    profit_activation_key: str
    profit_login: str
    profit_password: str


def load_settings() -> Settings:
    mode = os.getenv("MODE", "simulated").lower()
    if mode not in ("simulated", "real"):
        raise ValueError('MODE must be "simulated" or "real"')

    return Settings(
        mode=mode,
        ticker=os.getenv("TICKER", "WINFUT"),
        ma_fast=_get_int("MA_FAST", 9),
        ma_slow=_get_int("MA_SLOW", 21),
        order_qty=_get_int("ORDER_QTY", 1),
        max_position=_get_int("MAX_POSITION", 1),
        max_daily_loss=_get_float("MAX_DAILY_LOSS", -500.0),
        stop_loss_points=_get_float("STOP_LOSS_POINTS", 500.0),
        take_profit_points=_get_float("TAKE_PROFIT_POINTS", 1000.0),
        max_consecutive_losses=_get_int("MAX_CONSECUTIVE_LOSSES", 3),
        profit_dll_path=os.getenv("PROFIT_DLL_PATH", "ProfitDLL64.dll"),
        profit_activation_key=os.getenv("PROFIT_ACTIVATION_KEY", ""),
        profit_login=os.getenv("PROFIT_LOGIN", ""),
        profit_password=os.getenv("PROFIT_PASSWORD", ""),
    )
