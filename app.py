import os
import requests
from flask import Flask, render_template
from datetime import datetime
import statistics

app = Flask(__name__)

KRAKEN_URL = "https://api.kraken.com/0/public"
CACHE = {"data": [], "last_update": None}


# =========================
# CLEAN SYMBOL
# =========================
def clean_symbol(pair):
    pair = pair.replace("ZUSD", "").replace("USD", "")
    pair = pair.replace("XBT", "BTC")
    pair = pair.replace("XXBT", "BTC")
    pair = pair.replace("XETH", "ETH")
    pair = pair.replace("XXRP", "XRP")
    pair = pair.replace("XXDG", "DOGE")

    if pair.startswith("X") or pair.startswith("Z"):
        pair = pair[1:]

    return pair


# =========================
# GET USD PAIRS
# =========================
def get_usd_pairs():
    try:
        resp = requests.get(f"{KRAKEN_URL}/AssetPairs", timeout=10).json()
        pairs = []

        for pair_name, data in resp["result"].items():
            if data.get("quote") == "ZUSD" and ".d" not in pair_name:
                pairs.append(pair_name)

        return pairs[:40]  # limit for speed

    except:
        return []


# =========================
# GET DAILY DATA
# =========================
def get_daily_data(pair):
    try:
        resp = requests.get(
            f"{KRAKEN_URL}/OHLC",
            params={"pair": pair, "interval": 1440},
            timeout=10
        ).json()

        if resp.get("error"):
            return None

        candles = resp["result"][pair]
        closes = [float(c[4]) for c in candles]

        return closes

    except:
        return None


# =========================
# SCORE
# =========================
def calculate_score(closes):
    if len(closes) < 200:
        return 0

    ma50 = statistics.mean(closes[-50:])
    ma200 = statistics.mean(closes[-200:])
    momentum = (closes[-1] - closes[-30]) / closes[-30]

    return round((ma50 - ma200) + momentum * 100, 4)


# =========================
# BUILD MARKET DATA
# =========================
def build_market():
    pairs = get_usd_pairs()
    markets = []

    for pair in pairs:
        closes = get_daily_data(pair)
        if not closes:
            continue

        score = calculate_score(closes)

        if score > 2:
            strength = "STRONG"
        elif score > 0:
            strength = "NEUTRAL"
        else:
            strength = "WEAK"

        markets.append({
            "pair": clean_symbol(pair),
            "price": round(closes[-1], 2),
            "score": score,
            "strength": strength
        })

    markets = sorted(markets, key=lambda x: x["score"], reverse=True)
    return markets[:20]


# =========================
# ROUTE
# =========================
@app.route("/")
def home():
    global CACHE

    # Only refresh every 10 minutes
    if not CACHE["last_update"] or (datetime.utcnow() - CACHE["last_update"]).seconds > 600:
        CACHE["data"] = build_market()
        CACHE["last_update"] = datetime.utcnow()

    updated = CACHE["last_update"].strftime("%Y-%m-%d %H:%M UTC")

    return render_template(
        "index.html",
        markets=CACHE["data"],
        updated=updated
    )


# =========================
# START SERVER
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)