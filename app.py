from flask import Flask, render_template
import requests
from datetime import datetime
import time

app = Flask(__name__)

KRAKEN_ASSETS = "https://api.kraken.com/0/public/AssetPairs"
KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker"

# Simple in-memory cache (avoids API spam + timeouts)
CACHE = {
    "data": None,
    "last_update": 0
}

CACHE_SECONDS = 60  # refresh once per minute


# ----------------------------
# Get all USD pairs
# ----------------------------
def get_usd_pairs():
    response = requests.get(KRAKEN_ASSETS, timeout=10).json()
    result = response.get("result", {})

    pairs = []
    for pair, details in result.items():
        if details.get("quote") == "ZUSD":
            pairs.append(pair)

    return pairs


# ----------------------------
# Fetch ALL tickers at once
# ----------------------------
def fetch_all_tickers(pairs):
    pair_string = ",".join(pairs)

    response = requests.get(
        KRAKEN_TICKER,
        params={"pair": pair_string},
        timeout=15
    ).json()

    return response.get("result", {})


# ----------------------------
# Scoring engine
# ----------------------------
def score_market():

    # Use cache
    if time.time() - CACHE["last_update"] < CACHE_SECONDS:
        return CACHE["data"]

    pairs = get_usd_pairs()
    tickers = fetch_all_tickers(pairs)

    market = []

    for pair, ticker in tickers.items():
        try:
            price = float(ticker["c"][0])
            vwap = float(ticker["p"][1])
            volume = float(ticker["v"][1])
            low = float(ticker["l"][1])
            high = float(ticker["h"][1])

            if vwap == 0 or high == low:
                continue

        except:
            continue

        change_percent = ((price - vwap) / vwap) * 100
        range_position = (price - low) / (high - low)

        score = 0

        # Momentum (mild for longer-term)
        if change_percent > 3:
            score += 2
        elif change_percent > 1:
            score += 1
        elif change_percent < -3:
            score -= 2

        # Above VWAP
        if price > vwap:
            score += 1

        # Near top of range
        if range_position > 0.7:
            score += 1

        # Strong liquidity
        if volume > 5_000_000:
            score += 1

        market.append({
            "pair": pair,
            "price": round(price, 4),
            "score": score
        })

    # Sort strongest first
    market_sorted = sorted(market, key=lambda x: x["score"], reverse=True)

    # Cache result
    CACHE["data"] = market_sorted[:50]
    CACHE["last_update"] = time.time()

    return CACHE["data"]


# ----------------------------
# Route
# ----------------------------
@app.route("/")
def home():

    market = score_market()

    return render_template(
        "index.html",
        market=market,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)