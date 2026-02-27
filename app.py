from flask import Flask, render_template
from datetime import datetime
import random

app = Flask(__name__)

# ===== ACCOUNT STAGES =====
def account_stage(balance):
    if balance < 200:
        return "Stage 1: $50 → $200 (Aggressive Growth)"
    elif balance < 1000:
        return "Stage 2: $200 → $1,000 (Structured Growth)"
    else:
        return "Stage 3: $1,000+ (Capital Preservation)"

# ===== SWING SIGNAL ENGINE =====
def swing_signal(score):
    if score > 60:
        return "BUY"
    elif score < -60:
        return "SELL"
    else:
        return "NO TRADE"

# ===== TRADE PLAN =====
def trade_plan(price, signal, balance):
    risk_percent = 0.05 if balance < 200 else 0.03

    if signal == "BUY":
        entry = round(price, 2)
        take_profit = round(price * 1.10, 2)
        stop_loss = round(price * 0.94, 2)
        position_size = round(balance * risk_percent, 2)
    elif signal == "SELL":
        entry = round(price, 2)
        take_profit = round(price * 0.90, 2)
        stop_loss = round(price * 1.06, 2)
        position_size = round(balance * risk_percent, 2)
    else:
        entry = "-"
        take_profit = "-"
        stop_loss = "-"
        position_size = "-"

    return entry, take_profit, stop_loss, position_size

@app.route("/")
def home():

    balance = 50  # starting balance
    stage = account_stage(balance)

    coins = [
        ("BTC", 67000),
        ("ETH", 2000),
        ("SOL", 90),
        ("XRP", 0.55),
        ("ADA", 0.35),
        ("AVAX", 28),
        ("LINK", 15),
        ("LTC", 70),
        ("BCH", 450),
    ]

    scored = []

    for name, price in coins:
        score = random.uniform(-100, 100)
        scored.append((name, price, score))

    # Pick strongest swing only
    best = max(scored, key=lambda x: abs(x[2]))
    symbol, price, score = best

    signal = swing_signal(score)
    entry, tp, sl, size = trade_plan(price, signal, balance)

    return render_template(
        "index.html",
        symbol=symbol,
        price=price,
        score=round(score, 2),
        signal=signal,
        entry=entry,
        take_profit=tp,
        stop_loss=sl,
        size=size,
        balance=balance,
        stage=stage,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

if __name__ == "__main__":
    app.run(debug=True)