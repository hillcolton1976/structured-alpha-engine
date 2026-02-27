from flask import Flask, render_template
from datetime import datetime
import requests

app = Flask(__name__)

COIN_COUNT = 75


def get_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": COIN_COUNT,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h"
    }

    response = requests.get(url, params=params, timeout=15)
    return response.json()


def score_coin(coin):
    score = 0

    change_1h = coin.get("price_change_percentage_1h_in_currency", 0) or 0
    change_24h = coin.get("price_change_percentage_24h_in_currency", 0) or 0
    volume = coin.get("total_volume", 0)
    market_cap = coin.get("market_cap", 1)

    # Momentum scoring
    if change_1h > 0:
        score += 1
    else:
        score -= 1

    if change_24h > 0:
        score += 1
    else:
        score -= 1

    # Volume strength
    volume_ratio = volume / market_cap if market_cap > 0 else 0
    if volume_ratio > 0.05:
        score += 1

    if score >= 2:
        signal = "BUY"
    elif score <= -2:
        signal = "SELL"
    else:
        signal = "HOLD"

    return {
        "symbol": coin["symbol"].upper(),
        "price": round(coin["current_price"], 4),
        "signal": signal,
        "score": score,
        "change_1h": round(change_1h, 2),
        "change_24h": round(change_24h, 2),
        "volume_ratio": round(volume_ratio * 100, 2)
    }


@app.route("/")
def home():
    coins = get_market_data()
    results = []

    for coin in coins:
        results.append(score_coin(coin))

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    top = results[:10]

    return render_template(
        "index.html",
        top=top,
        results=results,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)