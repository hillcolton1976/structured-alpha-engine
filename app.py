from flask import Flask, render_template
import requests
import statistics
from datetime import datetime

app = Flask(__name__)

KRAKEN_TICKER = "https://api.kraken.com/0/public/Ticker"
KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"

# Major coins only (stable + realistic)
COINS = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
    "ADA": "ADAUSD",
    "DOT": "DOTUSD",
    "LINK": "LINKUSD",
    "AVAX": "AVAXUSD",
    "LTC": "LTCUSD",
    "BCH": "BCHUSD"
}

def get_price(pair):
    try:
        r = requests.get(KRAKEN_TICKER, params={"pair": pair}, timeout=5)
        data = r.json()
        result = list(data["result"].values())[0]
        return float(result["c"][0])
    except:
        return None

def get_daily_closes(pair):
    try:
        r = requests.get(
            KRAKEN_OHLC,
            params={"pair": pair, "interval": 1440},
            timeout=5
        )
        data = r.json()
        result = list(data["result"].values())[0]
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

    # Percentage based MA trend
    ma_trend = (ma50 - ma200) / ma200

    # 30 day momentum %
    momentum = (closes[-1] - closes[-30]) / closes[-30]

    # Final normalized score
    score = round((ma_trend * 100) + (momentum * 100), 2)

    # Classification
    if ma_trend > 0 and momentum > 0:
        strength = "STRONG"
    elif ma_trend > 0:
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

    # Sort by score descending
    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return render_template(
        "index.html",
        coins=results,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )

if __name__ == "__main__":
    app.run(debug=True)