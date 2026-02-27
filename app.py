from flask import Flask, render_template
from datetime import datetime
import requests

app = Flask(__name__)

COIN_COUNT = 75


# -----------------------------
# MARKET REGIME DETECTION
# -----------------------------
def get_market_regime():
    url = "https://api.coingecko.com/api/v3/global"
    data = requests.get(url, timeout=10).json()
    change = data["data"]["market_cap_change_percentage_24h_usd"]

    if change > 1:
        return "BULL"
    elif change < -1:
        return "BEAR"
    else:
        return "NEUTRAL"


# -----------------------------
# MARKET DATA
# -----------------------------
def get_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": COIN_COUNT,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h,7d"
    }

    response = requests.get(url, params=params, timeout=15)
    return response.json()


# -----------------------------
# SCORING ENGINE (0–100)
# -----------------------------
def score_coin(coin):
    score = 50  # start neutral

    c1h = coin.get("price_change_percentage_1h_in_currency", 0) or 0
    c24h = coin.get("price_change_percentage_24h_in_currency", 0) or 0
    c7d = coin.get("price_change_percentage_7d_in_currency", 0) or 0

    volume = coin.get("total_volume", 0)
    market_cap = coin.get("market_cap", 1)
    volume_ratio = volume / market_cap if market_cap > 0 else 0

    # Momentum boosts
    score += c1h * 1.5
    score += c24h * 1.2
    score += c7d * 0.5

    # Volume strength boost
    if volume_ratio > 0.05:
        score += 10
    elif volume_ratio < 0.01:
        score -= 10

    # Clamp score
    score = max(0, min(100, round(score)))

    # Signal logic
    if score >= 70:
        signal = "STRONG BUY"
    elif score >= 60:
        signal = "BUY"
    elif score <= 30:
        signal = "STRONG SELL"
    elif score <= 40:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Risk logic
    if abs(c24h) > 8:
        risk = "HIGH"
    elif abs(c24h) > 4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "symbol": coin["symbol"].upper(),
        "price": round(coin["current_price"], 4),
        "score": score,
        "signal": signal,
        "risk": risk,
        "change_24h": round(c24h, 2),
        "volume_ratio": round(volume_ratio * 100, 2)
    }


# -----------------------------
# ROUTE
# -----------------------------
@app.route("/")
def home():
    regime = get_market_regime()
    coins = get_market_data()

    results = [score_coin(c) for c in coins]
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    top = [r for r in results if r["score"] >= 60][:10]

    return render_template(
        "index.html",
        top=top,
        results=results,
        regime=regime,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)