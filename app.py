import requests
import pandas as pd
import numpy as np
import time
from flask import Flask, render_template

app = Flask(__name__)

balance = 50.0
position = None
entry_price = 0
level = 1
trade_log = []
last_update = time.time()

PAIR = "BTCUSD"
FEE = 0.0026
SLIPPAGE = 0.001

def get_price():
    url = f"https://api.kraken.com/0/public/Ticker?pair={PAIR}"
    data = requests.get(url).json()
    price = list(data["result"].values())[0]["c"][0]
    return float(price)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def determine_risk():
    global level
    if balance < 200:
        level = 1
        return 0.05
    elif balance < 1000:
        level = 2
        return 0.03
    elif balance < 5000:
        level = 3
        return 0.02
    else:
        level = 4
        return 0.01

@app.route("/")
def home():
    global balance, position, entry_price, trade_log, last_update

    price = get_price()

    # fake small history window for RSI simulation
    prices = pd.Series(np.random.normal(price, price * 0.002, 100))
    rsi = calculate_rsi(prices).iloc[-1]

    risk_pct = determine_risk()

    action = "HOLD"

    if position is None and rsi < 30:
        position = balance * risk_pct / price
        entry_price = price * (1 + SLIPPAGE)
        balance -= position * entry_price
        balance -= balance * FEE
        action = "BUY"

    elif position is not None and rsi > 55:
        exit_price = price * (1 - SLIPPAGE)
        balance += position * exit_price
        balance -= balance * FEE
        profit = (exit_price - entry_price) * position
        trade_log.append(round(profit, 2))
        position = None
        action = "SELL"

    return render_template(
        "dashboard.html",
        balance=round(balance, 2),
        level=level,
        price=round(price, 2),
        rsi=round(rsi, 2),
        action=action,
        trades=trade_log[-10:]
    )

if __name__ == "__main__":
    app.run(debug=True)