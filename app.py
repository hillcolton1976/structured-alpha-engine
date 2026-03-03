from flask import Flask, render_template_string
import threading
import requests
import time
import os
from collections import deque

app = Flask(__name__)

START_BALANCE = 50.0
PRICE_REFRESH = 8
HISTORY_LENGTH = 12

price_data = {}
price_history = {}
active_coins = []
last_update_time = "Starting..."
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
            self.entry_threshold = 0.015     # 1.5% pullback from high
            self.take_profit = 0.04          # 4% gain
            self.stop_loss = 0.02            # 2% loss
            self.position_size = 0.60        # 60% capital
        else:
            self.entry_threshold = 0.008     # 0.8% pullback
            self.take_profit = 0.02          # 2% gain
            self.stop_loss = 0.012           # 1.2% loss
            self.position_size = 0.35        # 35% capital

    def evaluate(self):
        for coin in list(active_coins):

            if coin not in price_history:
                continue
            if len(price_history[coin]) < 5:
                continue

            prices = list(price_history[coin])
            current = prices[-1]
            recent_high = max(prices)

            # ================= ENTRY =================
            if coin not in self.positions:
                drop_from_high = (current - recent_high) / recent_high

                if drop_from_high <= -self.entry_threshold:
                    allocation = self.balance * self.position_size
                    if allocation > 1:
                        self.balance -= allocation
                        self.positions[coin] = {
                            "entry": current,
                            "amount": allocation / current
                        }

            # ================= EXIT =================
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
# MARKET FETCH
# =========================

def fetch_market():
    global active_coins, last_update_time

    while True:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "volume_desc",
                    "per_page": 20,
                    "page": 1,
                },
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()

                if isinstance(data, list) and len(data) > 0:
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

                        active_coins[:] = new_coins
                        last_update_time = time.strftime("%H:%M:%S")

        except Exception as e:
            print("API error:", e)

        time.sleep(PRICE_REFRESH)


# =========================
# BOT LOOP
# =========================

bots = []

for i in range(3):
    bots.append(TradingBot(f"Conservative {i+1}", aggressive=False))

for i in range(5):
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
        <title>Aggressive Trading Engine</title>
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
        <h1>Aggressive Pullback Trading Engine</h1>
        <p>Last Market Update: {{ last_update }}</p>

        <h2>Active Coins</h2>
        {% if coins %}
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
        {% else %}
            <p>Waiting for market data...</p>
        {% endif %}

        <h2>Bots</h2>
        {% for bot in bots %}
        <div class="bot">
            <strong>{{ bot.name }}</strong><br>
            Balance: ${{ "%.2f"|format(bot.balance) }}<br>
            Wins: {{ bot.wins }} | Losses: {{ bot.losses }}<br>
            Holdings:
            {% for c in bot.positions %}
                {{ c }}
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """, bots=bots, coins=active_coins, prices=price_data, last_update=last_update_time)


@app.route("/health")
def health():
    return "Server running"


# =========================
# START THREADS
# =========================

threading.Thread(target=fetch_market, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)