from flask import Flask, render_template_string
import threading
import requests
import time
import statistics
import random
from collections import deque

app = Flask(__name__)

START_BALANCE = 50.0
PRICE_REFRESH = 10
HISTORY_LENGTH = 12

price_data = {}
price_history = {}
active_coins = []
lock = threading.Lock()


# =========================
# BOT
# =========================

class TradingBot:
    def __init__(self, name, aggressive=False):
        self.name = name
        self.balance = START_BALANCE
        self.positions = {}
        self.wins = 0
        self.losses = 0

        if aggressive:
            self.entry_threshold = random.uniform(0.03, 0.05)
            self.take_profit = random.uniform(0.05, 0.08)
            self.stop_loss = random.uniform(0.03, 0.05)
            self.position_size = random.uniform(0.40, 0.60)
        else:
            self.entry_threshold = random.uniform(0.015, 0.03)
            self.take_profit = random.uniform(0.02, 0.04)
            self.stop_loss = random.uniform(0.015, 0.03)
            self.position_size = random.uniform(0.20, 0.35)

    def evaluate(self):
        for coin in list(active_coins):

            if coin not in price_history:
                continue
            if len(price_history[coin]) < 5:
                continue

            prices = list(price_history[coin])
            current = prices[-1]
            avg = statistics.mean(prices)
            deviation = (current - avg) / avg

            # ENTRY
            if coin not in self.positions:
                if deviation <= -self.entry_threshold:
                    allocation = self.balance * self.position_size
                    if allocation > 1:
                        self.balance -= allocation
                        self.positions[coin] = {
                            "entry": current,
                            "amount": allocation / current
                        }

            # EXIT
            else:
                entry = self.positions[coin]["entry"]
                change = (current - entry) / entry

                if change >= self.take_profit:
                    self.balance += self.positions[coin]["amount"] * current
                    self.wins += 1
                    del self.positions[coin]

                elif change <= -self.stop_loss:
                    self.balance += self.positions[coin]["amount"] * current
                    self.losses += 1
                    del self.positions[coin]


# =========================
# MARKET FETCH (SAFE)
# =========================

def fetch_market():
    global active_coins

    while True:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 20,
                    "page": 1,
                },
                timeout=10
            )

            if r.status_code != 200:
                print("Bad status:", r.status_code)
                time.sleep(PRICE_REFRESH)
                continue

            data = r.json()

            if not isinstance(data, list) or len(data) == 0:
                print("Empty response")
                time.sleep(PRICE_REFRESH)
                continue

            with lock:
                new_coins = []

                for coin in data:
                    symbol = coin["symbol"].upper()
                    price = coin["current_price"]

                    new_coins.append(symbol)
                    price_data[symbol] = price

                    if symbol not in price_history:
                        price_history[symbol] = deque(maxlen=HISTORY_LENGTH)

                    price_history[symbol].append(price)

                # Only replace if we got valid data
                active_coins[:] = new_coins

        except Exception as e:
            print("API error:", e)

        time.sleep(PRICE_REFRESH)


# =========================
# BOT LOOP
# =========================

bots = []

for i in range(4):
    bots.append(TradingBot(f"Conservative {i+1}", aggressive=False))

for i in range(4):
    bots.append(TradingBot(f"Aggressive {i+1}", aggressive=True))


def bot_loop():
    while True:
        with lock:
            for bot in bots:
                bot.evaluate()
        time.sleep(2)


# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Elite Adaptive Trading Engine</title>
        <meta http-equiv="refresh" content="5">
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
            </tr>
            {% for coin in coins %}
            <tr>
                <td>{{ coin }}</td>
                <td>${{ prices.get(coin, 0) }}</td>
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
    """, bots=bots, coins=active_coins, prices=price_data)


# =========================
# START
# =========================

threading.Thread(target=fetch_market, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)