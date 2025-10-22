**

```python
# accounts.py
"""
A simple account management system for a trading‑simulation platform.

The module provides a single public class :class:`Account` that allows a user to:
* create an account,
* deposit and withdraw cash,
* record buy/sell transactions for supported symbols,
* query current holdings,
* compute the total portfolio value,
* compute profit / loss relative to the initial deposit,
* retrieve a chronological list of all transactions.

The module is completely self‑contained and uses a mock implementation of
``get_share_price`` for the symbols *AAPL*, *S3TA* and *GOOGL*.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class AccountError(Exception):
    """Base class for all account‑related errors."""
    pass


class InsufficientFundsError(AccountError):
    """Raised when a withdrawal or a purchase would make the cash balance negative."""
    pass


class InsufficientHoldingsError(AccountError):
    """Raised when attempting to sell more shares than are currently held."""
    pass


class InvalidTransactionError(AccountError):
    """Raised when a transaction request contains invalid parameters (e.g. non‑positive amount)."""
    pass


# --------------------------------------------------------------------------- #
# Core data structures
# --------------------------------------------------------------------------- #
class TransactionType(Enum):
    """Enumeration of supported transaction kinds."""
    DEPOSIT = auto()
    WITHDRAW = auto()
    BUY = auto()
    SELL = auto()


@dataclass(frozen=True)
class Transaction:
    """
    Immutable record of a single account operation.

    Attributes
    ----------
    timestamp: datetime.datetime
        Moment when the transaction was recorded (UTC).
    type: TransactionType
        Kind of operation (DEPOSIT, WITHDRAW, BUY, SELL).
    amount: float
        Cash amount for DEPOSIT/WITHDRAW. For BUY/SELL it stores the total value
        (price_per_share * quantity). ``0.0`` for other cases.
    symbol: Optional[str]
        Ticker symbol for BUY/SELL. ``None`` for cash‑only operations.
    quantity: Optional[int]
        Number of shares bought or sold. ``None`` for cash‑only operations.
    price_per_share: Optional[float]
        Unit price resolved at transaction time. ``None`` for cash‑only operations.
    """
    timestamp: _dt.datetime
    type: TransactionType
    amount: float = 0.0
    symbol: Optional[str] = None
    quantity: Optional[int] = None
    price_per_share: Optional[float] = None


# --------------------------------------------------------------------------- #
# Public API – Account class
# --------------------------------------------------------------------------- #
class Account:
    """
    Represents a single user's trading account.

    Parameters
    ----------
    user_id : str
        Unique identifier for the owner of the account.
    name : Optional[str]
        Human readable name for the account holder.

    Notes
    -----
    * The initial cash balance is ``0.0``.  Funds must be added by calling
      :meth:`deposit`.
    * All monetary amounts are stored as ``float`` – for a production system
      using ``Decimal`` is recommended.
    * The class maintains an internal ledger of :class:`Transaction` objects.
    """

    def __init__(self, user_id: str, name: Optional[str] = None) -> None:
        self.user_id: str = user_id
        self.name: Optional[str] = name

        self._cash_balance: float = 0.0          # liquid cash on the account
        self._initial_deposit: float = 0.0       # total amount ever deposited (used for P/L)
        self._holdings: Dict[str, int] = {}      # symbol -> quantity owned
        self._ledger: List[Transaction] = []     # chronological transaction history

    # --------------------------------------------------------------------- #
    # Cash management
    # --------------------------------------------------------------------- #
    def deposit(self, amount: float) -> None:
        """
        Add cash to the account.

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
        """
        Remove cash from the account, ensuring the balance never becomes negative.

        Parameters
        ----------
        amount : float
            Positive amount to withdraw.

        Raises
        ------
        InvalidTransactionError
            If ``amount`` is not positive.
        InsufficientFundsError
            If withdrawing would make the cash balance negative.
        """
        if amount <= 0:
            raise InvalidTransactionError("Withdrawal amount must be positive.")
        if amount > self._cash_balance:
            raise InsufficientFundsError(
                f"Requested {amount:.2f}, but only {self._cash_balance:.2f} is available."
            )
        self._cash_balance -= amount
        self._record_transaction(
            TransactionType.WITHDRAW,
            amount=amount,
        )

    # --------------------------------------------------------------------- #
    # Trading operations
    # --------------------------------------------------------------------- #
    def buy(self, symbol: str, quantity: int) -> None:
        """
        Record a purchase of ``quantity`` shares of ``symbol``.

        The transaction succeeds only if the account has enough cash to cover the
        total cost (price * quantity).

        Parameters
        ----------
        symbol : str
            Ticker symbol of the security to buy.
        quantity : int
            Number of shares to purchase (must be > 0).

        Raises
        ------
        InvalidTransactionError
            If ``quantity`` is not positive.
        InsufficientFundsError
            If the cash balance is insufficient for the purchase.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Buy quantity must be a positive integer.")
        price = get_share_price(symbol)
        total_cost = price * quantity
        if total_cost > self._cash_balance:
            raise InsufficientFundsError(
                f"Purchase requires {total_cost:.2f}, but only {self._cash_balance:.2f} is available."
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
        """
        Record a sale of ``quantity`` shares of ``symbol``.

        The transaction succeeds only if the account currently holds at least that
        many shares.

        Parameters
        ----------
        symbol : str
            Ticker symbol of the security to sell.
        quantity : int
            Number of shares to sell (must be > 0).

        Raises
        ------
        InvalidTransactionError
            If ``quantity`` is not positive.
        InsufficientHoldingsError
            If the account does not hold enough shares of the symbol.
        """
        if quantity <= 0:
            raise InvalidTransactionError("Sell quantity must be a positive integer.")
        current_qty = self._holdings.get(symbol, 0)
        if quantity > current_qty:
            raise InsufficientHoldingsError(
                f"Attempted to sell {quantity} {symbol}, but only {current_qty} are held."
            )
        price = get_share_price(symbol)
        proceeds = price * quantity
        # Update state
        self._cash_balance += proceeds
        new_qty = current_qty - quantity
        if new_qty:
            self._holdings[symbol] = new_qty
        else:
            del self._holdings[symbol]   # clean up zero‑holding entries
        self._record_transaction(
            TransactionType.SELL,
            amount=proceeds,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price,
        )

    # --------------------------------------------------------------------- #
    # Reporting utilities
    # --------------------------------------------------------------------- #
    @property
    def cash_balance(self) -> float:
        """Current cash available on the account (read‑only)."""
        return self._cash_balance

    @property
    def holdings(self) -> Dict[str, int]:
        """
        Snapshot of current holdings.

        Returns a copy to prevent external mutation.
        """
        return dict(self._holdings)

    def get_portfolio_value(self) -> float:
        """
        Compute the total market value of all held shares using the latest prices.

        Returns
        -------
        float
            Sum of (quantity * current_price) for each symbol.
        """
        total = 0.0
        for symbol, qty in self._holdings.items():
            total += qty * get_share_price(symbol)
        return total

    def get_total_equity(self) -> float:
        """
        Total account equity = cash + portfolio market value.

        Returns
        -------
        float
            Sum of cash balance and portfolio market value.
        """
        return self._cash_balance + self.get_portfolio_value()

    def get_profit_loss(self) -> float:
        """
        Compute profit/loss relative to the *initial* cash deposited.

        Positive value indicates profit, negative value indicates loss.

        Returns
        -------
        float
            ``total_equity - initial_deposit``.
        """
        return self.get_total_equity() - self._initial_deposit

    def list_transactions(
        self,
        start: Optional[_dt.datetime] = None,
        end: Optional[_dt.datetime] = None,
    ) -> List[Transaction]:
        """
        Return a chronological list of transactions, optionally filtered by a
        time window.

        Parameters
        ----------
        start : datetime, optional
            Include only transactions occurring *on or after* this timestamp.
        end : datetime, optional
            Include only transactions occurring *on or before* this timestamp.

        Returns
        -------
        List[Transaction]
            List of matching transaction objects.
        """
        if start is None and end is None:
            return list(self._ledger)  # shallow copy

        filtered = [
            txn for txn in self._ledger
            if (start is None or txn.timestamp >= start)
            and (end is None or txn.timestamp <= end)
        ]
        return filtered

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _record_transaction(
        self,
        txn_type: TransactionType,
        amount: float = 0.0,
        symbol: Optional[str] = None,
        quantity: Optional[int] = None,
        price_per_share: Optional[float] = None,
    ) -> None:
        """
        Create a :class:`Transaction` instance and append it to the internal ledger.
        This method centralises timestamp creation and ensures immutability of
        transaction records.
        """
        txn = Transaction(
            timestamp=_dt.datetime.utcnow(),
            type=txn_type,
            amount=amount,
            symbol=symbol,
            quantity=quantity,
            price_per_share=price_per_share,
        )
        self._ledger.append(txn)

    # --------------------------------------------------------------------- #
    # Representation helpers
    # --------------------------------------------------------------------- #
    def __repr__(self) -> str:
        return (
            f"Account(user_id={self.user_id!r}, name={self.name!r}, "
            f"cash={self._cash_balance:.2f}, holdings={self._holdings})"
        )


# --------------------------------------------------------------------------- #
# Mock price provider (replace with real market data source in production)
# --------------------------------------------------------------------------- #
def get_share_price(symbol: str) -> float:
    """
    Return a mocked current price for a given ticker symbol.

    The function is deliberately simple: it supports a small, fixed set of
    symbols required for unit‑testing.  An unknown symbol raises ``KeyError``.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. ``'AAPL'``).

    Returns
    -------
    float
        Current price per share.

    Raises
    ------
    KeyError
        If ``symbol`` is not present in the hard‑coded price table.
    """
    price_table: Dict[str, float] = {
        "AAPL": 150.00,
        "TSLA": 720.00,
        "GOOGL": 2800.00,
    }
    try:
        return price_table[symbol.upper()]
    except KeyError as exc:
        raise KeyError(f"Price for symbol '{symbol}' is not defined in the mock provider.") from exc


# --------------------------------------------------------------------------- #
# Example usage (executed only when run as a script)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Simple sanity test to demonstrate the public API.
    acct = Account(user_id="u123", name="Demo User")
    acct.deposit(10_000)
    acct.buy("AAPL", 20)       # spend 20 * 150 = 3,000
    acct.sell("AAPL", 5)       # receive 5 * 150 = 750
    acct.withdraw(1_000)

    print(acct)
    print("Cash balance:", acct.cash_balance)
    print("Holdings:", acct.holdings)
    print("Portfolio market value:", acct.get_portfolio_value())
    print("Total equity:", acct.get_total_equity())
    print("Profit / Loss:", acct.get_profit_loss())
    print("All transactions:")
    for tx in acct.list_transactions():
        print("  ", tx)
```