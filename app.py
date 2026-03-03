from flask import Flask, jsonify, render_template_string
import threading
import requests
import time
import random

app = Flask(__name__)

START_BALANCE = 50.0
MAX_POSITIONS = 5

market_data = {}
price_history = {}
bots = []

# -------------------------
# MARKET ENGINE
# -------------------------

def fetch_top_30():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 30,
        "page": 1
    }
    r = requests.get(url, params=params, timeout=10)
    data = r.json()
    return [coin["id"] for coin in data]


def market_loop():
    global market_data
    coins = fetch_top_30()

    while True:
        try:
            ids = ",".join(coins)
            r = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd",
                timeout=10
            )
            prices = r.json()

            for coin in coins:
                if coin in prices:
                    price = prices[coin]["usd"]
                    market_data[coin] = price

                    if coin not in price_history:
                        price_history[coin] = []

                    price_history[coin].append(price)

                    if len(price_history[coin]) > 50:
                        price_history[coin].pop(0)

        except:
            pass

        time.sleep(5)

# -------------------------
# BOT ENGINE
# -------------------------

class TradingBot:

    def __init__(self, name, risk_profile):
        self.name = name
        self.risk = risk_profile
        self.balance = START_BALANCE
        self.positions = {}
        self.wins = 0
        self.losses = 0

        if risk_profile == "conservative":
            self.base_risk = 0.12
        else:
            self.base_risk = 0.35

        self.dip_threshold = 0.03
        self.take_profit = 0.02

    def equity(self):
        total = self.balance
        for coin, entry in self.positions.items():
            if coin in market_data:
                total += entry["size"] * market_data[coin]
        return total

    def trade(self):

        for coin, prices in price_history.items():

            if len(prices) < 10:
                continue

            current = prices[-1]
            recent_high = max(prices)
            recent_low = min(prices)

            # --- BUY DIP ---
            if coin not in self.positions and len(self.positions) < MAX_POSITIONS:

                drop_pct = (recent_high - current) / recent_high

                if drop_pct >= self.dip_threshold:

                    size_usd = self.balance * self.base_risk
                    if size_usd <= 1:
                        continue

                    quantity = size_usd / current
                    self.balance -= size_usd

                    self.positions[coin] = {
                        "entry": current,
                        "size": quantity
                    }

            # --- SELL ---
            if coin in self.positions:

                entry_price = self.positions[coin]["entry"]
                change_pct = (current - entry_price) / entry_price

                if change_pct >= self.take_profit or change_pct <= -self.dip_threshold:

                    size = self.positions[coin]["size"]
                    self.balance += size * current

                    if change_pct > 0:
                        self.wins += 1
                        self.dip_threshold *= 0.98
                    else:
                        self.losses += 1
                        self.dip_threshold *= 1.02

                    del self.positions[coin]


def bot_loop():
    while True:
        for bot in bots:
            bot.trade()
        time.sleep(3)

# -------------------------
# INITIALIZE 8 BOTS
# -------------------------

for i in range(4):
    bots.append(TradingBot(f"Conservative {i+1}", "conservative"))

for i in range(4):
    bots.append(TradingBot(f"Aggressive {i+1}", "aggressive"))

threading.Thread(target=market_loop, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()

# -------------------------
# DASHBOARD
# -------------------------

@app.route("/")
def dashboard():

    leaderboard = sorted(bots, key=lambda b: b.equity(), reverse=True)

    return render_template_string("""
    <html>
    <head>
        <style>
            body { background:#0f1117; color:white; font-family:Arial; padding:20px;}
            table { width:100%; border-collapse:collapse; }
            th, td { padding:8px; border-bottom:1px solid #222; text-align:left;}
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
                <th>Equity</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>Open Positions</th>
            </tr>
            {% for bot in leaderboard %}
            <tr>
                <td>{{ bot.name }}</td>
                <td>{{ bot.risk }}</td>
                <td>${{ "%.2f"|format(bot.balance) }}</td>
                <td>${{ "%.2f"|format(bot.equity()) }}</td>
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
                for (const coin in data) {
                    html += coin + ": $" + data[coin] + "<br>";
                }
                document.getElementById("prices").innerHTML = html;
            }

            setInterval(updatePrices, 5000);
            updatePrices();
        </script>

    </body>
    </html>
    """, leaderboard=leaderboard)


@app.route("/prices")
def prices():
    return jsonify(market_data)


# -------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)