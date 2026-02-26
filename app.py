from flask import Flask, render_template
import requests
import datetime
import statistics

app = Flask(__name__)

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC_URL = "https://api.kraken.com/0/public/OHLC"

# Major strong coins only
COINS = {
    "BTC": "XXBTZUSD",
    "ETH": "XETHZUSD",
    "SOL": "SOLUSD",
    "ADA": "ADAUSD",
    "XRP": "XRPUSD",
    "AVAX": "AVAXUSD",
    "DOT": "DOTUSD",
    "LINK": "LINKUSD",
    "MATIC": "MATICUSD",
    "ATOM": "ATOMUSD",
    "LTC": "LTCUSD",
    "BCH": "BCHUSD"
}


def get_price(pair):
    try:
        r = requests.get(KRAKEN_TICKER_URL, params={"pair": pair}, timeout=10).json()
        result = list(r["result"].values())[0]
        return float(result["c"][0])
    except:
        return None


def get_daily_closes(pair):
    try:
        r = requests.get(
            KRAKEN_OHLC_URL,
            params={"pair": pair, "interval": 1440},
            timeout=10
        ).json()
        result = list(r["result"].values())[0]
        closes = [float(candle[4]) for candle in result]
        return closes
    except:
        return []


def analyze_coin(symbol, pair):
    price = get_price(pair)
    closes = get_daily_closes(pair)

    if not price or len(closes) < 200:
        return None

    ma50 = statistics.mean(closes[-50:])
    ma200 = statistics.mean(closes[-200:])
    momentum = (closes[-1] - closes[-30]) / closes[-30]

    score = round((ma50 - ma200) + (momentum * 100), 4)

    if price > ma200 and momentum > 0:
        strength = "STRONG"
    elif price > ma200:
        strength = "ACCUMULATION"
    else:
        strength = "WEAK"

    return {
        "coin": symbol,
        "price": round(price, 2),
        "score": score,
        "strength": strength
    }


@app.route("/")
def home():
    results = []

    for symbol, pair in COINS.items():
        data = analyze_coin(symbol, pair)
        if data:
            results.append(data)

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    return render_template("index.html", coins=results, updated=updated)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)