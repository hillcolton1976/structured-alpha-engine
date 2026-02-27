from flask import Flask, render_template
import requests
import pandas as pd
import numpy as np
import threading
import time

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50
RISK_PER_TRADE = 0.10  # 10%
LEVEL_TARGETS = [200, 1000, 5000, 10000]

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT"
]

# =============================
# ENGINE STATE
# =============================

engine = {
    "balance": START_BALANCE,
    "level": 1,
    "current_symbol": None,
    "entry_price": None,
    "position_size": 0,
    "last_action": "WAITING",
    "trades": []
}

# =============================
# MARKET DATA
# =============================

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
    data = requests.get(url).json()
    closes = [float(x[4]) for x in data]
    return pd.Series(closes)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =============================
# STRATEGY
# =============================

def evaluate_markets():
    best_signal = None
    best_score = 0

    for symbol in SYMBOLS:
        try:
            prices = get_klines(symbol)
            rsi = calculate_rsi(prices).iloc[-1]
            volatility = prices.pct_change().std()

            score = abs(50 - rsi) * volatility

            if score > best_score:
                best_score = score
                best_signal = {
                    "symbol": symbol,
                    "price": prices.iloc[-1],
                    "rsi": rsi
                }

        except:
            continue

    return best_signal

# =============================
# TRADING LOOP
# =============================

def trading_loop():
    while True:
        try:
            signal = evaluate_markets()

            if signal is None:
                time.sleep(10)
                continue

            price = signal["price"]
            rsi = signal["rsi"]

            # ENTRY
            if engine["current_symbol"] is None and rsi < 30:
                risk_amount = engine["balance"] * RISK_PER_TRADE
                position_size = risk_amount / price

                engine["current_symbol"] = signal["symbol"]
                engine["entry_price"] = price
                engine["position_size"] = position_size
                engine["last_action"] = f"BUY {signal['symbol']}"

            # EXIT
            elif engine["current_symbol"] is not None:
                if rsi > 60:
                    profit = (price - engine["entry_price"]) * engine["position_size"]
                    engine["balance"] += profit

                    engine["trades"].append({
                        "symbol": engine["current_symbol"],
                        "profit": round(profit, 2),
                        "balance": round(engine["balance"], 2)
                    })

                    engine["current_symbol"] = None
                    engine["entry_price"] = None
                    engine["position_size"] = 0
                    engine["last_action"] = "SELL"

                    check_level_up()

        except:
            pass

        time.sleep(15)

# =============================
# LEVEL SYSTEM
# =============================

def check_level_up():
    for i, target in enumerate(LEVEL_TARGETS):
        if engine["balance"] >= target and engine["level"] == i + 1:
            engine["level"] += 1
            print(f"LEVEL UP → {engine['level']}")

# =============================
# WEB
# =============================

@app.route("/")
def dashboard():
    return render_template("dashboard.html", engine=engine)

# =============================
# START THREAD
# =============================

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)