from flask import Flask, render_template_string
import requests
import os
from collections import deque

app = Flask(__name__)

START_BALANCE = 50.0
TRADE_SIZE_PERCENT = 0.25
HISTORY = 20
MOMENTUM_THRESHOLD = 0.002

COINS = ["bitcoin", "ethereum", "solana", "ripple", "dogecoin"]

balance = START_BALANCE
positions = {}
price_history = {coin: deque(maxlen=HISTORY) for coin in COINS}

def fetch_prices():
    prices = {}
    try:
        r = requests.get("https://api.coincap.io/v2/assets", timeout=5)
        data = r.json()["data"]

        for coin in COINS:
            for asset in data:
                if asset["id"] == coin:
                    price = float(asset["priceUsd"])
                    prices[coin.upper()] = round(price, 4)
                    price_history[coin].append(price)
                    break
    except Exception as e:
        print("API error:", e)

    return prices

def get_momentum(coin):
    hist = price_history[coin]
    if len(hist) < HISTORY:
        return 0
    return (hist[-1] - hist[0]) / hist[0]

def trade(prices):
    global balance

    for coin in COINS:
        symbol = coin.upper()

        if symbol not in prices:
            continue

        price = prices[symbol]
        momentum = get_momentum(coin)

        if momentum > MOMENTUM_THRESHOLD and symbol not in positions:
            size = balance * TRADE_SIZE_PERCENT
            if size > 1:
                positions[symbol] = {"type": "long", "entry": price, "size": size}
                balance -= size

        elif momentum < -MOMENTUM_THRESHOLD and symbol not in positions:
            size = balance * TRADE_SIZE_PERCENT
            if size > 1:
                positions[symbol] = {"type": "short", "entry": price, "size": size}
                balance -= size

        if symbol in positions:
            entry = positions[symbol]["entry"]
            size = positions[symbol]["size"]

            if positions[symbol]["type"] == "long" and momentum < 0:
                pnl = size * ((price - entry) / entry)
                balance += size + pnl
                del positions[symbol]

            elif positions[symbol]["type"] == "short" and momentum > 0:
                pnl = size * ((entry - price) / entry)
                balance += size + pnl
                del positions[symbol]

@app.route("/")
def home():
    prices = fetch_prices()
    trade(prices)

    return render_template_string("""
    <html>
    <head>
        <title>Momentum Engine</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background:#0e1117; color:#e6edf3; font-family:Arial; padding:20px; }
            h1 { color:#58a6ff; }
            .card { background:#161b22; padding:15px; margin-bottom:20px; border-radius:10px; }
            table { width:100%; border-collapse:collapse; }
            th, td { padding:8px; }
            th { border-bottom:1px solid #30363d; }
            tr { border-bottom:1px solid #21262d; }
            .green { color:#3fb950; }
            .red { color:#f85149; }
        </style>
    </head>
    <body>

        <h1>🚀 Dual Momentum Bot</h1>

        <div class="card">
            <h3>Balance: ${{balance}}</h3>
        </div>

        <div class="card">
            <h3>Open Positions</h3>
            {% if positions %}
            <table>
                <tr><th>Coin</th><th>Type</th><th>Entry</th></tr>
                {% for coin, pos in positions.items() %}
                <tr>
                    <td>{{coin}}</td>
                    <td class="{{ 'green' if pos.type=='long' else 'red' }}">{{pos.type}}</td>
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
                <tr><th>Coin</th><th>Price (USD)</th></tr>
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