from flask import Flask, render_template
import requests
from datetime import datetime

app = Flask(__name__)

def get_price(pair="DOTUSD"):
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    r = requests.get(url)
    data = r.json()
    result = list(data["result"].values())[0]
    return float(result["c"][0])  # last trade price

@app.route("/")
def home():
    balance = 50
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # === REAL PRICE ===
    price = get_price("DOTUSD")

    # === SIMPLE 4H TREND LOGIC ===
    # Basic structure: bullish bias if price > 50 EMA placeholder
    # For now we simulate structure with a simple rule
    signal = "BUY" if price > 1 else "SELL"

    # === RISK SETTINGS ===
    risk_percent = 0.05
    reward_ratio = 2

    risk_amount = balance * risk_percent
    stop_loss = round(price * 0.97, 4)
    take_profit = round(price + (price - stop_loss) * reward_ratio, 4)

    position_size = round(risk_amount / (price - stop_loss), 2)

    setup = {
        "coin": "DOT",
        "price": round(price, 4),
        "score": 70,
        "signal": signal,
        "entry": round(price, 4),
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "position_size": position_size
    }

    return render_template(
        "dashboard.html",
        updated=updated,
        balance=balance,
        setup=setup
    )

if __name__ == "__main__":
    app.run(debug=True)