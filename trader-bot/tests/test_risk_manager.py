import pytest

from trader_bot.risk_manager import RiskLimits, RiskManager, TradingHaltedError


def make_manager(**overrides) -> RiskManager:
    defaults = dict(
        max_position=1,
        max_daily_loss=-500.0,
        stop_loss_points=100.0,
        take_profit_points=200.0,
        max_consecutive_losses=3,
    )
    defaults.update(overrides)
    return RiskManager(RiskLimits(**defaults))


def test_approve_order_within_limits():
    risk = make_manager(max_position=2)
    assert risk.approve_order("BUY", 2) == 2


def test_approve_order_clamped_to_max_position():
    risk = make_manager(max_position=1)
    risk.register_fill("BUY", 1, price=100.0)
    with pytest.raises(TradingHaltedError):
        risk.approve_order("BUY", 1)


def test_stop_loss_triggers_after_adverse_move():
    risk = make_manager(stop_loss_points=50.0)
    risk.register_fill("BUY", 1, price=100.0)
    assert risk.check_stop_conditions(100.0) is None
    assert risk.check_stop_conditions(49.0) == "stop_loss"


def test_take_profit_triggers_after_favorable_move():
    risk = make_manager(take_profit_points=50.0)
    risk.register_fill("BUY", 1, price=100.0)
    assert risk.check_stop_conditions(151.0) == "take_profit"


def test_daily_loss_halts_trading():
    risk = make_manager(max_daily_loss=-100.0)
    risk.register_fill("BUY", 1, price=100.0)
    assert risk.check_stop_conditions(-1.0) == "daily_loss"
    risk.force_halt("daily_loss")
    with pytest.raises(TradingHaltedError):
        risk.approve_order("BUY", 1)


def test_register_fill_realizes_pnl_on_flatten():
    risk = make_manager(max_position=1)
    risk.register_fill("BUY", 1, price=100.0)
    risk.register_fill("SELL", 1, price=110.0)
    assert risk.position == 0
    assert risk.realized_pnl == pytest.approx(10.0)


def test_register_fill_realizes_pnl_on_flip():
    risk = make_manager(max_position=1)
    risk.register_fill("BUY", 1, price=100.0)
    risk.register_fill("SELL", 2, price=90.0)
    assert risk.position == -1
    assert risk.realized_pnl == pytest.approx(-10.0)


def test_consecutive_losses_halt_trading():
    risk = make_manager(max_position=1, max_consecutive_losses=3)
    # Three losing round-trips in a row: buy at 100, sell lower, each time.
    for _ in range(3):
        risk.register_fill("BUY", 1, price=100.0)
        risk.register_fill("SELL", 1, price=90.0)

    assert risk.consecutive_losses == 3
    assert risk.halted
    with pytest.raises(TradingHaltedError):
        risk.approve_order("BUY", 1)


def test_winning_trade_resets_consecutive_losses():
    risk = make_manager(max_position=1, max_consecutive_losses=3)
    risk.register_fill("BUY", 1, price=100.0)
    risk.register_fill("SELL", 1, price=90.0)  # loss #1
    risk.register_fill("BUY", 1, price=90.0)
    risk.register_fill("SELL", 1, price=100.0)  # win, resets streak

    assert risk.consecutive_losses == 0
    assert not risk.halted


def test_max_consecutive_losses_zero_disables_check():
    risk = make_manager(max_position=1, max_consecutive_losses=0)
    for _ in range(10):
        risk.register_fill("BUY", 1, price=100.0)
        risk.register_fill("SELL", 1, price=90.0)

    assert not risk.halted


def test_opening_and_adding_to_position_does_not_affect_streak():
    risk = make_manager(max_position=5, max_consecutive_losses=3)
    risk.register_fill("BUY", 1, price=100.0)
    risk.register_fill("BUY", 1, price=101.0)  # adds to position, nothing closed
    assert risk.consecutive_losses == 0
    assert not risk.halted


def test_reset_daily_counters_clears_halt_and_streak():
    risk = make_manager(max_position=1, max_consecutive_losses=1)
    risk.register_fill("BUY", 1, price=100.0)
    risk.register_fill("SELL", 1, price=90.0)
    assert risk.halted

    risk.reset_daily_counters()
    assert not risk.halted
    assert risk.consecutive_losses == 0
    assert risk.approve_order("BUY", 1) == 1
