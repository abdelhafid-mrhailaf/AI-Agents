import unittest
import datetime as dt

from accounts import (
    Account,
    InvalidTransactionError,
    InsufficientFundsError,
    InsufficientHoldingsError,
    TransactionType,
)


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.account = Account(user_id="test_user", name="Test User")

    def test_deposit_success(self):
        self.account.deposit(500.0)
        self.assertEqual(self.account.cash_balance, 500.0)
        self.assertEqual(self.account._initial_deposit, 500.0)

        txns = self.account.list_transactions()
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].type, TransactionType.DEPOSIT)
        self.assertEqual(txns[0].amount, 500.0)

    def test_deposit_invalid_amount(self):
        with self.assertRaises(InvalidTransactionError):
            self.account.deposit(-100.0)

    def test_withdraw_success(self):
        self.account.deposit(1000.0)
        self.account.withdraw(300.0)

        self.assertEqual(self.account.cash_balance, 700.0)

        txns = self.account.list_transactions()
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[1].type, TransactionType.WITHDRAW)
        self.assertEqual(txns[1].amount, 300.0)

    def test_withdraw_invalid_amount(self):
        self.account.deposit(200.0)
        with self.assertRaises(InvalidTransactionError):
            self.account.withdraw(0)

    def test_withdraw_insufficient_funds(self):
        self.account.deposit(100.0)
        with self.assertRaises(InsufficientFundsError):
            self.account.withdraw(150.0)

    def test_buy_success(self):
        self.account.deposit(2000.0)
        self.account.buy("AAPL", 5)  # 5 * 150 = 750

        self.assertAlmostEqual(self.account.cash_balance, 1250.0)
        self.assertEqual(self.account.holdings, {"AAPL": 5})

        txns = self.account.list_transactions()
        self.assertEqual(txns[-1].type, TransactionType.BUY)
        self.assertEqual(txns[-1].symbol, "AAPL")
        self.assertEqual(txns[-1].quantity, 5)
        self.assertAlmostEqual(txns[-1].price_per_share, 150.0)
        self.assertAlmostEqual(txns[-1].amount, 750.0)

    def test_buy_invalid_quantity(self):
        self.account.deposit(500.0)
        with self.assertRaises(InvalidTransactionError):
            self.account.buy("AAPL", 0)

    def test_buy_insufficient_funds(self):
        self.account.deposit(100.0)
        with self.assertRaises(InsufficientFundsError):
            self.account.buy("AAPL", 1)  # costs 150

    def test_buy_unknown_symbol(self):
        self.account.deposit(1000.0)
        with self.assertRaises(KeyError):
            self.account.buy("UNKNOWN", 1)

    def test_sell_success(self):
        self.account.deposit(2000.0)
        self.account.buy("TSLA", 2)   # 2 * 630 = 1260
        self.account.sell("TSLA", 1)  # receive 630

        self.assertAlmostEqual(self.account.cash_balance, 1370.0)
        self.assertEqual(self.account.holdings, {"TSLA": 1})

        txns = self.account.list_transactions()
        self.assertEqual(txns[-1].type, TransactionType.SELL)
        self.assertEqual(txns[-1].symbol, "TSLA")
        self.assertEqual(txns[-1].quantity, 1)
        self.assertAlmostEqual(txns[-1].price_per_share, 630.0)
        self.assertAlmostEqual(txns[-1].amount, 630.0)

    def test_sell_all_clears_holding(self):
        self.account.deposit(500.0)
        self.account.buy("AAPL", 2)  # cost 300
        self.account.sell("AAPL", 2)  # sell all

        self.assertNotIn("AAPL", self.account.holdings)

    def test_sell_invalid_quantity(self):
        self.account.deposit(500.0)
        self.account.buy("AAPL", 1)
        with self.assertRaises(InvalidTransactionError):
            self.account.sell("AAPL", 0)

    def test_sell_insufficient_holdings(self):
        self.account.deposit(500.0)
        self.account.buy("AAPL", 1)
        with self.assertRaises(InsufficientHoldingsError):
            self.account.sell("AAPL", 2)

    def test_portfolio_and_equity(self):
        self.account.deposit(3000.0)
        self.account.buy("AAPL", 4)   # 600
        self.account.buy("GOOGL", 1)  # 2800

        # Cash left should be 3000 - 600 - 2800 = -400 (but insufficient funds prevented)
        # Actually purchase should fail due to insufficient cash after first buy.
        # Recreate scenario with sufficient funds.
        self.account = Account(user_id="test_user2")
        self.account.deposit(5000.0)
        self.account.buy("AAPL", 4)   # 600
        self.account.buy("GOOGL", 1)  # 2800

        portfolio_val = self.account.get_portfolio_value()
        self.assertAlmostEqual(portfolio_val, 4 * 150.0 + 1 * 2800.0)

        total_equity = self.account.get_total_equity()
        expected_cash = 5000.0 - (4 * 150.0) - 2800.0
        self.assertAlmostEqual(total_equity, expected_cash + portfolio_val)

    def test_profit_calculation(self):
        self.account.deposit(1000.0)
        self.account.buy("AAPL", 4)   # spend 600
        self.account.sell("AAPL", 2)  # receive 300

        # Cash: 1000 - 600 + 300 = 700
        # Holdings: 2 AAPL = 300
        # Total equity: 1000
        self.assertAlmostEqual(self.account.get_total_equity(), 1000.0)
        self.assertAlmostEqual(self.account.get_profit(), 0.0)

        # Add profit by depositing extra cash
        self.account.deposit(200.0)
        self.assertAlmostEqual(self.account.get_total_equity(), 1200.0)
        self.assertAlmostEqual(self.account.get_profit(), 200.0)

    def test_list_transactions_time_filter(self):
        # Perform three actions spaced by a small time delta
        self.account.deposit(100.0)
        t1 = dt.datetime.utcnow()
        self.account.buy("AAPL", 1)
        t2 = dt.datetime.utcnow()
        self.account.withdraw(20.0)
        t3 = dt.datetime.utcnow()

        all_txns = self.account.list_transactions()
        self.assertEqual(len(all_txns), 3)

        # Filter between t1 and t2 (should include only the BUY)
        filtered = self.account.list_transactions(start=t1, end=t2)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].type, TransactionType.BUY)

    def test_repr(self):
        self.account.deposit(100.0)
        self.account.buy("AAPL", 1)
        repr_str = repr(self.account)
        self.assertIn("Account", repr_str)
        self.assertIn("cash=", repr_str)
        self.assertIn("holdings=", repr_str)


if __name__ == "__main__":
    unittest.main()