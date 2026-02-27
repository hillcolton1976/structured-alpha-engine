from flask import Flask, render_template, request, redirect
from datetime import datetime

app = Flask(__name__)

# ---- SIM SETTINGS ----
START_BALANCE = 50
RISK_PERCENT = 0.02      # 2% risk
REWARD_MULTIPLIER = 2    # 2R reward

# ---- GLOBAL STATE (simple version) ----
balance = START_BALANCE
wins = 0
losses = 0

@app.route("/", methods=["GET", "POST"])
def home():
    global balance, wins, losses

    if request.method == "POST":
        result = request.form.get("result")

        risk_amount = balance * RISK_PERCENT
        reward_amount = risk_amount * REWARD_MULTIPLIER

        if result == "win":
            balance += reward_amount
            wins += 1
        elif result == "loss":
            balance -= risk_amount
            losses += 1

        return redirect("/")

    total_trades = wins + losses
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return render_template(
        "sim.html",
        updated=updated,
        balance=round(balance, 2),
        wins=wins,
        losses=losses,
        win_rate=win_rate
    )

if __name__ == "__main__":
    app.run(debug=True)