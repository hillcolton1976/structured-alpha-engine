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
MOMENTUM_THRESHOLD = 0.002  # 0.2% momentum trigger

COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "ripple",
    "dogecoin"
]

# ================= STATE =================
balance = START_BALANCE
positions = {}
price_history = {coin: deque(maxlen=HISTORY) for coin in COINS}
last_prices = {}
lock = threading.Lock()

# ================= FETCH PRICES =================
def fetch_prices():
    global last_prices
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(COINS)}&vs_currencies=usd"
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200:
            data = r.json()
            for coin in COINS:
                if coin in data:
                    price = data[coin]["usd"]
                    last_prices[coin] = price
                    price_history[coin].append(price)
    except Exception as e:
        print("API Error:", e)

# ================= MOMENTUM =================
def get_momentum(coin):
    hist = price_history[coin]
    if len(hist) < HISTORY:
        return 0
    return (hist[-1] - hist[0]) / hist[0]

# ================= TRADE ENGINE =================
def trade_engine():
    global balance

    while True:
        with lock:
            fetch_prices()

            for coin in COINS:
                if coin not in last_prices:
                    continue

                price = last_prices[coin]
                momentum = get_momentum(coin)

                # ENTER LONG
                if momentum > MOMENTUM_THRESHOLD and coin not in positions:
                    trade_size = balance * TRADE_SIZE_PERCENT
                    if trade_size > 1:
                        positions[coin] = {
                            "type": "long",
                            "entry": price,
                            "size": trade_size
                        }
                        balance -= trade_size

                # ENTER SHORT
                elif momentum < -MOMENTUM_THRESHOLD and coin not in positions:
                    trade_size = balance * TRADE_SIZE_PERCENT
                    if trade_size > 1:
                        positions[coin] = {
                            "type": "short",
                            "entry": price,
                            "size": trade_size
                        }
                        balance -= trade_size

                # EXIT LONG
                if coin in positions and positions[coin]["type"] == "long":
                    if momentum < 0:
                        entry = positions[coin]["entry"]
                        size = positions[coin]["size"]
                        pnl = size * ((price - entry) / entry)
                        balance += size + pnl
                        del positions[coin]

                # EXIT SHORT
                if coin in positions and positions[coin]["type"] == "short":
                    if momentum > 0:
                        entry = positions[coin]["entry"]
                        size = positions[coin]["size"]
                        pnl = size * ((entry - price) / entry)
                        balance += size + pnl
                        del positions[coin]

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
                        <th>Price</th>
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