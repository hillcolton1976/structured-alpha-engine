import requests
import time
from flask import Flask

app = Flask(__name__)

STARTING_CAPITAL = 10.0
DEPLOYMENT_RATIO = 0.90
MAX_POSITIONS = 5
REBALANCE_COOLDOWN = 120  # 2 minutes

cash = STARTING_CAPITAL
positions = {}
last_rebalance = 0
total_trades = 0


# ================= MARKET =================
def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "price_change_percentage_24h_desc",
            "per_page": MAX_POSITIONS,
            "page": 1
        }

        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []

        return r.json()

    except:
        return []


def get_price(coin_id):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd"
        }

        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return 0

        return r.json()[coin_id]["usd"]

    except:
        return 0


# ================= EQUITY =================
def current_equity():
    total = cash
    for coin_id, pos in positions.items():
        price = get_price(coin_id)
        total += pos["qty"] * price
    return total


# ================= REBALANCE =================
def rebalance():
    global cash, positions, last_rebalance, total_trades

    now = time.time()

    if now - last_rebalance < REBALANCE_COOLDOWN:
        return

    market = get_market()
    if not market:
        return

    equity = current_equity()
    deploy_capital = equity * DEPLOYMENT_RATIO
    allocation = deploy_capital / MAX_POSITIONS

    new_positions = {}

    for coin in market:
        coin_id = coin["id"]
        price = coin["current_price"]

        qty = allocation / price
        new_positions[coin_id] = {"qty": qty}

    positions = new_positions
    cash = equity - deploy_capital
    total_trades += MAX_POSITIONS

    last_rebalance = now


# ================= DASHBOARD =================
@app.route("/")
def dashboard():
    rebalance()

    equity = current_equity()
    invested = equity - cash
    deployment = (invested / equity * 100) if equity > 0 else 0
    pnl = equity - STARTING_CAPITAL

    rows = ""
    for coin_id, pos in positions.items():
        price = get_price(coin_id)
        value = pos["qty"] * price

        rows += f"""
        <tr>
            <td>{coin_id.upper()}</td>
            <td>{round(pos["qty"], 6)}</td>
            <td>${round(value, 2)}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="10">
    </head>
    <body style="background:#0e1a2b;color:white;font-family:Arial;padding:20px;">

    <h2 style="color:#4fd1c5;">ELITE AI TRADER (LIVE PAPER MODE)</h2>

    <div style="background:#1f2a3c;padding:20px;border-radius:10px;margin-bottom:20px;">
        <b>Market Deployment:</b> {round(deployment,2)}%<br>
        <b>Cash:</b> ${round(cash,2)}<br>
        <b>Invested:</b> ${round(invested,2)}<br>
        <b>Total Equity:</b> ${round(equity,2)}<br>
        <b>PnL:</b> ${round(pnl,2)}<br>
        <b>Total Trades:</b> {total_trades}
    </div>

    <div style="background:#1f2a3c;padding:20px;border-radius:10px;">
        <h3>Positions</h3>
        <table width="100%">
            <tr>
                <th align="left">Coin</th>
                <th align="left">Quantity</th>
                <th align="left">Value</th>
            </tr>
            {rows}
        </table>
    </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)