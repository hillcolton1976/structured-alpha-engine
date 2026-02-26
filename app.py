from flask import Flask, render_template
import requests
import statistics
from datetime import datetime

app = Flask(__name__)

KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
KRAKEN_PAIRS = "https://api.kraken.com/0/public/AssetPairs"


# -------- CLEAN SYMBOL --------
def clean_symbol(pair):
    pair = pair.replace("ZUSD", "")
    pair = pair.replace("USD", "")
    pair = pair.replace("XBT", "BTC")

    if pair.startswith("X") or pair.startswith("Z"):
        pair = pair[1:]

    return pair


# -------- GET USD PAIRS --------
def get_usd_pairs():
    data = requests.get(KRAKEN_PAIRS, timeout=10).json()
    pairs = []

    for pair, info in data["result"].items():
        if info.get("quote") == "ZUSD":
            pairs.append(pair)

    return pairs[:25]  # limit for stability


# -------- SMART LONG TERM SCORE --------
def score_market(pair):
    try:
        # Current price
        ticker = requests.get(KRAKEN_TICKER, params={"pair": pair}, timeout=10).json()
        price = float(list(ticker["result"].values())[0]["c"][0])

        # 30-day daily candles
        ohlc = requests.get(
            KRAKEN_OHLC,
            params={"pair": pair, "interval": 1440},
            timeout=10
        ).json()

        candles = list(ohlc["result"].values())[0][-30:]
        closes = [float(c[4]) for c in candles]

        if len(closes) < 15:
            return None

        sma = sum(closes) / len(closes)
        trend = ((closes[-1] - closes[0]) / closes[0]) * 100
        position = ((price - sma) / sma) * 100
        volatility = statistics.stdev(closes)

        score = trend + position - ((volatility / price) * 50)

        if score > 15:
            strength = "STRONG"
        elif score > 0:
            strength = "ACCUMULATION"
        else:
            strength = "WEAK"

        return {
            "coin": clean_symbol(pair),
            "price": round(price, 2),
            "score": round(score, 2),
            "strength": strength
        }

    except:
        return None


# -------- HOME --------
@app.route("/")
def home():
    pairs = get_usd_pairs()
    results = []

    for pair in pairs:
        result = score_market(pair)
        if result:
            results.append(result)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    buy_list = [c for c in results if c["strength"] in ["STRONG", "ACCUMULATION"]]
    sell_list = [c for c in results if c["strength"] == "WEAK"]

    return render_template(
        "index.html",
        coins=results,
        buy_list=buy_list,
        sell_list=sell_list,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)