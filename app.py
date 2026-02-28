import requests
import threading
import time
import statistics
from flask import Flask, render_template_string

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

START_BALANCE = 50.0
MAX_COINS = 20
PRICE_HISTORY_LENGTH = 25
SLEEP_TIME = 1  # Fast loop

balance = START_BALANCE
equity = START_BALANCE
wins = 0
losses = 0
trades = 0
aggression = 0.25

open_positions = {}
recent_signals = []
price_history = {}

# ==============================
# FETCH TOP 20 USDT COINS
# ==============================

def get_top_pairs():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url, timeout=5).json()
    usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [x["symbol"] for x in sorted_pairs[:MAX_COINS]]

coins = get_top_pairs()

# ==============================
# TRADING LOGIC
# ==============================

def trader():
    global balance, equity, wins, losses, trades, aggression

    while True:
        try:
            prices = {}
            for coin in coins:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={coin}"
                data = requests.get(url, timeout=3).json()
                prices[coin] = float(data["price"])

            equity = balance

            for coin, price in prices.items():
                if coin not in price_history:
                    price_history[coin] = []

                price_history[coin].append(price)

                if len(price_history[coin]) > PRICE_HISTORY_LENGTH:
                    price_history[coin].pop(0)

                if len(price_history[coin]) < 10:
                    continue

                history = price_history[coin]
                momentum = (history[-1] - history[-5]) / history[-5]
                volatility = statistics.stdev(history[-10:]) / history[-1]

                # ===== BUY CONDITION (Adaptive)
                if coin not in open_positions:
                    if momentum > 0.002:

                        position_size = balance * aggression
                        if position_size < 5:
                            continue

                        qty = position_size / price
                        balance -= position_size
                        open_positions[coin] = {
                            "entry": price,
                            "qty": qty
                        }

                        recent_signals.insert(0, f"🚀 BUY {coin} @ {round(price,4)}")
                        recent_signals[:] = recent_signals[:10]

                # ===== SELL CONDITION
                if coin in open_positions:
                    entry = open_positions[coin]["entry"]
                    qty = open_positions[coin]["qty"]
                    pnl_pct = (price - entry) / entry

                    take_profit = 0.01 + (volatility * 1.5)
                    stop_loss = -0.008

                    if pnl_pct > take_profit or pnl_pct < stop_loss:

                        pnl = qty * (price - entry)
                        balance += qty * price
                        equity = balance
                        trades += 1

                        if pnl > 0:
                            wins += 1
                            aggression = min(0.50, aggression + 0.03)
                        else:
                            losses += 1
                            aggression = max(0.10, aggression - 0.05)

                        recent_signals.insert(0, f"SELL {coin} @ {round(price,4)} | PnL: {round(pnl,2)}")
                        recent_signals[:] = recent_signals[:10]

                        del open_positions[coin]

                # Update equity with unrealized PnL
                if coin in open_positions:
                    entry = open_positions[coin]["entry"]
                    qty = open_positions[coin]["qty"]
                    equity += qty * (price - entry)

        except:
            pass

        time.sleep(SLEEP_TIME)

# Start background trader
threading.Thread(target=trader, daemon=True).start()

# ==============================
# UI
# ==============================

@app.route("/")
def dashboard():
    win_rate = round((wins / trades) * 100, 2) if trades > 0 else 0

    return render_template_string("""
    <html>
    <head>
    <title>Adaptive AI Trader Pro</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: white;
    }
    .container {
        padding: 20px;
    }
    h1 {
        color: #ff9f43;
    }
    .card {
        background: rgba(255,255,255,0.08);
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 10px;
    }
    .green { color: #4cd137; }
    .red { color: #e84118; }
    </style>
    </head>
    <body>
    <div class="container">
        <h1>🔥 Adaptive AI Trader PRO</h1>

        <div class="card">
            <h2>Account</h2>
            <p><b>Equity:</b> ${{ equity }}</p>
            <p><b>Balance:</b> ${{ balance }}</p>
            <p><b>Trades:</b> {{ trades }}</p>
            <p class="green"><b>Wins:</b> {{ wins }}</p>
            <p class="red"><b>Losses:</b> {{ losses }}</p>
            <p><b>Win Rate:</b> {{ win_rate }}%</p>
            <p><b>Aggression:</b> {{ aggression }}%</p>
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            {% if open_positions %}
                {% for coin in open_positions %}
                    <p>{{ coin }}</p>
                {% endfor %}
            {% else %}
                <p>None</p>
            {% endif %}
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {% for signal in recent_signals %}
                <p>{{ signal }}</p>
            {% endfor %}
        </div>

    </div>
    </body>
    </html>
    """,
    balance=round(balance,2),
    equity=round(equity,2),
    trades=trades,
    wins=wins,
    losses=losses,
    win_rate=win_rate,
    aggression=round(aggression*100,1),
    open_positions=open_positions,
    recent_signals=recent_signals)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)