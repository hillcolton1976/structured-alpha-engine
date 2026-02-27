from flask import Flask, render_template
from datetime import datetime
import requests
import math

app = Flask(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"

# -------------------------
# SIGNAL LOGIC
# -------------------------

def generate_signal(score):
    if score > 60:
        return "BUY", "High"
    elif score > 25:
        return "BUY", "Medium"
    elif score > -25:
        return "HOLD", "Low"
    elif score > -60:
        return "SELL", "Medium"
    else:
        return "SELL", "High"

def build_trade_plan(price, signal):
    price = float(price)

    if signal == "BUY":
        stop = round(price * 0.97, 2)
        take_profit = round(price * 1.08, 2)
        risk = "2%"
        size = "Full"
    elif signal == "SELL":
        stop = round(price * 1.03, 2)
        take_profit = round(price * 0.92, 2)
        risk = "2%"
        size = "Reduced"
    else:
        stop = "-"
        take_profit = "-"
        risk = "-"
        size = "-"

    return stop, take_profit, risk, size

# -------------------------
# SIMPLE MOMENTUM SCORE
# -------------------------

def calculate_score(coin):
    change_24h = coin.get("price_change_percentage_24h", 0) or 0
    change_7d = coin.get("price_change_percentage_7d_in_currency", 0) or 0
    volume = coin.get("total_volume", 0) or 0

    volume_score = math.log(volume + 1) if volume > 0 else 0

    score = (change_24h * 1.5) + (change_7d * 2) + volume_score
    return round(score, 2)

# -------------------------
# MAIN ROUTE
# -------------------------

@app.route("/")
def home():

    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 75,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "7d"
    }

    response = requests.get(COINGECKO_URL, params=params)
    data = response.json()

    coins = []

    for coin in data:
        score = calculate_score(coin)
        signal, confidence = generate_signal(score)
        stop, take_profit, risk, size = build_trade_plan(
            coin["current_price"], signal
        )

        coins.append({
            "coin": coin["symbol"].upper(),
            "price": round(coin["current_price"], 4),
            "score": score,
            "signal": signal,
            "confidence": confidence,
            "stop": stop,
            "take_profit": take_profit,
            "risk": risk,
            "size": size
        })

    # Rank by score
    coins_sorted = sorted(coins, key=lambda x: x["score"], reverse=True)

    # Only show strongest and weakest
    top_buys = [c for c in coins_sorted if c["signal"] == "BUY"][:10]
    top_sells = [c for c in reversed(coins_sorted) if c["signal"] == "SELL"][:5]

    final_coins = top_buys + top_sells

    regime = "BULL" if sum(c["score"] for c in coins) > 0 else "BEAR"

    return render_template(
        "index.html",
        coins=final_coins,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        regime=regime
    )

# -------------------------

if __name__ == "__main__":
    app.run(debug=True)