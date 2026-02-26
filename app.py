import requests
import threading
import time
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_ASSETS_URL = "https://api.kraken.com/0/public/AssetPairs"

cached_data = {
    "top": [],
    "bottom": [],
    "last_update": "Loading..."
}

# ----------------------------
# MARKET SCORING LOGIC
# ----------------------------

def get_all_usd_pairs():
    response = requests.get(KRAKEN_ASSETS_URL, timeout=10).json()
    pairs = response.get("result", {})
    usd_pairs = []

    for pair_name, pair_info in pairs.items():
        if pair_info.get("quote") == "ZUSD":
            usd_pairs.append(pair_name)

    return usd_pairs


def get_price(pair):
    try:
        response = requests.get(
            KRAKEN_TICKER_URL,
            params={"pair": pair},
            timeout=10
        ).json()

        result = response.get("result", {})
        if not result:
            return None

        pair_data = list(result.values())[0]
        return float(pair_data["c"][0])  # last trade price
    except:
        return None


def score_market():
    pairs = get_all_usd_pairs()

    btc_price = get_price("XXBTZUSD")
    if not btc_price:
        return [], []

    market_scores = []

    for pair in pairs:
        if pair == "XXBTZUSD":
            continue

        price = get_price(pair)
        if not price:
            continue

        relative_strength = (price / btc_price) * 100

        if relative_strength > 1:
            label = "STRONG"
        elif relative_strength > 0.5:
            label = "NEUTRAL"
        else:
            label = "WEAK"

        market_scores.append({
            "pair": pair,
            "price": round(price, 6),
            "score": round(relative_strength, 4),
            "label": label
        })

    # Sort strongest first
    market_scores.sort(key=lambda x: x["score"], reverse=True)

    top = market_scores[:20]
    bottom = market_scores[-20:]

    return top, bottom


# ----------------------------
# UPDATE LOOP
# ----------------------------

def update_market():
    try:
        top, bottom = score_market()
        cached_data["top"] = top
        cached_data["bottom"] = bottom
        cached_data["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    except Exception as e:
        print("Update error:", e)


def background_updater():
    while True:
        update_market()
        time.sleep(600)  # every 10 minutes


# Run once immediately
update_market()

# Start background updates
threading.Thread(target=background_updater, daemon=True).start()


# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def home():
    return render_template(
        "index.html",
        top=cached_data["top"],
        bottom=cached_data["bottom"],
        last_update=cached_data["last_update"]
    )


# ----------------------------
# START SERVER
# ----------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)