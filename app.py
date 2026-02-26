import requests
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_ASSETS_URL = "https://api.kraken.com/0/public/AssetPairs"

# --------------------------------------------------
# Get all USD trading pairs
# --------------------------------------------------
def get_usd_pairs():
    try:
        response = requests.get(KRAKEN_ASSETS_URL, timeout=10).json()
        pairs = []

        for pair_name, pair_data in response["result"].items():
            if pair_data.get("quote") == "ZUSD":
                pairs.append(pair_name)

        return pairs

    except Exception as e:
        print("Error getting pairs:", e)
        return []

# --------------------------------------------------
# Long-Term Strength Scoring (6–8 Month Trend)
# --------------------------------------------------
def score_market(pair):
    try:
        response = requests.get(
            KRAKEN_TICKER_URL,
            params={"pair": pair},
            timeout=10
        ).json()

        data = response["result"][list(response["result"].keys())[0]]

        price = float(data["c"][0])       # last trade
        vwap_24h = float(data["p"][1])    # 24h VWAP
        high_24h = float(data["h"][1])    # 24h high
        low_24h = float(data["l"][1])     # 24h low
        volume_24h = float(data["v"][1])  # 24h volume

        if vwap_24h == 0:
            return None

        score = 0

        # Price above VWAP
        if price > vwap_24h:
            score += 1

        # Strong daily range (momentum)
        if (high_24h - low_24h) > (low_24h * 0.05):
            score += 1

        # High relative position in range
        if price > (low_24h + (high_24h - low_24h) * 0.6):
            score += 1

        # Good liquidity (avoid dead coins)
        if volume_24h > 100000:
            score += 1

        return {
            "pair": pair,
            "price": round(price, 6),
            "score": score
        }

    except Exception as e:
        print("Error scoring", pair, e)
        return None

# --------------------------------------------------
# Home Route
# --------------------------------------------------
@app.route("/")
def home():
    pairs = get_usd_pairs()
    market = []

    for pair in pairs:
        result = score_market(pair)
        if result:
            market.append(result)

    # Sort strongest first
    market = sorted(market, key=lambda x: x["score"], reverse=True)

    return render_template(
        "index.html",
        market=market,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

# --------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)