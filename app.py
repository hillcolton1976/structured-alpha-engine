from flask import Flask, render_template
from datetime import datetime
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

COIN_COUNT = 75


# ---------------------------
# Indicators
# ---------------------------

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)

    avg_gain = pd.Series(gain).rolling(length).mean()
    avg_loss = pd.Series(loss).rolling(length).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ---------------------------
# Data Fetch
# ---------------------------

def get_top_coins():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": COIN_COUNT,
        "page": 1,
        "sparkline": False
    }
    response = requests.get(url, params=params, timeout=10)
    return response.json()


def get_ohlc(coin_id):
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
    params = {
        "vs_currency": "usd",
        "days": 1
    }
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if not isinstance(data, list) or len(data) == 0:
        return None

    df = pd.DataFrame(data, columns=["time", "open", "high", "low", "close"])
    return df


# ---------------------------
# Signal Engine
# ---------------------------

def analyze_coin(coin):
    try:
        df = get_ohlc(coin["id"])
        if df is None or len(df) < 30:
            return None

        df["ema_fast"] = ema(df["close"], 9)
        df["ema_slow"] = ema(df["close"], 21)
        df["rsi"] = rsi(df["close"])

        latest = df.iloc[-1]

        trend = 1 if latest["ema_fast"] > latest["ema_slow"] else -1
        momentum = 1 if latest["rsi"] > 55 else -1 if latest["rsi"] < 45 else 0

        alignment = trend + momentum

        if alignment >= 2:
            signal = "BUY"
        elif alignment <= -2:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "symbol": coin["symbol"].upper(),
            "price": round(coin["current_price"], 4),
            "signal": signal,
            "alignment": alignment,
            "rsi": round(float(latest["rsi"]), 1)
        }

    except:
        return None


def scan_market():
    coins = get_top_coins()
    results = []

    for coin in coins:
        analyzed = analyze_coin(coin)
        if analyzed:
            results.append(analyzed)

    results = sorted(results, key=lambda x: x["alignment"], reverse=True)
    return results


# ---------------------------
# Route
# ---------------------------

@app.route("/")
def home():
    results = scan_market()
    top = results[:10]

    return render_template(
        "index.html",
        top=top,
        results=results,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


# ---------------------------
# Run
# ---------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)