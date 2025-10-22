import gradio as gr
from accounts import Account, get_share_price

# Global account instance (single‑user demo)
account = None

def get_info():
    """Return rendered markdown strings for cash, holdings, equity, P/L and transaction log."""
    if account is None:
        placeholder = "Account not created yet."
        return placeholder, placeholder, placeholder, placeholder, placeholder

    # Cash balance
    cash_md = f"**Cash Balance:** ${account.cash_balance:,.2f}"

    # Holdings
    if account.holdings:
        holdings_lines = []
        for sym, qty in account.holdings.items():
            price = get_share_price(sym)
            holdings_lines.append(f"- {sym}: {qty} shares @ ${price:,.2f}")
        holdings_md = "**Holdings:**\n" + "\n".join(holdings_lines)
    else:
        holdings_md = "**Holdings:** None"

    # Total equity and P/L
    equity_md = f"**Total Equity:** ${account.get_total_equity():,.2f}"
    pnl_md = f"**Profit/Loss:** ${account.get_profit_loss():,.2f}"

    # Transaction log (show all, newest first)
    txns = account.list_transactions()
    if txns:
        log_md = "### Transaction Log\n"
        log_md += "| Timestamp | Type | Symbol | Quantity | Price per Share | Amount |\n"
        log_md += "|---|---|---|---|---|---|\n"
        for t in reversed(txns):
            ts = t.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            typ = t.type.name
            sym = t.symbol if t.symbol else "-"
            qty = str(t.quantity) if t.quantity else "-"
            price = f"${t.price_per_share:,.2f}" if t.price_per_share else "-"
            amount = f"${t.amount:,.2f}"
            log_md += f"| {ts} | {typ} | {sym} | {qty} | {price} | {amount} |\n"
    else:
        log_md = "### Transaction Log\nNo transactions yet."

    return cash_md, holdings_md, equity_md, pnl_md, log_md

def create_account(user_id, name):
    global account
    try:
        account = Account(user_id, name)
        status = f"Account created for **{name}** (ID: {user_id})."
    except Exception as e:
        status = f"Error creating account: {e}"
    cash_md, holdings_md, equity_md, pnl_md, log_md = get_info()
    return status, cash_md, holdings_md, equity_md, pnl_md, log_md

def deposit_f(amount):
    if account is None:
        return "No account created yet.", *[""] * 5
    try:
        account.deposit(float(amount))
        status = f"Deposited ${float(amount):,.2f}."
    except Exception as e:
        status = f"Deposit error: {e}"
    cash_md, holdings_md, equity_md, pnl_md, log_md = get_info()
    return status, cash_md, holdings_md, equity_md, pnl_md, log_md

def withdraw_f(amount):
    if account is None:
        return "No account created yet.", *[""] * 5
    try:
        account.withdraw(float(amount))
        status = f"Withdrew ${float(amount):,.2f}."
    except Exception as e:
        status = f"Withdrawal error: {e}"
    cash_md, holdings_md, equity_md, pnl_md, log_md = get_info()
    return status, cash_md, holdings_md, equity_md, pnl_md, log_md

def trade_f(symbol, qty, direction):
    if account is None:
        return "No account created yet.", *[""] * 5
    try:
        qty_int = int(qty)
        if direction == "Buy":
            account.buy(symbol, qty_int)
            status = f"Bought {qty_int} shares of {symbol}."
        else:
            account.sell(symbol, qty_int)
            status = f"Sold {qty_int} shares of {symbol}."
    except Exception as e:
        status = f"Trade error: {e}"
    cash_md, holdings_md, equity_md, pnl_md, log_md = get_info()
    return status, cash_md, holdings_md, equity_md, pnl_md, log_md

with gr.Blocks() as demo:
    gr.Markdown("# Trading Simulator Demo (single user)")

    with gr.Row():
        with gr.Column():
            user_id_in = gr.Textbox(label="User ID", placeholder="e.g., user123")
            name_in = gr.Textbox(label="Name", placeholder="Your Name")
            create_btn = gr.Button("Create Account")
        with gr.Column():
            deposit_amount = gr.Number(label="Deposit Amount", precision=2)
            deposit_btn = gr.Button("Deposit")
            withdraw_amount = gr.Number(label="Withdraw Amount", precision=2)
            withdraw_btn = gr.Button("Withdraw")
    
    with gr.Row():
        with gr.Column():
            symbol_dd = gr.Dropdown(label="Symbol", choices=["AAPL", "TSLA", "GOOGL"])
            qty_num = gr.Number(label="Quantity", precision=0, value=1)
            direction_rb = gr.Radio(label="Direction", choices=["Buy", "Sell"], value="Buy")
            trade_btn = gr.Button("Execute Trade")

    status_md = gr.Markdown()
    cash_md = gr.Markdown()
    holdings_md = gr.Markdown()
    equity_md = gr.Markdown()
    pnl_md = gr.Markdown()
    log_md = gr.Markdown()

    create_btn.click(fn=create_account,
                     inputs=[user_id_in, name_in],
                     outputs=[status_md, cash_md, holdings_md, equity_md, pnl_md, log_md])

    deposit_btn.click(fn=deposit_f,
                      inputs=[deposit_amount],
                      outputs=[status_md, cash_md, holdings_md, equity_md, pnl_md, log_md])

    withdraw_btn.click(fn=withdraw_f,
                       inputs=[withdraw_amount],
                       outputs=[status_md, cash_md, holdings_md, equity_md, pnl_md, log_md])

    trade_btn.click(fn=trade_f,
                    inputs=[symbol_dd, qty_num, direction_rb],
                    outputs=[status_md, cash_md, holdings_md, equity_md, pnl_md, log_md])

if __name__ == "__main__":
    demo.launch()