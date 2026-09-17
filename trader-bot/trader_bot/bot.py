"""Main orchestrator: wires market data -> strategy -> risk -> broker.

Run with `python -m trader_bot.bot`. Defaults to simulated mode; real
mode requires MODE=real in .env plus valid ProfitDLL/XP credentials and
must run on Windows. See README.md before ever using real mode.
"""

from __future__ import annotations

import logging
import sys

from trader_bot.broker import BrokerGateway, SimulatedBroker
from trader_bot.config import Settings, load_settings
from trader_bot.market_data import MarketDataSource, SimulatedMarketData
from trader_bot.risk_manager import RiskLimits, RiskManager, TradingHaltedError
from trader_bot.strategy import Bar, MovingAverageCrossoverStrategy, Signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("trader_bot.bot")


def build_data_source_and_broker(settings: Settings) -> tuple[MarketDataSource, BrokerGateway]:
    if settings.mode == "simulated":
        return SimulatedMarketData(), SimulatedBroker()

    # Imported lazily: this module raises ImportError on non-Windows
    # platforms, and requires the real ProfitDLL64.dll to be present.
    from trader_bot.profit_dll_gateway import (
        ProfitDLLBroker,
        ProfitDLLClient,
        ProfitDLLMarketData,
    )

    if not (settings.profit_activation_key and settings.profit_login and settings.profit_password):
        raise ValueError(
            "MODE=real requires PROFIT_ACTIVATION_KEY, PROFIT_LOGIN and "
            "PROFIT_PASSWORD to be set in .env"
        )

    client = ProfitDLLClient(
        dll_path=settings.profit_dll_path,
        activation_key=settings.profit_activation_key,
        login=settings.profit_login,
        password=settings.profit_password,
    )
    client.connect()
    return ProfitDLLMarketData(client), ProfitDLLBroker(client)


def run(settings: Settings) -> None:
    logger.warning("Starting trader-bot in %s mode for ticker %s", settings.mode.upper(), settings.ticker)
    if settings.mode == "real":
        logger.warning(
            "REAL MODE: orders will be sent to your XP account via Profit Pro. "
            "Make sure you have validated this strategy extensively in "
            "simulated mode and Nelogica's simulator account first."
        )

    data_source, broker = build_data_source_and_broker(settings)
    strategy = MovingAverageCrossoverStrategy(settings.ma_fast, settings.ma_slow)
    risk = RiskManager(
        RiskLimits(
            max_position=settings.max_position,
            max_daily_loss=settings.max_daily_loss,
            stop_loss_points=settings.stop_loss_points,
            take_profit_points=settings.take_profit_points,
        )
    )

    def on_bar(bar: Bar) -> None:
        stop_reason = risk.check_stop_conditions(bar.price)
        if stop_reason is not None and risk.position != 0:
            side = "SELL" if risk.position > 0 else "BUY"
            logger.warning("Risk trigger: %s -> flattening position at %.2f", stop_reason, bar.price)
            fill = broker.send_order(settings.ticker, side, abs(risk.position), bar.price)
            risk.register_fill(fill.side, fill.quantity, fill.price)
            if stop_reason == "daily_loss":
                risk.force_halt(stop_reason)
                data_source.stop()
            return

        signal = strategy.on_bar(bar)
        if signal == Signal.HOLD:
            return

        try:
            qty = risk.approve_order(signal.value, settings.order_qty)
        except TradingHaltedError as exc:
            logger.warning("Order blocked by risk manager: %s", exc)
            return

        fill = broker.send_order(settings.ticker, signal.value, qty, bar.price)
        risk.register_fill(fill.side, fill.quantity, fill.price)
        logger.info(
            "Signal %s -> filled %d @ %.2f | position=%d realized_pnl=%.2f",
            signal.value, fill.quantity, fill.price, risk.position, risk.realized_pnl,
        )

    try:
        data_source.subscribe(settings.ticker, on_bar)
    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down")
    finally:
        data_source.stop()


def main() -> None:
    settings = load_settings()
    try:
        run(settings)
    except Exception:
        logger.exception("Fatal error, bot stopped")
        sys.exit(1)


if __name__ == "__main__":
    main()
