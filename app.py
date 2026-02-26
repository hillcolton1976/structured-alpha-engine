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
    data = response.json()["result"]

    results = []

    for coin, pair in PAIRS.items():
        if pair in data:
            price = float(data[pair]["c"][0])
            change = float(data[pair]["p"][1])  # 24h avg price

            score = 0
            action = "HOLD"

            if price > change:
                score += 3
            if price < change:
                score -= 2

            if score >= 2:
                action = "BUY"
            elif score <= -2:
                action = "SELL"

            results.append({
                "coin": coin,
                "pair": pair,
                "price": price,
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