import requests
import time
from flask import Flask

app = Flask(__name__)

STARTING_CAPITAL = 50.0
DEPLOYMENT_RATIO = 0.80
MAX_POSITIONS = 5
REBALANCE_COOLDOWN = 300

cash = STARTING_CAPITAL
positions = {}
last_rebalance = 0
total_trades = 0


# ================= MARKET (CoinGecko) =================
def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "price_change_percentage_24h_desc",
            "per_page": 20,
            "page": 1
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()
        return data[:MAX_POSITIONS]

    except:
        return []


def get_price(symbol):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": symbol,
            "vs_currencies": "usd"
        }

        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            return 0

        return r.json()[symbol]["usd"]

    except:
        return 0


# ================= EQUITY =================
def current_equity():
    total = cash
    for symbol, pos in positions.items():
        price = get_price(symbol)
        total += pos["qty"] * price
    return total


# ================= REBALANCE =================
def rebalance():
    global cash, positions, last_rebalance, total_trades

    now = time.time()
    if now - last_rebalance < REBALANCE_COOLDOWN:
        return

    equity = current_equity()
    if equity <= 1:
        return

    market = get_market()
    if not market:
        return

    target_symbols = [coin["id"] for coin in market]

    # SELL old
    for symbol in list(positions.keys()):
        if symbol not in target_symbols:
            price = get_price(symbol)
            cash += positions[symbol]["qty"] * price
            del positions[symbol]
            total_trades += 1

    equity = current_equity()
    deploy_capital = equity * DEPLOYMENT_RATIO
    allocation = deploy_capital / len(target_symbols)

    for coin in market:
        symbol = coin["id"]
        price = coin["current_price"]

        if symbol in positions:
            continue

        if cash >= allocation:
            qty = allocation / price
            positions[symbol] = {"qty": qty}
            cash -= allocation
            total_trades += 1

    last_rebalance = now


# ================= DASHBOARD =================
@app.route("/")
def dashboard():
    rebalance()

    equity = current_equity()
    invested = equity - cash
    deployment = (invested / equity * 100) if equity > 0 else 0

    rows = ""
    for symbol, pos in positions.items():
        price = get_price(symbol)
        value = pos["qty"] * price

        rows += f"""
        <tr>
            <td>{symbol.upper()}</td>
            <td>{round(pos["qty"], 6)}</td>
            <td>${round(value, 2)}</td>
        </tr>
        """

    return f"""
    <html>
    <body style="background:#0e1a2b;color:white;font-family:Arial;padding:20px;">

    <h2 style="color:#4fd1c5;">ELITE AI TRADER</h2>

    <div style="background:#1f2a3c;padding:20px;border-radius:10px;margin-bottom:20px;">
        <b>Market Deployment:</b> {round(deployment,2)}%<br>
        <b>Cash:</b> ${round(cash,2)}<br>
        <b>Invested:</b> ${round(invested,2)}<br>
        <b>Total Equity:</b> ${round(equity,2)}<br>
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