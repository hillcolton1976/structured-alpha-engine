import os
import time
import threading
import statistics
import requests
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

TOP_30 = []
price_history = {}
bots = []
MAX_POSITIONS = 5


# ===============================
# LOAD TOP 30 COINS
# ===============================

def load_top_30():
    global TOP_30, price_history

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 30,
        "page": 1,
    }

    try:
        data = requests.get(url, params=params, timeout=10).json()
        TOP_30 = [coin["id"] for coin in data]
        price_history = {coin: [] for coin in TOP_30}
    except:
        TOP_30 = []
        price_history = {}


# ===============================
# PRICE LOOP
# ===============================

def price_loop():
    while True:
        try:
            if not TOP_30:
                time.sleep(5)
                continue

            ids = ",".join(TOP_30)
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
            data = requests.get(url, timeout=10).json()

            for coin in TOP_30:
                price = data.get(coin, {}).get("usd")
                if price:
                    price_history[coin].append(price)
                    if len(price_history[coin]) > 100:
                        price_history[coin].pop(0)

        except:
            pass

        time.sleep(5)


# ===============================
# TRADING BOT
# ===============================

class TradingBot:

    def __init__(self, name, strategy, risk):
        self.name = name
        self.strategy = strategy
        self.risk = risk
        self.balance = 50.0
        self.positions = {}
        self.wins = 0
        self.losses = 0
        self.base_size = 0.25

    def enter(self, coin, price):
        if len(self.positions) >= MAX_POSITIONS:
            return

        size = self.balance * self.base_size
        if size < 1:
            return

        qty = size / price
        self.balance -= size

        self.positions[coin] = {
            "entry": price,
            "qty": qty,
        }

    def exit(self, coin, price):
        position = self.positions.pop(coin)
        entry = position["entry"]
        qty = position["qty"]

        value = qty * price
        self.balance += value

        if price > entry:
            self.wins += 1
        else:
            self.losses += 1

    def evaluate(self):

        # manage open trades
        for coin in list(self.positions.keys()):
            history = price_history.get(coin, [])
            if len(history) < 20:
                continue

            entry_price = self.positions[coin]["entry"]
            current_price = history[-1]
            change = (current_price - entry_price) / entry_price * 100

            if self.risk == "conservative":
                take_profit = 3
                stop_loss = -2
            else:
                take_profit = 6
                stop_loss = -4

            if change >= take_profit or change <= stop_loss:
                self.exit(coin, current_price)

        # scan for new trades
        for coin in TOP_30:
            if coin in self.positions:
                continue

            history = price_history.get(coin, [])
            if len(history) < 20:
                continue

            current = history[-1]
            average = statistics.mean(history[-20:])
            deviation = (current - average) / average * 100

            if self.strategy == "mean_reversion":
                trigger = -2 if self.risk == "conservative" else -4
                if deviation <= trigger:
                    self.enter(coin, current)

            elif self.strategy == "momentum":
                trigger = 2 if self.risk == "conservative" else 4
                if deviation >= trigger:
                    self.enter(coin, current)


# ===============================
# BOT LOOP
# ===============================

def bot_loop():
    while True:
        for bot in bots:
            bot.evaluate()
        time.sleep(5)


# ===============================
# INITIALIZE
# ===============================

load_top_30()

bots.append(TradingBot("Conservative 1", "mean_reversion", "conservative"))
bots.append(TradingBot("Conservative 2", "momentum", "conservative"))
bots.append(TradingBot("Conservative 3", "mean_reversion", "conservative"))
bots.append(TradingBot("Conservative 4", "momentum", "conservative"))
bots.append(TradingBot("Aggressive 1", "mean_reversion", "aggressive"))
bots.append(TradingBot("Aggressive 2", "momentum", "aggressive"))
bots.append(TradingBot("Aggressive 3", "mean_reversion", "aggressive"))
bots.append(TradingBot("Aggressive 4", "momentum", "aggressive"))

threading.Thread(target=price_loop, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()


# ===============================
# DASHBOARD
# ===============================

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>8 Bot Adaptive Trading Engine</title>
        <style>
            body { background:#0f1117; color:white; font-family:Arial; padding:20px; }
            table { width:100%; border-collapse:collapse; margin-top:20px; }
            th, td { padding:8px; border-bottom:1px solid #222; text-align:left; }
            th { color:#888; }
        </style>
    </head>
    <body>

        <h1>🚀 8 Bot Adaptive Trading Engine</h1>

        <h2>Top 30 Live Prices</h2>
        <div id="prices"></div>

        <h2>Bot Leaderboard</h2>
        <table>
            <tr>
                <th>Name</th>
                <th>Risk</th>
                <th>Balance</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Open Positions</th>
            </tr>
            {% for bot in bots %}
            <tr>
                <td>{{ bot.name }}</td>
                <td>{{ bot.risk }}</td>
                <td>${{ "%.2f"|format(bot.balance) }}</td>
                <td>{{ bot.wins }}</td>
                <td>{{ bot.losses }}</td>
                <td>{{ bot.positions|length }}</td>
            </tr>
            {% endfor %}
        </table>

        <script>
        async function updatePrices() {
            const res = await fetch("/prices");
            const data = await res.json();

            let html = "";
            for (let coin in data) {
                html += `<div>${coin.toUpperCase()} - $${data[coin]}</div>`;
            }
            document.getElementById("prices").innerHTML = html;
        }

        setInterval(updatePrices, 5000);
        updatePrices();
        </script>

    </body>
    </html>
    """, bots=bots)


@app.route("/prices")
def prices():
    latest = {}
    for coin in TOP_30:
        history = price_history.get(coin, [])
        if history:
            latest[coin] = history[-1]
    return jsonify(latest)


# ===============================
# RUN (Local Only)
# ===============================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)