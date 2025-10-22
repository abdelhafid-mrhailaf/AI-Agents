# accounts.py
"""
A simplified account management system for a trading simulation platform.

Provides a single public class :class:`Account` that enables:
* creation of a trading account
* deposit and withdrawal of cash
* buying and selling of shares
* querying holdings, portfolio value, and profit/loss
* listing a chronological log of all transactions

The module includes a mock implementation of ``get_share_price`` that
covers a few static tickers (AAPL, TSLA, GOOGL) for testing purposes.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class AccountError(Exception):
    """Base class for all account‑related errors."""
    pass


class InsufficientFundsError(AccountError):
    """Raised when a withdrawal or purchase would lead to a negative cash balance."""
    pass


class InsufficientHoldingsError(AccountError):
    """Raised when trying to sell more shares than are currently owned."""
    pass


class InvalidTransactionError(AccountError):
    """Raised when a transaction receives invalid arguments (e.g., negative amounts)."""
    pass


# --------------------------------------------------------------------------- #
# Core data structures
# --------------------------------------------------------------------------- #
class TransactionType(Enum):
    """Supported transaction categories."""
    DEPOSIT = auto()
    WITHDRAW = auto()
    BUY = auto()
    SELL = auto()


@dataclass(frozen=True)
class Transaction:
    """Immutable record of a single account operation.

    Attributes
    ----------
    timestamp : datetime.datetime
        Moment when the transaction was recorded (UTC).
    type : TransactionType
        Kind of operation (DEPOSIT, WITHDRAW, BUY, SELL).
    amount : float
        Cash amount for DEPOSIT/WITHDRAW. For BUY/SELL it contains the total
        transaction value (price_per_share * quantity). Zero for other ops.
    symbol : Optional[str]
        Ticker symbol for BUY/SELL, otherwise ``None``.
    quantity : Optional[int]
        Number of shares for BUY/SELL, otherwise ``None``.
    price_per_share : Optional[float]
        Unit price fixed at transaction time, otherwise ``None``.
    """
    timestamp: _dt.datetime
    type: TransactionType
    amount: float = 0.0
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    price_per_share: Optional[float] = None


# --------------------------------------------------------------------------- #
# Public API – Account
# --------------------------------------------------------------------------- #
class Account:
    """
    Represents a user's trading account.

    Parameters
    ----------
    user_id : str
        Unique identifier for the account owner.
    name : Optional[str]
        Human‑readable name for the owner (optional).
    """

    def __init__(self, user_id: str, name: Optional[str] = None) -> None:
        self.user_id: str = user_id
        self.name: Optional[str] = name

        self._cash_balance: float = 0.0          # liquid cash
        self._initial_deposit: float = 0.0       # cumulative deposit amount (for P/L)
        self._holdings: Dict[str, int] = {}      # symbol -> shares owned
        self._ledger: List[Transaction] = []     # chronological transaction log

    # ------------------------------------------------------------------- #
    # Cash management
    # ------------------------------------------------------------------- #
    def deposit(self, amount: float) -> None:
        """Add cash to the account.

        Parameters
        ----------
        amount : float
            Positive amount to deposit.

        Raises
        ------
        InvalidTransactionError
            If ``amount`` is not positive.
        """
        if amount <= 0:
            raise InvalidTransactionError("Deposit amount must be positive.")
        self._cash_balance += amount
        self._initial_deposit += amount
        self._record_transaction(
            TransactionType.DEPOSIT,
            amount=amount,
        )

    def withdraw(self, amount: float) -> None:
        """Remove cash from the account, ensuring a non‑negative balance.

        Parameters
        ----------
        amount : float
            Positive amount to withdraw.

        Raises
        ------
        InvalidTransactionError
            If ``amount`` is not positive.
        InsufficientFundsError
            If the withdrawal would cause a negative cash balance.
        """
        if amount <= 0:
            raise InvalidTransactionError("Withdrawal amount must be positive.")
        if amount > self._cash_balance:
            raise InsufficientFundsError(
                f"Requested {amount:.2f}, but only {self._cash_balance:.2f} available."
            )
        self._cash_balance -= amount
        self._record_transaction(
            TransactionType.WITHDRAW,
            amount=amount,
        )

    # ------------------------------------------------------------------- #
    # Trading operations
    # ------------------------------------------------------------------- #
    def buy(self, symbol: str, quantity: int) -> None:
        """Purchase ``quantity`` shares of ``symbol``.

        Parameters
        ----------
        symbol : str
            Ticker to purchase.
        quantity : int
            Number of shares (must be > 0).

        Raises
        ------
        InvalidTransactionError
            If ``quantity`` is not positive.
        InsufficientFundsError
            If cash is insufficient for the transaction.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Buy quantity must be a positive integer.")
        price = get_share_price(symbol)
        total_cost = price * quantity
        if total_cost > self._cash_balance:
            raise InsufficientFundsError(
                f"Purchase requires {total_cost:.2f}, but only {self._cash_balance:.2f} available."
            )
        # Update state
        self._cash_balance -= total_cost
        self._holdings[symbol] = self._holdings.get(symbol, 0) + quantity
        self._record_transaction(
            TransactionType.BUY,
            amount=total_cost,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price,
        )

    def sell(self, symbol: str, quantity: int) -> None:
        """Sell ``quantity`` shares of ``symbol``.

        Parameters
        ----------
        symbol : str
            Ticker to sell.
        quantity : int
            Number of shares (must be > 0).

        Raises
        ------
        InvalidTransactionError
            If ``quantity`` is not positive.
        InsufficientHoldingsError
            If shares held are insufficient.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Sell quantity must be a positive integer.")
        current_qty = self._holdings.get(symbol, 0)
        if quantity > current_qty:
            raise InsufficientHoldingsError(
                f"Attempted to sell {quantity} of {symbol}, but only {current_qty} held."
            )
        price = get_share_price(symbol)
        proceeds = price * quantity
        # Update state
        self._cash_balance += proceeds
        new_qty = current_qty - quantity
        if new_qty:
            self._holdings[symbol] = new_qty
        else:
            del self._holdings[symbol]  # clean empty holdings
        self._record_transaction(
            TransactionType.SELL,
            amount=proceeds,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price,
        )

    # ------------------------------------------------------------------- #
    # Reporting utilities
    # ------------------------------------------------------------------- #
    @property
    def cash_balance(self) -> float:
        """Current liquid cash in the account (read‑only)."""
        return self._cash_balance

    @property
    def holdings(self) -> Dict[str, int]:
        """Snapshot of current holdings (symbol -> quantity). Returns a copy."""
        return dict(self._holdings)

    def get_portfolio_value(self) -> float:
        """Calculate the total market value of all held shares."""
        total = 0.0
        for sym, qty in self._holdings.items():
            total += qty * get_share_price(sym)
        return total

    def get_total_equity(self) -> float:
        """Total equity = cash + portfolio value."""
        return self._cash_balance + self.get_portfolio_value()

    def get_profit_loss(self) -> float:
        """Profit/loss relative to the cumulative initial deposit."""
        return self.get_total_equity() - self._initial_deposit

    def list_transactions(
        self,
        start: Optional[_dt.datetime] = None,
        end: Optional[_dt.datetime] = None,
    ) -> List[Transaction]:
        """Return a chronological list of transactions, optionally filtered by time."""
        if start is None and end is None:
            return list(self._ledger)  # shallow copy
        return [
            txn for txn in self._ledger
            if (start is None or txn.timestamp >= start) and
               (end is None or txn.timestamp <= end)
        ]

    # ------------------------------------------------------------------- #
    # Internal helpers
    # ------------------------------------------------------------------- #
    def _record_transaction(
        self,
        txn_type: TransactionType,
        amount: float = 0.0,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        price_per_share: Optional[float] = None,
    ) -> None:
        """Create a ``Transaction`` record and add it to the ledger."""
        txn = Transaction(
            timestamp=_dt.datetime.utcnow(),
            type=txn_type,
            amount=amount,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price_per_share,
        )
        self._ledger.append(txn)

    # ------------------------------------------------------------------- #
    # Representation
    # ------------------------------------------------------------------- #
    def __repr__(self) -> str:
        return (
            f"Account(user_id={self.user_id!r}, name={self.name!r}, "
            f"cash={self._cash_balance:.2f}, holdings={self._holdings})"
        )


# --------------------------------------------------------------------------- #
# Mock share price provider (replace with real data feed for production)
# --------------------------------------------------------------------------- #
def get_share_price(symbol: str) -> float:
    """Return a static price for supported symbols.

    Supported symbols:
    * AAPL  -> 150.00
    * TSLA  -> 630.00
    * GOOGL -> 2800.00

    Raises
    ------
    KeyError
        If the symbol is not defined.
    """
    price_table: Dict[str, float] = {
        "AAPL": 150.00,
        "TSLA": 630.00,
        "GOOGL": 2800.00,
    }
    try:
        return price_table[symbol.upper()]
    except KeyError as exc:
        raise KeyError(f"Price not defined for symbol '{symbol}'.") from exc


# --------------------------------------------------------------------------- #
# Minimal demonstration when executed as a script
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    acct = Account(user_id="test123", name="Demo User")
    acct.deposit(10000)
    acct.buy("AAPL", 20)       # 20 * 150 = 3000
    acct.sell("AAPL", 5)       # 5 * 150 = 750
    acct.withdraw(2000)

    print(acct)
    print("Cash:", acct.cash_balance)
    print("Holdings:", acct.holdings)
    print("Portfolio value:", acct.get_portfolio_value())
    print("Total equity:", acct.get_total_equity())
    print("Profit/Loss:", acct.get_profit_loss())
    print("\nTransaction log:")
    for t in acct.list_transactions():
        print(t)