from flask import Flask, render_template
import random
from datetime import datetime

app = Flask(__name__)

# --- Fake market data (replace later with Kraken API if wanted) ---
coins = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC", "BCH"]

def generate_swing_setup():
    coin = random.choice(coins)
    price = round(random.uniform(20, 300), 2)

    entry = price
    take_profit = round(price * 1.10, 2)     # 10% target
    stop_loss = round(price * 0.94, 2)       # 6% risk
    position_size = 5                       # Risk controlled for $50 account

    return {
        "coin": coin,
        "price": price,
        "entry": entry,
        "tp": take_profit,
        "sl": stop_loss,
        "size": position_size,
        "score": round(random.uniform(70, 95), 2),
        "signal": "BUY"
    }

@app.route("/")
def swing():
    setup = generate_swing_setup()

    return render_template(
        "swing.html",
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        balance=50,
        stage="Stage 1: $50 → $200 (Aggressive Growth)",
        setup=setup
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)