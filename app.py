import requests
import time
from flask import Flask

app = Flask(__name__)

# ================= SETTINGS =================
STARTING_CAPITAL = 50.0
DEPLOYMENT_RATIO = 0.80
MAX_POSITIONS = 5
MIN_TRADE_SIZE = 1.00
REBALANCE_COOLDOWN = 300  # 5 minutes

# ================= STATE =================
cash = STARTING_CAPITAL
positions = {}  # {symbol: {"qty": float, "entry": float}}
last_rebalance = 0
total_trades = 0


# ================= MARKET DATA =================
def get_market():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        usdt_pairs = [
            c for c in data
            if c["symbol"].endswith("USDT")
            and not c["symbol"].startswith(("BUSD", "USDC"))
        ]

        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x["priceChangePercent"]),
            reverse=True
        )

        return sorted_pairs[:MAX_POSITIONS]

    except:
        return []


def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return 0
        return float(r.json()["price"])
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

    target_symbols = [c["symbol"] for c in market]

    # SELL coins no longer in top list
    for symbol in list(positions.keys()):
        if symbol not in target_symbols:
            price = get_price(symbol)
            cash += positions[symbol]["qty"] * price
            del positions[symbol]
            total_trades += 1

    equity = current_equity()
    deploy_capital = equity * DEPLOYMENT_RATIO
    allocation_per_coin = deploy_capital / len(target_symbols)

    for coin in market:
        symbol = coin["symbol"]
        price = float(coin["lastPrice"])

        if allocation_per_coin < MIN_TRADE_SIZE:
            continue

        if symbol in positions:
            continue

        if cash >= allocation_per_coin:
            qty = allocation_per_coin / price
            positions[symbol] = {
                "qty": qty,
                "entry": price
            }
            cash -= allocation_per_coin
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
            <td>{symbol.replace("USDT","")}</td>
            <td>{round(pos["qty"], 6)}</td>
            <td>${round(value, 2)}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
    <style>
        body {{
            background-color: #0e1a2b;
            color: #e6edf3;
            font-family: Arial;
            padding: 20px;
        }}
        .card {{
            background: #1f2a3c;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
        }}
        th {{
            background: #2d3a4f;
        }}
    </style>
    </head>
    <body>

    <h2 style="color:#4fd1c5;">ELITE AI TRADER</h2>

    <div class="card">
        <b>Market Deployment:</b> {round(deployment,2)}%<br>
        <b>Cash:</b> ${round(cash,2)}<br>
        <b>Invested:</b> ${round(invested,2)}<br>
        <b>Total Equity:</b> ${round(equity,2)}<br>
        <b>Total Trades:</b> {total_trades}
    </div>

    <div class="card">
        <h3>Positions</h3>
        <table>
            <tr>
                <th>Coin</th>
                <th>Quantity</th>
                <th>Value</th>
            </tr>
            {rows}
        </table>
    </div>

    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)