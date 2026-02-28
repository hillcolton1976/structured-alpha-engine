from flask import Flask, render_template_string
import requests
import threading
import time
import math

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50.0
balance = START_BALANCE
wins = 0
losses = 0
trades = 0
aggression = 0.20  # 20% starting risk
open_positions = {}
recent_signals = []

COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ATOMUSDT"
]

price_history = {coin: [] for coin in COINS}

# =============================
# MARKET DATA
# =============================

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data["price"])
    except:
        return None

# =============================
# INDICATORS
# =============================

def momentum(prices):
    if len(prices) < 5:
        return 0
    return (prices[-1] - prices[0]) / prices[0]

def volatility(prices):
    if len(prices) < 5:
        return 0.01
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    return math.sqrt(variance) / mean

# =============================
# EQUITY CALC
# =============================

def calculate_equity():
    total = balance
    for coin, pos in open_positions.items():
        current_price = get_price(coin)
        if current_price:
            unrealized = ((current_price - pos["entry"]) / pos["entry"]) * pos["size"]
            total += pos["size"] + unrealized
    return round(total, 2)

# =============================
# AI TRADER
# =============================

def trader():
    global balance, wins, losses, trades, aggression

    while True:
        for coin in COINS:

            price = get_price(coin)
            if not price:
                continue

            # Update history
            price_history[coin].append(price)
            if len(price_history[coin]) > 10:
                price_history[coin].pop(0)

            prices = price_history[coin]
            mom = momentum(prices)
            vol = volatility(prices)

            # ENTRY (aggressive momentum breakout)
            if coin not in open_positions and mom > 0.003 and vol > 0.001:

                position_size = balance * aggression
                if position_size < 5:
                    continue

                open_positions[coin] = {
                    "entry": price,
                    "size": position_size,
                    "tp": price * (1 + vol * 3),
                    "sl": price * (1 - vol * 2)
                }

                balance -= position_size
                trades += 1
                recent_signals.insert(0, f"🚀 BUY {coin} @ {round(price,2)}")

            # EXIT
            if coin in open_positions:
                pos = open_positions[coin]

                if price >= pos["tp"] or price <= pos["sl"]:

                    pnl = ((price - pos["entry"]) / pos["entry"]) * pos["size"]
                    balance += pos["size"] + pnl

                    if pnl > 0:
                        wins += 1
                        aggression = min(0.40, aggression + 0.02)
                        recent_signals.insert(0, f"✅ SELL {coin} +{round(pnl,2)}")
                    else:
                        losses += 1
                        aggression = max(0.10, aggression - 0.03)
                        recent_signals.insert(0, f"❌ SELL {coin} {round(pnl,2)}")

                    del open_positions[coin]

        time.sleep(3)

# =============================
# WEB UI
# =============================

@app.route("/")
def index():

    equity = calculate_equity()
    win_rate = round((wins / trades) * 100, 1) if trades > 0 else 0

    return render_template_string("""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta http-equiv="refresh" content="5">
        <style>
            body {
                background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                color: white;
                font-family: Arial;
                padding: 20px;
            }
            h1 { color: #ff914d; }
            .card {
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 12px;
                margin-bottom: 15px;
            }
            .green { color: #00ff99; }
            .red { color: #ff4d4d; }
        </style>
    </head>
    <body>

        <h1>🔥 Aggressive AI Trader</h1>

        <div class="card">
            <h3>Account</h3>
            <p><strong>Equity:</strong> ${{equity}}</p>
            <p>Balance: ${{balance}}</p>
            <p>Trades: {{trades}}</p>
            <p class="green">Wins: {{wins}}</p>
            <p class="red">Losses: {{losses}}</p>
            <p>Win Rate: {{win_rate}}%</p>
            <p>Aggression: {{aggression_percent}}%</p>
        </div>

        <div class="card">
            <h3>Open Positions</h3>
            {% if open_positions %}
                {% for coin, pos in open_positions.items() %}
                    <p>{{coin}} @ {{pos["entry"]}}</p>
                {% endfor %}
            {% else %}
                <p>None</p>
            {% endif %}
        </div>

        <div class="card">
            <h3>Recent Signals</h3>
            {% for s in recent_signals[:8] %}
                <p>{{s}}</p>
            {% endfor %}
        </div>

    </body>
    </html>
    """,
    equity=equity,
    balance=round(balance,2),
    trades=trades,
    wins=wins,
    losses=losses,
    win_rate=win_rate,
    aggression_percent=round(aggression*100,1),
    open_positions=open_positions,
    recent_signals=recent_signals
    )

# =============================
# START THREAD
# =============================

if __name__ == "__main__":
    t = threading.Thread(target=trader)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=5000)