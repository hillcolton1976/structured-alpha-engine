from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
import random

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

START_BALANCE = 50.0

COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "DOGEUSDT"
]

RSI_PERIOD = 14
BUY_RSI = 30
SELL_RSI = 70

# ==============================
# STORAGE (paper mode)
# ==============================

portfolio = {
    "cash": START_BALANCE,
    "positions": {coin: 0 for coin in COINS},
    "entry_prices": {coin: 0 for coin in COINS}
}

trade_log = []

# ==============================
# HELPERS
# ==============================

def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    data = requests.get(url).json()
    return float(data["price"])

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    data = requests.get(url).json()
    closes = [float(k[4]) for k in data]
    return closes

def calculate_rsi(closes, period=14):
    series = pd.Series(closes)
    delta = series.diff()

    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.iloc[-1]

def portfolio_value():
    total = portfolio["cash"]
    for coin in COINS:
        if portfolio["positions"][coin] > 0:
            price = get_price(coin)
            total += portfolio["positions"][coin] * price
    return round(total, 2)

# ==============================
# TRADING ENGINE
# ==============================

def run_engine():
    allocation = portfolio["cash"] / len(COINS)

    for coin in COINS:
        try:
            price = get_price(coin)
            closes = get_klines(coin)
            rsi = calculate_rsi(closes)

            # BUY
            if rsi < BUY_RSI and portfolio["positions"][coin] == 0:
                amount = allocation / price
                portfolio["positions"][coin] = amount
                portfolio["entry_prices"][coin] = price
                portfolio["cash"] -= allocation

                trade_log.append({
                    "coin": coin,
                    "action": "BUY",
                    "price": price
                })

            # SELL
            elif rsi > SELL_RSI and portfolio["positions"][coin] > 0:
                amount = portfolio["positions"][coin]
                portfolio["cash"] += amount * price
                portfolio["positions"][coin] = 0

                trade_log.append({
                    "coin": coin,
                    "action": "SELL",
                    "price": price
                })

        except:
            continue

# ==============================
# LEVEL SYSTEM
# ==============================

def level_from_balance(balance):
    if balance < 200:
        return 1
    elif balance < 1000:
        return 2
    elif balance < 5000:
        return 3
    else:
        return 4

# ==============================
# ROUTE
# ==============================

@app.route("/")
def dashboard():
    run_engine()

    value = portfolio_value()
    level = level_from_balance(value)

    return render_template(
        "dashboard.html",
        portfolio_value=value,
        level=level,
        cash=round(portfolio["cash"], 2),
        positions=portfolio["positions"],
        trades=trade_log[-10:]
    )

if __name__ == "__main__":
    app.run(debug=True)