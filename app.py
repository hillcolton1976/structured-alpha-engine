from flask import Flask, jsonify, render_template_string
import threading
import requests
import time
import statistics

app = Flask(__name__)

START_BALANCE = 50.0
TOP_30 = []
price_history = {}
MAX_HISTORY = 120
MAX_POSITIONS = 3
bots = []

# ===============================
# LOAD TOP 30 COINS
# ===============================

def load_top_30():
    global TOP_30
    r = requests.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 30,
            "page": 1,
            "sparkline": False
        },
        timeout=10
    )
    data = r.json()
    TOP_30 = [coin["id"] for coin in data]

    for coin in TOP_30:
        price_history[coin] = []

# ===============================
# PRICE LOOP
# ===============================

def price_loop():
    while True:
        try:
            ids = ",".join(TOP_30)
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": ids, "vs_currencies": "usd"},
                timeout=10
            )
            data = r.json()

            for coin in TOP_30:
                if coin in data:
                    price = data[coin]["usd"]
                    history = price_history[coin]
                    history.append(price)

                    if len(history) > MAX_HISTORY:
                        history.pop(0)

        except:
            pass

        time.sleep(5)

# ===============================
# BOT CLASS
# ===============================

class TradingBot:
    def __init__(self, name, strategy, risk):
        self.name = name
        self.strategy = strategy
        self.risk = risk
        self.balance = START_BALANCE
        self.positions = {}
        self.wins = 0
        self.losses = 0

        if risk == "conservative":
            self.base_size = 0.10
        else:
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
            "qty": qty
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
        for coin in list(self.positions.keys()):
            history = price_history[coin]
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

        for coin in TOP_30:
            if coin in self.positions:
                continue

            history = price_history[coin]
            if len(history) < 20:
                continue

            current = history[-1]
            average = statistics.mean(history[-20:])
            dip_percent = (current - average) / average * 100

            if self.strategy == "mean_reversion":
                trigger = -2 if self.risk == "conservative" else -4
            elif self.strategy == "momentum":
                trigger = 2 if self.risk == "conservative" else 4
            else:
                trigger = -3

            if dip_percent <= trigger:
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
# INITIALIZATION
# ===============================

load_top_30()

bots.append(TradingBot("Bot 1", "mean_reversion", "conservative"))
bots.append(TradingBot("Bot 2", "momentum", "conservative"))
bots.append(TradingBot("Bot 3", "hybrid", "conservative"))
bots.append(TradingBot("Bot 4", "mean_reversion", "conservative"))
bots.append(TradingBot("Bot 5", "mean_reversion", "aggressive"))
bots.append(TradingBot("Bot 6", "momentum", "aggressive"))
bots.append(TradingBot("Bot 7", "hybrid", "aggressive"))
bots.append(TradingBot("Bot 8", "mean_reversion", "aggressive"))

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
        <title>Alpha Engine</title>
        <style>
            body { background:#0f1117; color:white; font-family:Arial; padding:20px; }
            .price { font-size:32px; margin:5px 0; }
            .bot { border:1px solid #222; padding:15px; margin-top:15px; border-radius:8px; }
            .green { color:#00ff99; }
            .red { color:#ff4d4d; }
        </style>
        </style>
    </head>
    <body>

        <h1>🚀 Live Top 30 Market + 8 AI Bots</h1>

        <h2>Top 30 Coins (Live)</h2>
        <div id="prices"></div>

        <h2>Bot Performance</h2>
        {% for bot in bots %}
        <div class="bot">
            <h3>{{ bot.name }} ({{ bot.strategy }} / {{ bot.risk }})</h3>
            <p>Balance: ${{ "%.2f"|format(bot.balance) }}</p>
            <p>Open Positions: {{ bot.positions|length }}</p>
            <p class="green">Wins: {{ bot.wins }}</p>
            <p class="red">Losses: {{ bot.losses }}</p>
        </div>
        {% endfor %}

        <script>
        async function updatePrices() {
            const res = await fetch("/prices");
            const data = await res.json();

            let html = "";
            for (let coin in data) {
                html += `<div class="price">${coin.toUpperCase()} - $${data[coin]}</div>`;
            }

            document.getElementById("prices").innerHTML = html;
        }

        setInterval(updatePrices, 5000);
        updatePrices();
        </script>

    </body>
    </html>
    """, bots=bots)

# ===============================
# API ENDPOINT
# ===============================

@app.route("/prices")
def prices():
    latest = {}
    for coin in TOP_30:
        history = price_history[coin]
        if history:
            latest[coin] = history[-1]
    return jsonify(latest)

# ===============================
# RUN
# ===============================

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)