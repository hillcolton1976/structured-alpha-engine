from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

# Kraken spot pairs we will scan
PAIRS = {
    "BTC": "XBTUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "AVAX": "AVAXUSDT",
    "DOT": "DOTUSDT",
    "LINK": "LINKUSDT",
    "LTC": "LTCUSDT",
    "BCH": "BCHUSDT"
}

ACCOUNT_BALANCE = 50
RISK_PER_TRADE = 0.05  # 5% risk


def get_ohlc(pair):
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=240"
    r = requests.get(url)
    data = r.json()

    result_key = list(data["result"].keys())[0]
    ohlc = data["result"][result_key]

    df = pd.DataFrame(ohlc, columns=[
        "time","open","high","low","close",
        "vwap","volume","count"
    ])

    df["close"] = df["close"].astype(float)
    return df


def add_indicators(df):
    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()

    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    return df


def analyze_coin(symbol, pair):
    try:
        df = get_ohlc(pair)
        df = add_indicators(df)

        last = df.iloc[-1]

        price = last["close"]
        ema9 = last["ema9"]
        ema21 = last["ema21"]
        rsi = last["rsi"]

        signal = "NO TRADE"
        score = 0

        if ema9 > ema21:
            score += 40
        if rsi > 50 and rsi < 70:
            score += 30
        if df["ema9"].iloc[-2] < df["ema9"].iloc[-1]:
            score += 30

        if score >= 70:
            signal = "BUY"
        elif score <= 30:
            signal = "SELL"

        stop = price * 0.94
        take = price * 1.10

        position_size = ACCOUNT_BALANCE * RISK_PER_TRADE

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "score": round(score, 2),
            "signal": signal,
            "entry": round(price, 2),
            "take": round(take, 2),
            "stop": round(stop, 2),
            "size": round(position_size, 2)
        }

    except:
        return None


@app.route("/")
def home():
    results = []

    for symbol, pair in PAIRS.items():
        data = analyze_coin(symbol, pair)
        if data:
            results.append(data)

    best = max(results, key=lambda x: x["score"]) if results else None

    return render_template(
        "swing.html",
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        balance=ACCOUNT_BALANCE,
        best=best
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)