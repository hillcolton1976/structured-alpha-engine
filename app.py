from flask import Flask, render_template, request, redirect
from datetime import datetime

app = Flask(__name__)

# Simple in-memory simulator stats
balance = 50
wins = 0
losses = 0

@app.route("/", methods=["GET", "POST"])
def dashboard():
    global balance, wins, losses

    # Handle simulator buttons
    if request.method == "POST":
        result = request.form.get("result")

        if result == "win":
            balance += 5
            wins += 1
        elif result == "loss":
            balance -= 5
            losses += 1

        return redirect("/")

    # ===== Swing Setup Logic =====
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    price = 1.55
    risk_percent = 0.05
    risk_amount = balance * risk_percent
    stop_loss = round(price * 0.97, 2)
    take_profit = round(price * 1.06, 2)
    position_size = round(risk_amount / (price - stop_loss), 2)

    setup = {
        "coin": "DOT",
        "price": price,
        "score": 70,
        "signal": "BUY",
        "entry": price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "position_size": position_size
    }

    total_trades = wins + losses
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    return render_template(
        "dashboard.html",
        updated=updated,
        balance=balance,
        setup=setup,
        wins=wins,
        losses=losses,
        win_rate=win_rate
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)