import threading
import time
import requests
import random
from flask import Flask, render_template_string

app = Flask(__name__)

# ===== SETTINGS =====
START_BALANCE = 50.0
AGGRESSION = 0.20  # 20%
SCAN_INTERVAL = 10  # seconds
TAKE_PROFIT = 0.015  # 1.5%
STOP_LOSS = 0.01  # 1%

# ===== ACCOUNT STATE =====
balance = START_BALANCE
equity = START_BALANCE
wins = 0
losses = 0
trades = 0
position = None
entry_price = 0
trade_size = 0
recent_signals = []

# ===== GET TOP USDT PAIRS =====
def get_pairs():
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
        usdt_pairs = [x["symbol"] for x in data if x["symbol"].endswith("USDT")]
        return random.sample(usdt_pairs, min(20, len(usdt_pairs)))
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

coins = get_pairs()

# ===== GET PRICE =====
def get_price(symbol):
    try:
        data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
        return float(data["price"])
    except:
        return None

# ===== AI TRADING LOOP =====
def trader():
    global balance, equity, wins, losses, trades
    global position, entry_price, trade_size, AGGRESSION

    while True:
        try:
            if position is None:
                for coin in coins:
                    price = get_price(coin)
                    if not price:
                        continue

                    # Momentum trigger (randomized breakout style)
                    if random.random() > 0.7:
                        trade_size = balance * AGGRESSION
                        if trade_size < 5:
                            continue

                        position = coin
                        entry_price = price
                        balance -= trade_size
                        recent_signals.insert(0, f"🚀 BUY {coin} @ {price:.4f}")
                        break

            else:
                price = get_price(position)
                if not price:
                    continue

                change = (price - entry_price) / entry_price

                # TAKE PROFIT
                if change >= TAKE_PROFIT:
                    profit = trade_size * change
                    balance += trade_size + profit
                    wins += 1
                    trades += 1
                    recent_signals.insert(0, f"✅ SELL {position} +{profit:.2f}")
                    position = None

                # STOP LOSS
                elif change <= -STOP_LOSS:
                    loss = trade_size * change
                    balance += trade_size + loss
                    losses += 1
                    trades += 1
                    recent_signals.insert(0, f"❌ SELL {position} {loss:.2f}")
                    position = None

                # Adaptive aggression every 10 trades
                if trades > 0 and trades % 10 == 0:
                    winrate = wins / trades
                    if winrate > 0.6:
                        AGGRESSION = min(0.35, AGGRESSION + 0.05)
                    else:
                        AGGRESSION = max(0.10, AGGRESSION - 0.05)

            equity = balance
            if position:
                price = get_price(position)
                if price:
                    unrealized = trade_size * ((price - entry_price) / entry_price)
                    equity += trade_size + unrealized

        except Exception as e:
            print("ERROR:", e)

        time.sleep(SCAN_INTERVAL)

# ===== START THREAD =====
threading.Thread(target=trader, daemon=True).start()

# ===== UI =====
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
    <title>Aggressive AI Trader</title>
    <style>
        body {
            background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
            font-family: Arial;
            color: white;
            padding: 40px;
        }
        .card {
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        h1 {
            color: orange;
        }
    </style>
    </head>
    <body>
        <h1>🔥 Aggressive AI Trader</h1>

        <div class="card">
            <h2>Account</h2>
            <p><b>Equity:</b> ${{equity}}</p>
            <p><b>Balance:</b> ${{balance}}</p>
            <p><b>Trades:</b> {{trades}}</p>
            <p><b>Wins:</b> {{wins}}</p>
            <p><b>Losses:</b> {{losses}}</p>
            <p><b>Win Rate:</b> {{winrate}}%</p>
            <p><b>Aggression:</b> {{aggression}}%</p>
        </div>

        <div class="card">
            <h2>Open Position</h2>
            <p>{{position}}</p>
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {% for s in signals %}
                <p>{{s}}</p>
            {% endfor %}
        </div>
    </body>
    </html>
    """,
    equity=round(equity,2),
    balance=round(balance,2),
    trades=trades,
    wins=wins,
    losses=losses,
    winrate=round((wins/trades*100),2) if trades>0 else 0,
    aggression=round(AGGRESSION*100,1),
    position=position if position else "None",
    signals=recent_signals[:10]
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)