from flask import Flask, render_template
from datetime import datetime
import random

app = Flask(__name__)

# ------------------------
# Generate Random Score
# ------------------------
def generate_score():
    return round(random.uniform(-100, 100), 2)

# ------------------------
# Determine Market Regime
# ------------------------
def determine_regime(coins):
    avg_score = sum(c["score"] for c in coins) / len(coins)

    if avg_score > 10:
        return "BULL"
    elif avg_score < -10:
        return "BEAR"
    else:
        return "SIDEWAYS"

# ------------------------
# Signal Logic
# ------------------------
def generate_signal(score, regime):

    if regime == "BULL":
        if score > 30:
            return "BUY", "High"
        elif score > 10:
            return "BUY", "Medium"
        else:
            return "HOLD", "Low"

    elif regime == "BEAR":
        if score < -30:
            return "SELL", "High"
        elif score < -10:
            return "SELL", "Medium"
        else:
            return "HOLD", "Low"

    return "HOLD", "Low"

# ------------------------
# Trade Plan Builder
# ------------------------
def build_trade_plan(price, signal):

    price = float(price)

    if signal == "BUY":
        stop_loss = round(price * 0.97, 2)
        take_profit = round(price * 1.06, 2)
        risk = "2%"
        size = "Full"

    elif signal == "SELL":
        stop_loss = round(price * 1.03, 2)
        take_profit = round(price * 0.94, 2)
        risk = "2%"
        size = "Reduced"

    else:
        stop_loss = "-"
        take_profit = "-"
        risk = "-"
        size = "-"

    return stop_loss, take_profit, risk, size


@app.route("/")
def home():

    coins_raw = [
        ("BTC", 66937.6),
        ("ETH", 2005.35),
        ("SOL", 85.43),
        ("XRP", 1.4),
        ("ADA", 0.29),
        ("AVAX", 9.27),
        ("DOT", 1.6),
        ("LINK", 9.01),
        ("LTC", 55.43),
        ("BCH", 476.84),
    ]

    coins = []

    # First pass: generate scores
    for name, price in coins_raw:
        score = generate_score()
        coins.append({
            "coin": name,
            "price": price,
            "score": score
        })

    # Determine regime
    regime = determine_regime(coins)

    # Second pass: generate signals + trade plans
    for coin in coins:
        signal, confidence = generate_signal(coin["score"], regime)
        stop_loss, take_profit, risk, size = build_trade_plan(coin["price"], signal)

        coin["signal"] = signal
        coin["confidence"] = confidence
        coin["stop_loss"] = stop_loss
        coin["take_profit"] = take_profit
        coin["risk"] = risk
        coin["size"] = size

    return render_template(
        "index.html",
        coins=coins,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        regime=regime
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)