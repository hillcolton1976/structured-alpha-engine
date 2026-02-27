from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

BINANCE_EXCHANGE = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_KLINES = "https://api.binance.com/api/v3/klines"

TIMEFRAMES = {
    "scalp": "5m",
    "swing": "4h",
    "position": "1d"
}

# -------------------------
# Get Top 75 USDT pairs
# -------------------------
def get_top_symbols(limit=75):
    data = requests.get(BINANCE_EXCHANGE, timeout=10).json()
    symbols = []

    for s in data["symbols"]:
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING":
            symbols.append(s["symbol"])

    return symbols[:limit]

# -------------------------
# Indicators
# -------------------------
def get_klines(symbol, interval, limit=200):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(BINANCE_KLINES, params=params, timeout=10)
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

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def score_timeframe(df):
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["rsi"] = rsi(df["close"])

    latest = df.iloc[-1]
    score = 0

    # Trend
    if latest["ema20"] > latest["ema50"]:
        score += 30
    else:
        score -= 30

    # Momentum
    if latest["rsi"] > 60:
        score += 30
    elif latest["rsi"] < 40:
        score -= 30

    # Breakout
    if latest["close"] > df["close"].rolling(20).max().iloc[-2]:
        score += 20
    if latest["close"] < df["close"].rolling(20).min().iloc[-2]:
        score -= 20

    # Volume spike
    if latest["volume"] > df["volume"].rolling(20).mean().iloc[-2]:
        score += 20

    return score, latest["close"]

def classify(score):
    if score >= 70:
        return "BUY"
    elif score <= -70:
        return "SELL"
    else:
        return "HOLD"

# -------------------------
# Main Route
# -------------------------
@app.route("/")
def home():

    symbols = get_top_symbols(75)
    results = []

    for symbol in symbols:

        try:
            alignment = 0
            tf_signals = {}

            for name, tf in TIMEFRAMES.items():
                df = get_klines(symbol, tf)
                score, price = score_timeframe(df)
                signal = classify(score)
                tf_signals[name] = signal

                if signal == "BUY":
                    alignment += 1
                elif signal == "SELL":
                    alignment -= 1

            results.append({
                "symbol": symbol.replace("USDT", ""),
                "price": round(price, 4),
                "scalp": tf_signals["scalp"],
                "swing": tf_signals["swing"],
                "position": tf_signals["position"],
                "alignment": alignment
            })

        except:
            continue

    # Sort by strongest alignment
    sorted_results = sorted(results, key=lambda x: x["alignment"], reverse=True)
    top_aligned = sorted_results[:20]

    return render_template(
        "index.html",
        results=sorted_results,
        top=top_aligned,
        updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )

if __name__ == "__main__":
    app.run()