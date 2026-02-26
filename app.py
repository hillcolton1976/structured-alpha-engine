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

    try:
        response = requests.get(
            f"{KRAKEN_API}?pair={pairs_string}",
            timeout=10
        )
        response.raise_for_status()
        raw = response.json()
        data = raw.get("result", {})
    except Exception as e:
        print("Kraken API error:", e)
        return []

    results = []

    for coin, pair in PAIRS.items():

        # Kraken sometimes renames pairs internally
        matching_key = None
        for key in data.keys():
            if pair in key:
                matching_key = key
                break

        if not matching_key:
            continue

        ticker = data[matching_key]

        try:
            price = float(ticker["c"][0])
            vwap_24h = float(ticker["p"][1])
            volume_24h = float(ticker["v"][1])
            low_24h = float(ticker["l"][1])
            high_24h = float(ticker["h"][1])
        except (KeyError, ValueError):
            continue

        change_percent = ((price - vwap_24h) / vwap_24h) * 100

        score = 0

        if change_percent > 2:
            score += 2
        elif change_percent < -2:
            score -= 2

        if price > vwap_24h:
            score += 1
        else:
            score -= 1

        range_position = (price - low_24h) / (high_24h - low_24h + 1e-9)
        if range_position > 0.75:
            score += 1
        elif range_position < 0.25:
            score -= 1

        if volume_24h > 1_000_000:
            score += 1

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
            "pair": matching_key,
            "price": price,
            "change_24h_percent": round(change_percent, 2),
            "volume_24h": volume_24h,
            "score": score,
            "action": action
        })

    # Sort strongest signals first
    results.sort(key=lambda x: x["score"], reverse=True)

    return results


@app.route("/")
def home():
    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "market": get_market_data()
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)