from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from datetime import datetime

app = Flask(__name__)

COINS = [
    "BTCUSD",
    "ETHUSD",
    "SOLUSD",
    "XRPUSD",
    "DOTUSD",
    "AVAXUSD",
    "LINKUSD",
    "LTCUSD"
]

def get_kraken_4h(symbol):
    url = f"https://api.kraken.com/0/public/OHLC?pair={symbol}&interval=240"
    r = requests.get(url)
    data = r.json()

    pair_key = list(data["result"].keys())[0]
    df = pd.DataFrame(data["result"][pair_key])
    df.columns = [
        "time","open","high","low","close",
        "vwap","volume","count"
    ]

    df["close"] = df["close"].astype(float)
    return df

def analyze_coin(symbol):

    df = get_kraken_4h(symbol)

    df["ema50"] = EMAIndicator(df["close"], 50).ema_indicator()
    df["ema200"] = EMAIndicator(df["close"], 200).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], 14).rsi()

    latest = df.iloc[-1]

    price = latest["close"]
    ema50 = latest["ema50"]
    ema200 = latest["ema200"]
    rsi = latest["rsi"]

    score = 0

    if price > ema50:
        score += 30
    if ema50 > ema200:
        score += 30
    if 45 < rsi < 65:
        score += 20
    if rsi > 50:
        score += 20

    signal = "BUY" if score >= 70 else "HOLD"

    return {
        "coin": symbol.replace("USD",""),
        "price": round(price,2),
        "score": score,
        "signal": signal
    }

def stage_logic(balance):

    if balance < 200:
        return "Stage 1: $50 → $200 (Aggressive Growth)"
    elif balance < 1000:
        return "Stage 2: $200 → $1,000"
    elif balance < 5000:
        return "Stage 3: $1,000 → $5,000"
    else:
        return "Stage 4: $5,000 → $20,000"

@app.route("/")
def swing():

    balance = 50  # starting capital
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    results = []

    for coin in COINS:
        try:
            results.append(analyze_coin(coin))
        except:
            continue

    best = max(results, key=lambda x: x["score"])

    risk_percent = 0.05
    reward_ratio = 2

    entry = best["price"]
    stop_loss = round(entry * 0.97, 2)
    take_profit = round(entry * 1.06, 2)

    risk_amount = balance * risk_percent
    position_size = round(risk_amount / (entry - stop_loss), 3)

    best["entry"] = entry
    best["stop_loss"] = stop_loss
    best["take_profit"] = take_profit
    best["position_size"] = position_size

    return render_template(
        "swing.html",
        updated=updated,
        balance=balance,
        stage=stage_logic(balance),
        setup=best
    )

if __name__ == "__main__":
    app.run()