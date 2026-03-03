from flask import Flask, jsonify, render_template_string
import threading
import requests
import random
import time

app = Flask(__name__)

START_BALANCE = 50.0
btc_price = None
bots = []

# ---------------------------
# Trading Bot Class
# ---------------------------

class TradingBot:
    def __init__(self, name):
        self.name = name
        self.balance = START_BALANCE
        self.learning_bias = random.uniform(0.8, 1.2)

    def update(self):
        # Simple simulated learning drift
        self.learning_bias *= random.uniform(0.999, 1.001)


# ---------------------------
# Background Bot Loop
# ---------------------------

def bot_loop():
    while True:
        for bot in bots:
            bot.update()
        time.sleep(5)


# ---------------------------
# BTC Price Polling (CoinGecko)
# ---------------------------

def price_loop():
    global btc_price
    while True:
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=5
            )
            btc_price = r.json()["bitcoin"]["usd"]
        except:
            pass
        time.sleep(2)


# ---------------------------
# Initialize Bots
# ---------------------------

for i in range(4):
    bots.append(TradingBot(f"Bot {i+1}"))

threading.Thread(target=bot_loop, daemon=True).start()
threading.Thread(target=price_loop, daemon=True).start()


# ---------------------------
# Dashboard Route
# ---------------------------

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Structured Alpha Engine</title>
        <style>
            body { background:#0f1117; color:white; font-family:Arial; padding:20px; }
            .price { font-size:48px; font-weight:bold; margin-bottom:20px; }
            .bot { border:1px solid #222; padding:15px; margin-top:15px; border-radius:8px; }
        </style>
    </head>
    <body>

        <h1>🚀 Structured Alpha Engine</h1>

        <h2>BTC/USD Live</h2>
        <div id="btc" class="price">$Loading...</div>

        <h2>Trading Bots</h2>
        {% for bot in bots %}
        <div class="bot">
            <h3>{{ bot.name }}</h3>
            <p>Balance: ${{ "%.2f"|format(bot.balance) }}</p>
            <p>Learning Bias: {{ "%.3f"|format(bot.learning_bias) }}</p>
        </div>
        {% endfor %}

        <script>
            async function updatePrice() {
                const res = await fetch("/price");
                const data = await res.json();
                if (data.price) {
                    document.getElementById("btc").innerText =
                        "$" + data.price.toLocaleString();
                }
            }

            setInterval(updatePrice, 2000);
            updatePrice();
        </script>

    </body>
    </html>
    """, bots=bots)


# ---------------------------
# Price API Endpoint
# ---------------------------

@app.route("/price")
def price():
    return jsonify({"price": btc_price})


# ---------------------------
# Run App
# ---------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)