from flask import Flask, render_template_string
import requests
import time
import os
from collections import deque

app = Flask(__name__)

START_BALANCE = 50.0
TRADE_SIZE_PERCENT = 0.25
HISTORY = 20
MOMENTUM_THRESHOLD = 0.002

COINS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT"
}

balance = START_BALANCE
positions = {}
price_history = {symbol: deque(maxlen=HISTORY) for symbol in COINS}

# ================= FETCH BINANCE PRICES =================
def fetch_prices():
    prices = {}
    for symbol, pair in COINS.items():
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                data = r.json()
                price = float(data["price"])
                prices[symbol] = price
                price_history[symbol].append(price)
        except:
            prices[symbol] = "API Error"

    return prices

# ================= MOMENTUM =================
def get_momentum(symbol):
    hist = price_history[symbol]
    if len(hist) < HISTORY:
        return 0
    return (hist[-1] - hist[0]) / hist[0]

# ================= TRADE LOGIC =================
def trade(prices):
    global balance

    for symbol, price in prices.items():
        if isinstance(price, str):
            continue

        momentum = get_momentum(symbol)

        # ENTER LONG
        if momentum > MOMENTUM_THRESHOLD and symbol not in positions:
            trade_size = balance * TRADE_SIZE_PERCENT
            if trade_size > 1:
                positions[symbol] = {
                    "type": "long",
                    "entry": price,
                    "size": trade_size
                }
                balance -= trade_size

        # ENTER SHORT
        elif momentum < -MOMENTUM_THRESHOLD and symbol not in positions:
            trade_size = balance * TRADE_SIZE_PERCENT
            if trade_size > 1:
                positions[symbol] = {
                    "type": "short",
                    "entry": price,
                    "size": trade_size
                }
                balance -= trade_size

        # EXIT LONG
        if symbol in positions and positions[symbol]["type"] == "long":
            if momentum < 0:
                entry = positions[symbol]["entry"]
                size = positions[symbol]["size"]
                pnl = size * ((price - entry) / entry)
                balance += size + pnl
                del positions[symbol]

        # EXIT SHORT
        if symbol in positions and positions[symbol]["type"] == "short":
            if momentum > 0:
                entry = positions[symbol]["entry"]
                size = positions[symbol]["size"]
                pnl = size * ((entry - price) / entry)
                balance += size + pnl
                del positions[symbol]

# ================= UI =================
@app.route("/")
def home():
    prices = fetch_prices()
    trade(prices)

    return render_template_string("""
    <html>
    <head>
        <title>Dual Momentum Engine</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body {
                background: #0e1117;
                color: #e6edf3;
                font-family: Arial, sans-serif;
                padding: 20px;
            }
            h1 { color: #58a6ff; }
            .card {
                background: #161b22;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 10px;
            }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 8px; }
            th { border-bottom: 1px solid #30363d; }
            tr { border-bottom: 1px solid #21262d; }
            .green { color: #3fb950; }
            .red { color: #f85149; }
        </style>
    </head>
    <body>

        <h1>🚀 Dual Momentum Trading Bot</h1>

        <div class="card">
            <h3>Balance: ${{balance}}</h3>
        </div>

        <div class="card">
            <h3>Open Positions</h3>
            {% if positions %}
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Type</th>
                    <th>Entry</th>
                </tr>
                {% for coin, pos in positions.items() %}
                <tr>
                    <td>{{coin}}</td>
                    <td class="{{ 'green' if pos.type == 'long' else 'red' }}">
                        {{pos.type}}
                    </td>
                    <td>${{pos.entry}}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <p>No open positions</p>
            {% endif %}
        </div>

        <div class="card">
            <h3>Live Prices</h3>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Price (USDT)</th>
                </tr>
                {% for coin, price in prices.items() %}
                <tr>
                    <td>{{coin}}</td>
                    <td>${{price}}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

    </body>
    </html>
    """, balance=round(balance,2), positions=positions, prices=prices)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)