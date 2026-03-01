import requests
from flask import Flask
import random

app = Flask(__name__)

# =========================
# SIM STATE
# =========================

START_BALANCE = 50.0

cash = START_BALANCE
positions = {}
trades = 0
wins = 0
losses = 0
entry_threshold = 0.0020  # Adaptive entry trigger


# =========================
# SAFE BINANCE FETCH
# =========================

def get_top_pairs(limit=35):
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()

        if not isinstance(data, list):
            return []

        usdt_pairs = [
            x for x in data
            if isinstance(x, dict)
            and "symbol" in x
            and x["symbol"].endswith("USDT")
        ]

        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x.get("quoteVolume", 0)),
            reverse=True
        )

        return sorted_pairs[:limit]

    except Exception:
        return []


# =========================
# PRICE FETCH
# =========================

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data["price"])
    except Exception:
        return None


# =========================
# SIMPLE ADAPTIVE LOGIC
# =========================

def maybe_trade(symbol, price):
    global cash, positions, trades, wins, losses, entry_threshold

    # Random micro "AI score"
    score = random.uniform(0, 0.01)

    if symbol not in positions and score > entry_threshold and cash > 5:
        allocation = cash * 0.25
        qty = allocation / price
        positions[symbol] = {
            "entry": price,
            "qty": qty
        }
        cash -= allocation
        trades += 1

    elif symbol in positions:
        entry = positions[symbol]["entry"]
        qty = positions[symbol]["qty"]
        pnl_pct = (price - entry) / entry

        if pnl_pct > 0.01 or pnl_pct < -0.01:
            value = qty * price
            cash += value
            if pnl_pct > 0:
                wins += 1
                entry_threshold *= 1.01
            else:
                losses += 1
                entry_threshold *= 0.99
            del positions[symbol]


# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    global cash, positions

    coins = get_top_pairs(35)

    market_rows = ""
    position_rows = ""

    total_positions_value = 0
    unrealized_pl = 0

    # Market Table
    for coin in coins:
        symbol = coin["symbol"]
        price = float(coin["lastPrice"])
        change = float(coin["priceChangePercent"])

        maybe_trade(symbol, price)

        market_rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${price:.6f}</td>
            <td>{change:.2f}%</td>
        </tr>
        """

    # Position Table
    if positions:
        for symbol, data in positions.items():
            current_price = get_price(symbol)
            if current_price is None:
                continue

            qty = data["qty"]
            entry = data["entry"]
            value = qty * current_price
            pnl = value - (qty * entry)

            total_positions_value += value
            unrealized_pl += pnl

            position_rows += f"""
            <tr>
                <td>{symbol}</td>
                <td>{qty:.4f}</td>
                <td>${entry:.6f}</td>
                <td>${value:.2f}</td>
                <td>${pnl:.2f}</td>
            </tr>
            """
    else:
        position_rows = """
        <tr>
            <td colspan="5">No open positions</td>
        </tr>
        """

    total_equity = cash + total_positions_value

    return f"""
    <html>
    <head>
        <title>ELITE AI TRADER v3.1</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body {{
                background: #0b132b;
                color: white;
                font-family: Arial;
                padding: 20px;
            }}
            .card {{
                background: #1c2541;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 8px;
                border-bottom: 1px solid #3a506b;
                text-align: left;
            }}
        </style>
    </head>
    <body>

        <h2>🔥 ELITE AI TRADER v3.1</h2>

        <div class="card">
            <h3>Account</h3>
            <p>Cash: ${cash:.2f}</p>
            <p>Positions Value: ${total_positions_value:.2f}</p>
            <p><b>Total Equity: ${total_equity:.2f}</b></p>
            <p>Unrealized P/L: ${unrealized_pl:.2f}</p>
        </div>

        <div class="card">
            <h3>Stats</h3>
            <p>Trades: {trades}</p>
            <p>Wins: {wins}</p>
            <p>Losses: {losses}</p>
            <p>Adaptive Threshold: {entry_threshold:.4f}</p>
        </div>

        <div class="card">
            <h3>Open Positions</h3>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Value ($)</th>
                    <th>P/L</th>
                </tr>
                {position_rows}
            </table>
        </div>

        <div class="card">
            <h3>Top 35 USDT Pairs</h3>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Price</th>
                    <th>24h %</th>
                </tr>
                {market_rows}
            </table>
        </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)