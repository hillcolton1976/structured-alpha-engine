from flask import Flask, render_template
from datetime import datetime
import random

app = Flask(__name__)

def generate_signal(score):
    if score > 50:
        return "BUY", "High"
    elif score > 10:
        return "BUY", "Medium"
    elif score > -10:
        return "HOLD", "Medium"
    elif score > -30:
        return "SELL", "Medium"
    else:
        return "SELL", "High"

def build_trade_plan(price, signal):
    price = float(price)

    if signal == "BUY":
        entry = round(price, 2)
        take_profit = round(price * 1.08, 2)
        risk = "2%"
        size = "Full"
    elif signal == "SELL":
        entry = round(price, 2)
        take_profit = round(price * 0.92, 2)
        risk = "2%"
        size = "Reduced"
    else:
        entry = "-"
        take_profit = "-"
        risk = "-"
        size = "-"

    return entry, take_profit, risk, size

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

    for name, price in coins_raw:
        score = round(random.uniform(-100, 100), 2)
        signal, confidence = generate_signal(score)
        entry, take_profit, risk, size = build_trade_plan(price, signal)

        coins.append({
            "coin": name,
            "price": price,
            "score": score,
            "signal": signal,
            "confidence": confidence,
            "entry": entry,
            "take_profit": take_profit,
            "risk": risk,
            "size": size
        })

    regime = "BULL" if sum(c["score"] for c in coins) > 0 else "BEAR"

    return render_template(
        "index.html",
        coins=coins,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        regime=regime
    )

if __name__ == "__main__":
    app.run(debug=True)