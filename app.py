import os
import requests
import statistics
import threading
import time
from flask import Flask, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

KRAKEN_URL = "https://api.kraken.com/0/public"
CACHE = {"data": [], "updated": "Loading..."}


def clean_symbol(pair):
    pair = pair.replace("ZUSD", "").replace("USD", "")
    pair = pair.replace("XXBT", "BTC").replace("XBT", "BTC")
    pair = pair.replace("XETH", "ETH")

    if pair.startswith("X") or pair.startswith("Z"):
        pair = pair[1:]

    return pair


def get_usd_pairs():
    try:
        resp = requests.get(f"{KRAKEN_URL}/AssetPairs", timeout=10).json()
        pairs = []

        for name, data in resp["result"].items():
            if data.get("quote") == "ZUSD" and ".d" not in name:
                pairs.append(name)

        return pairs[:30]

    except:
        return []


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


def calculate_score(closes):
    if len(closes) < 200:
        return 0

    ma50 = statistics.mean(closes[-50:])
    ma200 = statistics.mean(closes[-200:])
    momentum = (closes[-1] - closes[-30]) / closes[-30]

    return round((ma50 - ma200) + momentum * 100, 4)


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


def updater():
    while True:
        try:
            CACHE["data"] = build_market()
            CACHE["updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        except:
            CACHE["updated"] = "Error updating"
        time.sleep(60)


threading.Thread(target=updater, daemon=True).start()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify({
        "updated": CACHE["updated"],
        "markets": CACHE["data"]
    })