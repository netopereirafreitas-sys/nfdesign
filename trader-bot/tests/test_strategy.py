from trader_bot.strategy import Bar, MovingAverageCrossoverStrategy, Signal


def feed(strategy: MovingAverageCrossoverStrategy, prices: list[float]) -> list[Signal]:
    return [strategy.on_bar(Bar(timestamp=i, price=p)) for i, p in enumerate(prices)]


def test_invalid_periods_rejected():
    try:
        MovingAverageCrossoverStrategy(fast_period=10, slow_period=5)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_holds_until_slow_window_is_full():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4)
    signals = feed(strategy, [100, 100, 100])
    assert all(s == Signal.HOLD for s in signals)


def test_detects_bullish_crossover():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4)
    # Flat prices to fill the window, then a sharp rise so the fast MA
    # crosses above the slow MA.
    prices = [100, 100, 100, 100, 110, 120]
    signals = feed(strategy, prices)
    assert Signal.BUY in signals
    assert signals.index(Signal.BUY) == len(prices) - 1 or Signal.BUY in signals[-2:]


def test_detects_bearish_crossover():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4)
    # Rise first so the fast MA is above the slow MA, then drop sharply
    # to trigger a bearish crossover (starting already-below never
    # counts as a crossover, since nothing "crossed").
    prices = [100, 100, 100, 100, 110, 120, 90, 80]
    signals = feed(strategy, prices)
    assert Signal.BUY in signals
    assert Signal.SELL in signals
    assert signals.index(Signal.SELL) > signals.index(Signal.BUY)


def test_no_repeated_signal_while_trend_continues():
    strategy = MovingAverageCrossoverStrategy(fast_period=2, slow_period=4)
    prices = [100, 100, 100, 100, 110, 120, 130, 140]
    signals = feed(strategy, prices)
    buy_count = sum(1 for s in signals if s == Signal.BUY)
    assert buy_count == 1
