"""Risk controls applied before any order reaches the broker.

This is the layer that keeps a strategy bug or a bad tick from turning
into an uncapped loss. Every order request must pass through here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_position: int
    """Max absolute number of contracts/shares held at once."""

    max_daily_loss: float
    """Trading halts for the day once realized+open P&L drops to this
    value (negative number, e.g. -500.0)."""

    stop_loss_points: float
    """Distance in price points from entry that force-closes a losing
    position."""

    take_profit_points: float
    """Distance in price points from entry that force-closes a winning
    position."""

    max_consecutive_losses: int
    """Trading halts for the day once this many closed trades in a row
    lost money (0 or negative disables this check)."""


class TradingHaltedError(Exception):
    """Raised when an order is blocked by a risk limit."""


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.position = 0
        self.entry_price: float | None = None
        self.realized_pnl = 0.0
        self.consecutive_losses = 0
        self._halted = False

    @property
    def halted(self) -> bool:
        return self._halted

    def _halt(self, reason: str) -> None:
        self._halted = True
        raise TradingHaltedError(reason)

    def open_pnl(self, last_price: float) -> float:
        if self.position == 0 or self.entry_price is None:
            return 0.0
        return (last_price - self.entry_price) * self.position

    def total_pnl(self, last_price: float) -> float:
        return self.realized_pnl + self.open_pnl(last_price)

    def check_stop_conditions(self, last_price: float) -> str | None:
        """Call on every tick. Returns 'stop_loss', 'take_profit',
        'daily_loss' if the position/day should be force-closed, else None.
        """
        if self._halted:
            return None

        if self.total_pnl(last_price) <= self.limits.max_daily_loss:
            return "daily_loss"

        if self.position != 0 and self.entry_price is not None:
            move = (last_price - self.entry_price) * (
                1 if self.position > 0 else -1
            )
            if move <= -self.limits.stop_loss_points:
                return "stop_loss"
            if move >= self.limits.take_profit_points:
                return "take_profit"

        return None

    def approve_order(self, side: str, quantity: int) -> int:
        """Validates a proposed order and returns the quantity that may
        actually be sent (may be reduced to respect max_position).

        Raises TradingHaltedError if trading is halted or the order
        would exceed limits with no safe reduction (e.g. already halted).
        """
        if self._halted:
            self._halt("trading already halted for the day")

        signed_qty = quantity if side == "BUY" else -quantity
        resulting_position = self.position + signed_qty

        if abs(resulting_position) > self.limits.max_position:
            max_allowed = self.limits.max_position - abs(self.position)
            if max_allowed <= 0:
                raise TradingHaltedError(
                    f"position limit reached ({self.limits.max_position}); order rejected"
                )
            return max_allowed

        return quantity

    def register_fill(self, side: str, quantity: int, price: float) -> None:
        signed_qty = quantity if side == "BUY" else -quantity
        new_position = self.position + signed_qty
        closed_pnl: float | None = None

        if self.position == 0:
            self.entry_price = price
        elif (self.position > 0) != (new_position > 0) and new_position != 0:
            # Position flipped sign: realize P&L on the closed portion, re-enter.
            closed_qty = min(abs(self.position), quantity)
            closed_pnl = (
                (price - self.entry_price) * closed_qty * (1 if self.position > 0 else -1)
            )
            self.realized_pnl += closed_pnl
            self.entry_price = price
        elif new_position == 0:
            closed_pnl = (
                (price - self.entry_price) * abs(self.position) * (1 if self.position > 0 else -1)
            )
            self.realized_pnl += closed_pnl
            self.entry_price = None
        # else: adding to an existing position in the same direction keeps entry_price
        # as a simplification (not volume-weighted-average). Fine for single-lot bots.

        self.position = new_position
        self._track_consecutive_losses(closed_pnl)

    def _track_consecutive_losses(self, closed_pnl: float | None) -> None:
        if closed_pnl is None:
            return  # this fill only opened/added to a position, nothing closed

        if closed_pnl < 0:
            self.consecutive_losses += 1
            if (
                self.limits.max_consecutive_losses > 0
                and self.consecutive_losses >= self.limits.max_consecutive_losses
            ):
                self._halted = True
        else:
            self.consecutive_losses = 0

    def force_halt(self, reason: str) -> None:
        self._halted = True

    def reset_daily_counters(self) -> None:
        """Call at the start of a new trading day/session to clear the
        halt and consecutive-loss streak (does not reset realized_pnl,
        which callers typically track per-day externally)."""
        self.consecutive_losses = 0
        self._halted = False
