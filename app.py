from flask import Flask, jsonify
import requests
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

SYMBOLS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","ADAUSDT",
    "AVAXUSDT","DOTUSDT","LINKUSDT","LTCUSDT","BNBUSDT"
]

TIMEFRAMES = {
    "scalp": "5m",
    "swing": "4h",
    "position": "1d"
}

def get_klines(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params)
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades","taker_base",
        "taker_quote","ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def score_timeframe(df):
    score = 0

    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["rsi"] = calculate_rsi(df["close"])
    df["atr"] = calculate_atr(df)

    latest = df.iloc[-1]

    # Trend
    if latest["ema20"] > latest["ema50"]:
        score += 25
    else:
        score -= 25

    # Momentum
    if latest["rsi"] > 60:
        score += 25
    elif latest["rsi"] < 40:
        score -= 25

    # Breakout
    if latest["close"] > df["close"].rolling(20).max().iloc[-2]:
        score += 25
    if latest["close"] < df["close"].rolling(20).min().iloc[-2]:
        score -= 25

    # Volume spike
    if latest["volume"] > df["volume"].rolling(20).mean().iloc[-2]:
        score += 25

    return score, latest["close"], latest["atr"]

def classify(score):
    if score > 70:
        return "STRONG BUY"
    elif score > 40:
        return "BUY"
    elif score < -70:
        return "STRONG SELL"
    elif score < -40:
        return "SELL"
    else:
        return "HOLD"

@app.route("/")
def home():
    results = []

    for symbol in SYMBOLS:
        tf_scores = {}
        alignment = 0

        for name, interval in TIMEFRAMES.items():
            df = get_klines(symbol, interval)
            score, price, atr = score_timeframe(df)
            tf_scores[name] = classify(score)

            if score > 40:
                alignment += 1
            if score < -40:
                alignment -= 1

        results.append({
            "symbol": symbol,
            "price": round(price, 4),
            "scalp": tf_scores["scalp"],
            "swing": tf_scores["swing"],
            "position": tf_scores["position"],
            "alignment": alignment
        })

    return jsonify({
        "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "results": results
    })

if __name__ == "__main__":
    app.run()