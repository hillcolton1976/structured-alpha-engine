from flask import Flask, render_template
import requests
from datetime import datetime

app = Flask(__name__)

KRAKEN_URL = "https://api.kraken.com/0/public/Ticker"

# Focused long-term coins (clean, stable list)
COINS = {
    "BTCUSD": "BTC",
    "ETHUSD": "ETH",
    "SOLUSD": "SOL",
    "ADAUSD": "ADA",
    "XRPUSD": "XRP",
    "AVAXUSD": "AVAX",
    "DOTUSD": "DOT",
    "LINKUSD": "LINK",
    "LTCUSD": "LTC",
    "BCHUSD": "BCH"
}

previous_scores = {}

def get_market_data(pair):
    try:
        r = requests.get(KRAKEN_URL, params={"pair": pair}, timeout=5)
        data = r.json()["result"]
        key = list(data.keys())[0]
        info = data[key]

        price = float(info["c"][0])
        volume = float(info["v"][1])
        change = float(info["p"][1])  # 24h VWAP approx proxy

        return price, volume, change
    except:
        return None, None, None


def calculate_score(price, volume, change):
    # Long-term weighted score
    score = 0

    score += change * 0.6
    score += (volume / 1_000_000) * 0.4

    return round(score, 2)


def market_regime():
    price, volume, change = get_market_data("BTCUSD")
    if change is None:
        return "NEUTRAL"

    if change > 0:
        return "BULL"
    else:
        return "BEAR"


def generate_signal(symbol, score, regime):
    prev = previous_scores.get(symbol, 0)
    delta = score - prev

    previous_scores[symbol] = score

    # BUY conditions
    if regime == "BULL" and delta > 5:
        return "BUY", "High"

    # SELL conditions
    if delta < -5:
        return "SELL", "High"

    return "HOLD", "Medium"


@app.route("/")
def home():
    results = []
    regime = market_regime()

    for pair, name in COINS.items():
        price, volume, change = get_market_data(pair)
        if price is None:
            continue

        score = calculate_score(price, volume, change)
        signal, confidence = generate_signal(name, score, regime)

        results.append({
            "coin": name,
            "price": round(price, 2),
            "score": score,
            "signal": signal,
            "confidence": confidence
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return render_template(
        "index.html",
        results=results,
        updated=updated,
        regime=regime
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)