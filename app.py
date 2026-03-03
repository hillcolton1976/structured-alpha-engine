from flask import Flask, render_template_string
import threading
import requests
import time
import os
from collections import deque

app = Flask(__name__)

# ================= SETTINGS =================
START_BALANCE = 50.0
TRADE_SIZE_PERCENT = 0.25
PRICE_REFRESH = 5
HISTORY = 20
MOMENTUM_THRESHOLD = 0.002  # 0.2%

# Binance trading pairs
COINS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT"
}

# ================= STATE =================
balance = START_BALANCE
positions = {}
price_history = {symbol: deque(maxlen=HISTORY) for symbol in COINS}
last_prices = {}
lock = threading.Lock()

# ================= FETCH PRICES FROM BINANCE =================
def fetch_prices():
    try:
        for symbol, pair in COINS.items():
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                data = r.json()
                price = float(data["price"])
                last_prices[symbol] = price
                price_history[symbol].append(price)

    except Exception as e:
        print("API Error:", e)

# ================= MOMENTUM =================
def get_momentum(symbol):
    hist = price_history[symbol]
    if len(hist) < HISTORY:
        return 0
    return (hist[-1] - hist[0]) / hist[0]

# ================= TRADE ENGINE =================
def trade_engine():
    global balance

    while True:
        with lock:
            fetch_prices()

            for symbol in COINS.keys():
                if symbol not in last_prices:
                    continue

                price = last_prices[symbol]
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

        time.sleep(PRICE_REFRESH)

# ================= UI =================
@app.route("/")
def home():
    with lock:
        return render_template_string("""
        <html>
        <head>
            <title>Dual Momentum Engine</title>
            <meta http-equiv="refresh" content="4">
            <style>
                body {
                    background: #0e1117;
                    color: #e6edf3;
                    font-family: Arial, sans-serif;
                    padding: 20px;
                }
                h1 {
                    color: #58a6ff;
                }
                .card {
                    background: #161b22;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.4);
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                }
                th {
                    color: #8b949e;
                    border-bottom: 1px solid #30363d;
                }
                tr {
                    border-bottom: 1px solid #21262d;
                }
                .green { color: #3fb950; }
                .red { color: #f85149; }
                .balance {
                    font-size: 22px;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>

            <h1>🚀 Dual Momentum Trading Bot</h1>

            <div class="card">
                <div class="balance">Balance: ${{balance}}</div>
            </div>

            <div class="card">
                <h3>📈 Open Positions</h3>
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
                <h3>💰 Live Prices</h3>
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
        """, balance=round(balance,2), positions=positions, prices=last_prices)

# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=trade_engine, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)