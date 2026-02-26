from flask import Flask, jsonify
import requests
from datetime import datetime

app = Flask(__name__)

KRAKEN_API = "https://api.kraken.com/0/public/Ticker"

PAIRS = {
    "XRP": "XRPUSD",
    "SOL": "SOLUSD",
    "PEPE": "PEPEUSD",
    "SHIB": "SHIBUSD",
    "COQ": "COQUSD"
}

def get_market_data():
    pairs_string = ",".join(PAIRS.values())
    response = requests.get(f"{KRAKEN_API}?pair={pairs_string}")
    data = response.json().get("result", {})

    results = []

    for coin, pair in PAIRS.items():
        if pair not in data:
            continue

        ticker = data[pair]

        price = float(ticker["c"][0])              # last trade
        vwap_24h = float(ticker["p"][1])           # 24h VWAP
        volume_24h = float(ticker["v"][1])         # 24h volume
        low_24h = float(ticker["l"][1])
        high_24h = float(ticker["h"][1])

        # --- Calculate 24h % change ---
        change_percent = ((price - vwap_24h) / vwap_24h) * 100

        score = 0

        # Momentum
        if change_percent > 2:
            score += 2
        elif change_percent < -2:
            score -= 2

        # Trend vs VWAP
        if price > vwap_24h:
            score += 1
        else:
            score -= 1

        # Position in daily range
        range_position = (price - low_24h) / (high_24h - low_24h + 1e-9)
        if range_position > 0.75:
            score += 1
        elif range_position < 0.25:
            score -= 1

        # Volume strength
        if volume_24h > 1_000_000:
            score += 1

        # --- Action Mapping ---
        if score >= 4:
            action = "STRONG BUY"
        elif score >= 2:
            action = "BUY"
        elif score <= -4:
            action = "STRONG SELL"
        elif score <= -2:
            action = "SELL"
        else:
            action = "HOLD"

        results.append({
            "coin": coin,
            "pair": pair,
            "price": price,
            "change_24h_percent": round(change_percent, 2),
            "volume_24h": volume_24h,
            "score": score,
            "action": action
        })

    return results


@app.route("/")
def home():
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "market": get_market_data()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)