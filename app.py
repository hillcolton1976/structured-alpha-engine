from flask import Flask, render_template
from datetime import datetime
import random
import os

app = Flask(__name__)

# -----------------------------
# SIGNAL ENGINE
# -----------------------------

def generate_signal():
    alignment = random.randint(-3, 3)

    if alignment >= 2:
        signal = "BUY"
    elif alignment <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    rsi = round(random.uniform(20, 80), 1)

    return signal, alignment, rsi


# -----------------------------
# PORTFOLIO SIM ENGINE
# -----------------------------

def run_portfolio_sim(start_balance=50):

    balance = start_balance
    wins = 0
    losses = 0
    max_balance = balance
    max_drawdown = 0

    target = 200 if balance < 200 else 1000

    while balance < target:

        risk = balance * 0.02
        reward = risk * 1.8

        win = random.random() < 0.47

        if win:
            balance += reward
            wins += 1
        else:
            balance -= risk
            losses += 1

        max_balance = max(max_balance, balance)
        drawdown = (max_balance - balance) / max_balance
        max_drawdown = max(max_drawdown, drawdown)

        if balance <= 0:
            break

    return {
        "start": start_balance,
        "end": round(balance, 2),
        "wins": wins,
        "losses": losses,
        "winrate": round((wins / (wins + losses)) * 100, 1) if (wins + losses) > 0 else 0,
        "drawdown": round(max_drawdown * 100, 2),
        "target": target
    }


# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def home():

    coins = ["BTC","ETH","SOL","XRP","ADA","AVAX","DOT","LINK","LTC","BCH"]

    results = []

    for coin in coins:
        price = round(random.uniform(0.5, 70000), 2)
        signal, alignment, rsi = generate_signal()

        results.append({
            "symbol": coin,
            "price": price,
            "signal": signal,
            "alignment": alignment,
            "rsi": rsi
        })

    sim = run_portfolio_sim(50)

    return render_template(
        "index.html",
        results=results,
        sim=sim,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


# REQUIRED FOR RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)