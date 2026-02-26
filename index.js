import requests
import pandas as pd
import numpy as np
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

KRAKEN_API = "https://api.kraken.com/0/public"

########################################
# GET ALL USD PAIRS FROM KRAKEN
########################################
def get_usd_pairs():
    url = f"{KRAKEN_API}/AssetPairs"
    res = requests.get(url).json()

    pairs = []
    for pair, data in res["result"].items():
        if "USD" in data.get("quote", "") and data.get("status") == "online":
            pairs.append(pair)

    return pairs


########################################
# GET OHLC DATA
########################################
def get_ohlc(pair):
    url = f"{KRAKEN_API}/OHLC?pair={pair}&interval=60"
    res = requests.get(url).json()

    if "error" in res and len(res["error"]) > 0:
        return None

    data_key = list(res["result"].keys())[0]
    df = pd.DataFrame(res["result"][data_key])
    df.columns = ["time","open","high","low","close","vwap","volume","count"]

    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)

    return df


########################################
# RSI CALCULATION
########################################
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


########################################
# SCORE FUNCTION
########################################
def score_coin(df):
    if df is None or len(df) < 20:
        return None

    df["rsi"] = calculate_rsi(df["close"])

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    price = latest["close"]
    volume = latest["volume"]
    rsi = latest["rsi"]

    change = ((latest["close"] - previous["close"]) / previous["close"]) * 100

    score = 0

    # Momentum
    if change > 1:
        score += 2
    if change > 3:
        score += 2

    # Volume spike
    avg_vol = df["volume"].rolling(10).mean().iloc[-1]
    if volume > avg_vol * 1.5:
        score += 2

    # RSI sweet spot
    if 45 < rsi < 70:
        score += 2

    # Oversold bounce
    if rsi < 30:
        score += 1

    action = "HOLD"
    if score >= 6:
        action = "BUY"
    elif score <= 2:
        action = "SELL"

    return {
        "price": round(price, 6),
        "change_1h_percent": round(change, 2),
        "volume": round(volume, 2),
        "rsi": round(rsi, 2),
        "score": score,
        "action": action
    }


########################################
# MAIN ROUTE
########################################
@app.route("/signals")
def signals():

    pairs = get_usd_pairs()
    results = []

    for pair in pairs:
        try:
            df = get_ohlc(pair)
            scored = score_coin(df)
            if scored:
                scored["pair"] = pair
                results.append(scored)
        except:
            continue

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "top_opportunities": results[:20]
    })


########################################
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)