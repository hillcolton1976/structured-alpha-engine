from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def swing():

    # ===== ACCOUNT SETTINGS =====
    balance = 50  # Starting account
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # ===== MOCK MARKET DATA (Safe For Now) =====
    coin = "DOT"
    price = 284.15
    score = 87.96
    signal = "BUY"

    # ===== RISK MODEL =====
    risk_percent = 0.05      # Risk 5% per trade
    reward_ratio = 2         # 2R target
    stop_distance_percent = 0.03  # 3% stop

    risk_amount = balance * risk_percent

    stop_loss = round(price - (price * stop_distance_percent), 2)
    risk_per_unit = price - stop_loss
    take_profit = round(price + (risk_per_unit * reward_ratio), 2)

    # Avoid division error
    if risk_per_unit == 0:
        position_size = 0
    else:
        position_size = round(risk_amount / risk_per_unit, 2)

    # ===== SETUP OBJECT =====
    setup = {
        "coin": coin,
        "price": price,
        "score": score,
        "signal": signal,
        "entry": price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "position_size": position_size
    }

    stage = "Stage 1: $50 → $200 (Aggressive Growth)"

    return render_template(
        "swing.html",
        updated=updated,
        balance=balance,
        stage=stage,
        setup=setup
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)