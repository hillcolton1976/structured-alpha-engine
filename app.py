import asyncio
import json
import math
import statistics
import threading
import time
from datetime import datetime

import requests
from flask import Flask, render_template

app = Flask(__name__)

# ==========================
# CONFIG
# ==========================

START_BALANCE = 50.0
MAX_POSITIONS = 5
BASE_AGGRESSION = 0.20

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

# ==========================
# ACCOUNT STATE
# ==========================

account = {
    "balance": START_BALANCE,
    "equity": START_BALANCE,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "aggression": BASE_AGGRESSION,
    "drawdown": 0.0
}

positions = {}
signals = []
price_data = {}
equity_peak = START_BALANCE


# ==========================
# HELPERS
# ==========================

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return None


def calculate_momentum(symbol):
    if symbol not in price_data or len(price_data[symbol]) < 10:
        return 0
    prices = price_data[symbol]
    return ((prices[-1] - prices[0]) / prices[0]) * 100


def update_prices():
    for coin in TOP_20:
        price = get_price(coin)
        if price:
            if coin not in price_data:
                price_data[coin] = []
            price_data[coin].append(price)
            if len(price_data[coin]) > 20:
                price_data[coin].pop(0)


def open_trade(symbol, price):
    if len(positions) >= MAX_POSITIONS:
        return

    risk = account["balance"] * account["aggression"]
    if risk <= 1:
        return

    positions[symbol] = {
        "entry": price,
        "size": risk / price
    }

    account["balance"] -= risk
    signals.insert(0, f"{datetime.now().strftime('%H:%M:%S')} BUY {symbol}")
    account["trades"] += 1


def close_trade(symbol, price):
    global equity_peak

    pos = positions[symbol]
    entry = pos["entry"]
    size = pos["size"]

    value = size * price
    pnl = value - (size * entry)

    account["balance"] += value

    if pnl > 0:
        account["wins"] += 1
    else:
        account["losses"] += 1

    del positions[symbol]

    signals.insert(0, f"{datetime.now().strftime('%H:%M:%S')} SELL {symbol} P/L {round(pnl,2)}")

    account["equity"] = account["balance"]

    equity_peak = max(equity_peak, account["equity"])
    dd = (equity_peak - account["equity"]) / equity_peak * 100
    account["drawdown"] = round(dd, 2)

    adjust_aggression()


def adjust_aggression():
    total = account["wins"] + account["losses"]
    if total < 5:
        return

    win_rate = account["wins"] / total

    if win_rate > 0.6:
        account["aggression"] = min(0.35, account["aggression"] + 0.02)
    elif win_rate < 0.4:
        account["aggression"] = max(0.10, account["aggression"] - 0.02)


def trading_loop():
    while True:
        update_prices()

        rotation = sorted(
            TOP_20,
            key=lambda x: calculate_momentum(x),
            reverse=True
        )

        # Try opening top movers
        for coin in rotation[:5]:
            if coin not in positions:
                momentum = calculate_momentum(coin)
                if momentum > 0.3:
                    price = price_data[coin][-1]
                    open_trade(coin, price)

        # Manage open positions
        for coin in list(positions.keys()):
            price = price_data[coin][-1]
            entry = positions[coin]["entry"]
            change = (price - entry) / entry * 100

            if change > 1.0 or change < -1.0:
                close_trade(coin, price)

        # Update equity
        unrealized = 0
        for coin in positions:
            price = price_data[coin][-1]
            entry = positions[coin]["entry"]
            size = positions[coin]["size"]
            unrealized += size * price

        account["equity"] = account["balance"] + unrealized

        time.sleep(5)


# ==========================
# FLASK ROUTES
# ==========================

@app.route("/")
def dashboard():
    total = account["wins"] + account["losses"]
    win_rate = round((account["wins"]/total)*100, 2) if total > 0 else 0

    pos_list = []
    for coin in positions:
        entry = positions[coin]["entry"]
        current = price_data.get(coin, [entry])[-1]
        pnl = round((current-entry)/entry*100, 2)
        pos_list.append({
            "symbol": coin,
            "entry": round(entry,4),
            "current": round(current,4),
            "pnl": pnl
        })

    rotation_list = []
    for coin in sorted(TOP_20, key=lambda x: calculate_momentum(x), reverse=True)[:20]:
        rotation_list.append({
            "symbol": coin,
            "score": round(calculate_momentum(coin),2)
        })

    return render_template(
        "dashboard.html",
        equity=round(account["equity"],2),
        balance=round(account["balance"],2),
        trades=account["trades"],
        wins=account["wins"],
        losses=account["losses"],
        win_rate=win_rate,
        drawdown=account["drawdown"],
        aggression=round(account["aggression"]*100,1),
        positions=pos_list,
        rotation=rotation_list,
        signals=signals[:10]
    )


# ==========================
# START BACKGROUND THREAD
# ==========================

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)