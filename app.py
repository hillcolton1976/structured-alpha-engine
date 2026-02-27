from flask import Flask, render_template, jsonify
import requests
import datetime

app = Flask(__name__)

# Major coins only
COINS = [
    "BTCUSD",
    "ETHUSD",
    "SOLUSD",
    "XRPUSD",
    "ADAUSD",
    "LINKUSD",
    "AVAXUSD",
    "DOTUSD",
    "LTCUSD",
    "BCHUSD",
    "ATOMUSD"
]

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"


def get_price(pair):
    try:
        r = requests.get(KRAKEN_TICKER_URL, params={"pair": pair}, timeout=10).json()
        data = list(r["result"].values())[0]
        return float(data["c"][0])
    except:
        return None


def get_return(pair, interval, periods_back):
    try:
        r = requests.get(
            KRAKEN_OHLC_URL,
            params={"pair": pair, "interval": interval},
            timeout=10
        ).json()

        candles = list(r["result"].values())[0]

        if len(candles) < periods_back:
            return 0

        current_close = float(candles[-1][4])
        past_close = float(candles[-periods_back][4])

        return ((current_close - past_close) / past_close) * 100
    except:
        return 0


def calculate_scores():
    results = []

    btc_30 = get_return("BTCUSD", 1440, 30)
    btc_90 = get_return("BTCUSD", 1440, 90)

    for pair in COINS:
        price = get_price(pair)
        if price is None:
            continue

        r30 = get_return(pair, 1440, 30)
        r90 = get_return(pair, 1440, 90)

        relative = ((r30 - btc_30) + (r90 - btc_90)) / 2

        score = (r30 * 0.4) + (r90 * 0.4) + (relative * 0.2)

        if score > 25:
            strength = "STRONG"
        elif score > 5:
            strength = "ACCUMULATION"
        elif score > -5:
            strength = "NEUTRAL"
        else:
            strength = "WEAK"

        results.append({
            "coin": pair.replace("USD", ""),
            "price": round(price, 2),
            "score": round(score, 2),
            "strength": strength
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def data():
    coins = calculate_scores()
    return jsonify({
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "coins": coins
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)