from flask import Flask, render_template_string
import random
import threading
import time

app = Flask(__name__)

START_BALANCE = 50.0
bots = []

class TradingBot:
    def __init__(self, name):
        self.name = name
        self.balance = START_BALANCE
        self.learning_bias = random.uniform(0.8, 1.2)
        self.trades = 0

    def update(self):
        # simple simulated learning drift
        self.learning_bias *= random.uniform(0.999, 1.001)

def bot_loop():
    while True:
        for bot in bots:
            bot.update()
        time.sleep(5)

for i in range(4):
    bots.append(TradingBot(f"Bot {i+1}"))

threading.Thread(target=bot_loop, daemon=True).start()

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Structured Alpha Engine</title>
        <style>
            body { background:#0f1117; color:white; font-family:Arial; padding:20px; }
            .price { font-size:48px; font-weight:bold; transition:0.2s; }
            .green { color:#00ff88; }
            .red { color:#ff4d4d; }
            .bot { border:1px solid #222; padding:15px; margin-top:15px; border-radius:8px; }
        </style>
    </head>
    <body>

        <h1>🚀 Structured Alpha Engine</h1>

        <h2>BTC/USDT Live</h2>
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
            const priceEl = document.getElementById("btc");
            let lastPrice = null;

            const ws = new WebSocket("wss://stream.binance.com:9443/ws/btcusdt@trade");

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const price = parseFloat(data.p);
                priceEl.innerText = "$" + price.toFixed(2);

                if (lastPrice) {
                    if (price > lastPrice) {
                        priceEl.classList.remove("red");
                        priceEl.classList.add("green");
                    } else if (price < lastPrice) {
                        priceEl.classList.remove("green");
                        priceEl.classList.add("red");
                    }
                }

                lastPrice = price;
            };

            ws.onerror = function() {
                priceEl.innerText = "Connection Error";
            };
        </script>

    </body>
    </html>
    """, bots=bots)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)