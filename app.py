from flask import Flask, jsonify, render_template_string
import threading
import requests
import time
import statistics
import random
from collections import deque
import math

app = Flask(__name__)

START_BALANCE = 50.0
BOT_COUNT = 8
ROTATION_INTERVAL = 300  # 5 minutes
PRICE_REFRESH = 15

price_data = {}
coin_scores = {}
active_coins = []
price_history = {}
volume_history = {}
lock = threading.Lock()


# ============================
# Bot Class
# ============================

class TradingBot:
    def __init__(self, name, aggressive=False):
        self.name = name
        self.balance = START_BALANCE
        self.positions = {}
        self.wins = 0
        self.losses = 0
        self.aggressive = aggressive

        if aggressive:
            self.entry_threshold = random.uniform(0.04, 0.06)
            self.take_profit = random.uniform(0.06, 0.10)
            self.stop_loss = random.uniform(0.03, 0.06)
            self.position_size = random.uniform(0.35, 0.60)
        else:
            self.entry_threshold = random.uniform(0.02, 0.03)
            self.take_profit = random.uniform(0.03, 0.04)
            self.stop_loss = random.uniform(0.015, 0.025)
            self.position_size = random.uniform(0.20, 0.30)

    def evaluate(self):
        for coin in active_coins:
            if coin not in price_history or len(price_history[coin]) < 20:
                continue

            prices = list(price_history[coin])
            current_price = prices[-1]
            mean_price = statistics.mean(prices)
            deviation = (current_price - mean_price) / mean_price

            # Entry
            if coin not in self.positions:
                if deviation <= -self.entry_threshold:
                    allocation = self.balance * self.position_size
                    if allocation > 1:
                        self.balance -= allocation
                        self.positions[coin] = {
                            "entry": current_price,
                            "amount": allocation / current_price
                        }

            # Exit
            else:
                entry = self.positions[coin]["entry"]
                change = (current_price - entry) / entry

                if change >= self.take_profit:
                    self.balance += self.positions[coin]["amount"] * current_price
                    self.wins += 1
                    del self.positions[coin]

                elif change <= -self.stop_loss:
                    self.balance += self.positions[coin]["amount"] * current_price
                    self.losses += 1
                    del self.positions[coin]

    def adapt(self):
        total_trades = self.wins + self.losses
        if total_trades < 3:
            return

        win_rate = self.wins / total_trades

        if win_rate > 0.6:
            self.position_size = min(self.position_size * 1.05, 0.75)
            self.take_profit *= 1.05
        elif win_rate < 0.4:
            self.position_size = max(self.position_size * 0.90, 0.10)
            self.stop_loss *= 0.95
            self.entry_threshold *= 0.95


# ============================
# Market Data Engine
# ============================

def fetch_market():
    global active_coins

    while True:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 100,
                    "page": 1,
                },
                timeout=10
            )
            data = r.json()

            with lock:
                for coin in data:
                    symbol = coin["symbol"].upper()
                    price = coin["current_price"]
                    volume = coin["total_volume"]

                    if symbol not in price_history:
                        price_history[symbol] = deque(maxlen=50)
                        volume_history[symbol] = deque(maxlen=50)

                    price_history[symbol].append(price)
                    volume_history[symbol].append(volume)
                    price_data[symbol] = price

                score_coins()

        except:
            pass

        time.sleep(PRICE_REFRESH)


def score_coins():
    global active_coins

    scores = {}

    for symbol in price_history:
        if len(price_history[symbol]) < 20:
            continue

        prices = list(price_history[symbol])
        volumes = list(volume_history[symbol])

        returns = [(prices[i] - prices[i - 1]) / prices[i - 1]
                   for i in range(1, len(prices))]

        volatility = statistics.stdev(returns) if len(returns) > 2 else 0
        momentum = (prices[-1] - prices[0]) / prices[0]
        slope = (prices[-1] - prices[-5]) / prices[-5] if len(prices) > 5 else 0
        volume_expansion = volumes[-1] / (statistics.mean(volumes) + 1)

        score = (
            0.30 * volatility +
            0.30 * momentum +
            0.20 * slope +
            0.20 * volume_expansion
        )

        scores[symbol] = score

    sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    active_coins = [c[0] for c in sorted_coins[:30]]
    coin_scores.update(scores)


# ============================
# Bot Engine Loop
# ============================

bots = []

for i in range(4):
    bots.append(TradingBot(f"Conservative {i+1}", aggressive=False))

for i in range(4):
    bots.append(TradingBot(f"Aggressive {i+1}", aggressive=True))


def bot_loop():
    last_adapt = time.time()

    while True:
        with lock:
            for bot in bots:
                bot.evaluate()

        if time.time() - last_adapt > ROTATION_INTERVAL:
            for bot in bots:
                bot.adapt()
            last_adapt = time.time()

        time.sleep(2)


# ============================
# Dashboard
# ============================

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Elite Adaptive Trading Engine</title>
        <style>
            body { background:#0e1117; color:white; font-family:Arial; padding:20px; }
            table { border-collapse:collapse; width:100%; margin-bottom:20px; }
            th, td { padding:6px; border:1px solid #222; }
            th { background:#161b22; }
            .bot { border:1px solid #333; padding:15px; margin:10px 0; border-radius:8px; }
        </style>
    </head>
    <body>
        <h1>Elite Adaptive Trading Engine</h1>

        <h2>Active Coins</h2>
        <table>
            <tr>
                <th>Symbol</th>
                <th>Price</th>
                <th>Score</th>
            </tr>
            {% for coin in coins %}
            <tr>
                <td>{{ coin }}</td>
                <td>${{ prices.get(coin, 0) }}</td>
                <td>{{ "%.4f"|format(scores.get(coin, 0)) }}</td>
            </tr>
            {% endfor %}
        </table>

        <h2>Bots</h2>
        {% for bot in bots %}
        <div class="bot">
            <strong>{{ bot.name }}</strong><br>
            Balance: ${{ "%.2f"|format(bot.balance) }}<br>
            Wins: {{ bot.wins }} | Losses: {{ bot.losses }}<br>
            Entry: {{ "%.2f"|format(bot.entry_threshold*100) }}% |
            TP: {{ "%.2f"|format(bot.take_profit*100) }}% |
            SL: {{ "%.2f"|format(bot.stop_loss*100) }}% |
            Size: {{ "%.2f"|format(bot.position_size*100) }}%<br>
            Holdings:
            {% for c in bot.positions %}
                {{ c }} 
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """, bots=bots, coins=active_coins, prices=price_data, scores=coin_scores)


# ============================
# Start Threads
# ============================

threading.Thread(target=fetch_market, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)