from flask import Flask, render_template_string
import requests
import random
import threading
import time

app = Flask(__name__)

SYMBOLS = ["BTCUSDT"]
START_BALANCE = 50.0
TRADE_PERCENT = 2
TRADE_SIZE = 0.25

prices = {}
last_update = "Loading..."
bots = []

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
            threshold = TRADE_PERCENT * self.learning_bias

            if change <= -threshold and self.balance > 5:
                amount = self.balance * TRADE_SIZE
                qty = amount / current_price
                self.balance -= amount
                self.coins[symbol] = self.coins.get(symbol, 0) + qty
                self.learning_bias *= 0.99

            if change >= threshold and symbol in self.coins:
                qty = self.coins[symbol]
                self.balance += qty * current_price
                self.coins[symbol] = 0
                self.learning_bias *= 1.01

            self.last_prices[symbol] = current_price

def fetch_prices():
    global prices, last_update
    while True:
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=5)
            data = response.json()
            prices["BTCUSDT"] = float(data["price"])
            last_update = time.strftime("%H:%M:%S")
        except:
            pass
        time.sleep(5)

def bot_loop():
    while True:
        for bot in bots:
            bot.update()
        time.sleep(10)

for i in range(4):
    bots.append(TradingBot(f"Bot {i+1}"))

threading.Thread(target=fetch_prices, daemon=True).start()
threading.Thread(target=bot_loop, daemon=True).start()

@app.route("/")
def dashboard():
    btc_price = prices.get("BTCUSDT", "Loading...")
    return render_template_string("""
    <html>
    <head>
        <title>Alpha Engine</title>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background:#111; color:white; font-family:Arial; padding:20px; }
            .btc { font-size:28px; margin-bottom:20px; }
            .bot { border:1px solid #333; padding:15px; margin-bottom:15px; border-radius:8px; }
        </style>
    </head>
    <body>

        <h1>🚀 Structured Alpha Engine</h1>

        <div class="btc">
            <strong>BTC Live Price:</strong>
            ${{ btc_price if btc_price == "Loading..." else "%.2f"|format(btc_price) }}
            <br>
            <small>Last update: {{ last_update }}</small>
        </div>

        <h2>Trading Bots</h2>

        {% for bot in bots %}
        <div class="bot">
            <h3>{{ bot.name }}</h3>
            <p>Balance: ${{ "%.2f"|format(bot.balance) }}</p>
            <p>Learning Bias: {{ "%.3f"|format(bot.learning_bias) }}</p>
            <p>Holdings:</p>
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
    """, bots=bots, btc_price=btc_price, last_update=last_update)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)