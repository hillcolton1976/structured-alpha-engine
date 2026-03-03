from flask import Flask, render_template_string
import requests
import random
import threading
import time

app = Flask(__name__)

# ===== CONFIG =====
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
START_BALANCE = 50.0
TRADE_PERCENT = 2  # % move required to trade
TRADE_SIZE = 0.25  # 25% of balance per trade

# ===== GLOBAL STATE =====
prices = {}
bots = []

# ===== BOT CLASS =====
class TradingBot:
    def __init__(self, name):
        self.name = name
        self.balance = START_BALANCE
        self.coins = {}
        self.last_prices = {}
        self.learning_bias = random.uniform(0.8, 1.2)

    def update(self):
        global prices

        for symbol in SYMBOLS:
            if symbol not in prices:
                continue

            current_price = prices[symbol]

            if symbol not in self.last_prices:
                self.last_prices[symbol] = current_price
                continue

            change = ((current_price - self.last_prices[symbol]) / self.last_prices[symbol]) * 100

            adjusted_threshold = TRADE_PERCENT * self.learning_bias

            # BUY
            if change <= -adjusted_threshold and self.balance > 5:
                amount_to_spend = self.balance * TRADE_SIZE
                quantity = amount_to_spend / current_price
                self.balance -= amount_to_spend
                self.coins[symbol] = self.coins.get(symbol, 0) + quantity
                self.learning_bias *= 0.99

            # SELL
            if change >= adjusted_threshold and symbol in self.coins:
                quantity = self.coins[symbol]
                self.balance += quantity * current_price
                self.coins[symbol] = 0
                self.learning_bias *= 1.01

            self.last_prices[symbol] = current_price


# ===== PRICE FETCHER =====
def fetch_prices():
    global prices
    while True:
        try:
            for symbol in SYMBOLS:
                url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                response = requests.get(url, timeout=5)
                data = response.json()
                prices[symbol] = float(data["price"])
        except:
            pass

        time.sleep(5)


# ===== BOT LOOP =====
def bot_loop():
    while True:
        for bot in bots:
            bot.update()
        time.sleep(10)


# ===== INITIALIZE =====
for i in range(4):
    bots.append(TradingBot(f"Bot {i+1}"))

threading.Thread(target=fetch_prices, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()


# ===== DASHBOARD =====
@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Alpha Engine Dashboard</title>
        <meta http-equiv="refresh" content="10">
        <style>
            body { font-family: Arial; background: #111; color: white; padding: 20px; }
            .price { font-size: 18px; margin-bottom: 10px; }
            .bot { border: 1px solid #333; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
            h2 { margin-bottom: 5px; }
        </style>
    </head>
    <body>

        <h1>🚀 Structured Alpha Engine</h1>

        <h2>Live Prices</h2>
        {% for symbol, price in prices.items() %}
            <div class="price">{{ symbol }}: ${{ "%.2f"|format(price) }}</div>
        {% endfor %}

        <hr>

        <h2>Trading Bots</h2>

        {% for bot in bots %}
            <div class="bot">
                <h3>{{ bot.name }}</h3>
                <p><strong>Balance:</strong> ${{ "%.2f"|format(bot.balance) }}</p>
                <p><strong>Learning Bias:</strong> {{ "%.3f"|format(bot.learning_bias) }}</p>
                <p><strong>Holdings:</strong></p>
                <ul>
                    {% for coin, qty in bot.coins.items() %}
                        {% if qty > 0 %}
                            <li>{{ coin }} - {{ "%.6f"|format(qty) }}</li>
                        {% endif %}
                    {% endfor %}
                </ul>
            </div>
        {% endfor %}

    </body>
    </html>
    """, prices=prices, bots=bots)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)