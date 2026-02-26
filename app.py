from flask import Flask, render_template
import requests
import threading
import time
from datetime import datetime
import statistics

app = Flask(__name__)

KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
KRAKEN_PAIRS = "https://api.kraken.com/0/public/AssetPairs"

UPDATE_INTERVAL = 600  # 10 minutes
cached_data = {
    "last_update": None,
    "top": [],
    "bottom": []
}

# -------------------------
# Helper: EMA
# -------------------------
def calculate_ema(prices, period=50):
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return ema

# -------------------------
# Get USD Token Pairs
# -------------------------
def get_token_pairs():
    response = requests.get(KRAKEN_PAIRS, timeout=10).json()
    pairs = response.get("result", {})
    tokens = []

    for pair, details in pairs.items():
        if details.get("quote") == "ZUSD":
            base = details.get("base", "")
            # exclude stablecoins
            if "USD" not in base and "EUR" not in base:
                tokens.append(pair)

    return tokens

# -------------------------
# Get OHLC data
# -------------------------
def get_ohlc(pair):
    response = requests.get(
        KRAKEN_OHLC,
        params={"pair": pair, "interval": 1440},
        timeout=10
    ).json()

    result = response.get("result", {})
    if pair not in result:
        return None

    candles = result[pair][-90:]
    closes = [float(c[4]) for c in candles]
    volumes = [float(c[6]) for c in candles]

    return closes, volumes

# -------------------------
# Main Scoring Engine
# -------------------------
def update_market():

    global cached_data

    try:
        pairs = get_token_pairs()

        btc_data = get_ohlc("XBTUSD")
        if not btc_data:
            return

        btc_closes, _ = btc_data
        btc_30 = (btc_closes[-1] / btc_closes[-30]) - 1
        btc_90 = (btc_closes[-1] / btc_closes[0]) - 1

        results = []

        for pair in pairs:

            data = get_ohlc(pair)
            if not data:
                continue

            closes, volumes = data
            if len(closes) < 90:
                continue

            r30 = (closes[-1] / closes[-30]) - 1
            r90 = (closes[-1] / closes[0]) - 1

            ema50 = calculate_ema(closes, 50)
            if not ema50:
                continue

            volatility = statistics.stdev(closes[-30:]) if len(closes) >= 30 else 0

            score = 0

            # Relative strength vs BTC
            if r90 > btc_90:
                score += 3
            if r30 > btc_30:
                score += 2

            # Trend filter
            if closes[-1] > ema50:
                score += 2

            # Momentum
            if r30 > 0:
                score += 1

            # Volatility control
            if volatility < statistics.mean(closes[-30:]) * 0.15:
                score += 1

            results.append({
                "pair": pair,
                "score": score,
                "r30": round(r30 * 100, 2),
                "r90": round(r90 * 100, 2)
            })

        ranked = sorted(results, key=lambda x: x["score"], reverse=True)

        cached_data["top"] = ranked[:30]
        cached_data["bottom"] = ranked[-30:]
        cached_data["last_update"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    except Exception as e:
        print("Update error:", e)

# -------------------------
# Background Thread
# -------------------------
def background_updater():
    while True:
        update_market()
        time.sleep(UPDATE_INTERVAL)

threading.Thread(target=background_updater, daemon=True).start()

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    return render_template(
        "index.html",
        top=cached_data["top"],
        bottom=cached_data["bottom"],
        last_update=cached_data["last_update"]
    )

# -------------------------
# Run
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)