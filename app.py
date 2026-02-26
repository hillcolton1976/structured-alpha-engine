import requests
from flask import Flask, render_template
from datetime import datetime
import statistics

app = Flask(__name__)

KRAKEN_URL = "https://api.kraken.com/0/public"

# ==============================
# CLEAN SYMBOL FORMATTER
# ==============================
def clean_symbol(pair):
    pair = pair.replace("ZUSD", "").replace("USD", "")

    mapping = {
        "XXBT": "BTC",
        "XBT": "BTC",
        "XETH": "ETH",
        "XXDG": "DOGE",
        "XXRP": "XRP",
        "XADA": "ADA",
        "XLTC": "LTC"
    }

    if pair in mapping:
        return mapping[pair]

    if pair.startswith("X") or pair.startswith("Z"):
        pair = pair[1:]

    return pair


# ==============================
# GET USD PAIRS
# ==============================
def get_usd_pairs():
    resp = requests.get(f"{KRAKEN_URL}/AssetPairs").json()
    pairs = []

    for pair_name, data in resp["result"].items():
        if data.get("quote") == "ZUSD" and ".d" not in pair_name:
            pairs.append(pair_name)

    return pairs


# ==============================
# GET DAILY CANDLES
# ==============================
def get_daily_data(pair):
    resp = requests.get(
        f"{KRAKEN_URL}/OHLC",
        params={"pair": pair, "interval": 1440}
    ).json()

    if resp["error"]:
        return None

    candles = resp["result"][pair]
    closes = [float(c[4]) for c in candles]

    return closes


# ==============================
# LONG TERM SCORE
# ==============================
def calculate_score(closes):
    if len(closes) < 200:
        return 0

    ma50 = statistics.mean(closes[-50:])
    ma200 = statistics.mean(closes[-200:])

    momentum = (closes[-1] - closes[-30]) / closes[-30]

    score = (ma50 - ma200) + momentum * 100
    return round(score, 4)


# ==============================
# MAIN ROUTE
# ==============================
@app.route("/")
def home():
    pairs = get_usd_pairs()
    markets = []

    for pair in pairs:
        try:
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

        except:
            continue

    # Sort strongest first
    markets = sorted(markets, key=lambda x: x["score"], reverse=True)

    # Only show top 20
    markets = markets[:20]

    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return render_template("index.html", markets=markets, updated=updated)


# ==============================
# RUN APP
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)