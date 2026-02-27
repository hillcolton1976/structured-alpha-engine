from flask import Flask, render_template
import random

app = Flask(__name__)

START_BALANCE = 50
WIN_RATE = 0.52
RISK_PERCENT = 0.05
RR = 2

LEVELS = [
    (200, "Stage 2"),
    (1000, "Stage 3"),
    (5000, "Stage 4")
]

def simulate():

    balance = START_BALANCE
    trades = 0
    wins = 0
    losses = 0
    max_balance = balance
    max_drawdown = 0
    stage = "Stage 1"

    trade_log = []

    while balance < 5000 and trades < 1000:

        risk_amount = balance * RISK_PERCENT

        if random.random() < WIN_RATE:
            profit = risk_amount * RR
            balance += profit
            wins += 1
            result = "WIN"
        else:
            balance -= risk_amount
            losses += 1
            result = "LOSS"

        trades += 1

        if balance > max_balance:
            max_balance = balance

        drawdown = (max_balance - balance) / max_balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown

        for level, name in LEVELS:
            if balance >= level:
                stage = name

        trade_log.append({
            "trade": trades,
            "result": result,
            "balance": round(balance, 2)
        })

        if balance <= 0:
            break

    win_rate_actual = (wins / trades) * 100 if trades > 0 else 0

    return {
        "balance": round(balance, 2),
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate_actual, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "stage": stage,
        "trade_log": trade_log[-20:]
    }

@app.route("/")
def home():
    results = simulate()
    return render_template("sim.html", **results)

if __name__ == "__main__":
    app.run(debug=True)