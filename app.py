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
RISK_PER_TRADE = 0.10
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
    "peak_balance": START_BALANCE,
    "level": 1,
    "current_symbol": None,
    "entry_price": None,
    "position_size": 0,
    "last_action": "WAITING",
    "trades": [],
    "equity_curve": [START_BALANCE]
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
# ANALYTICS
# =============================

def calculate_stats():
    trades = engine["trades"]

    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0,
            "total_profit": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "max_drawdown": 0,
            "roi": 0
        }

    profits = [t["profit"] for t in trades]
    wins = [p for p in profits if p > 0]
    losses = [p for p in profits if p <= 0]

    total_profit = sum(profits)
    win_rate = (len(wins) / len(profits)) * 100

    avg_win = np.mean(wins) if wins else 0
    avg_loss = np.mean(losses) if losses else 0

    # Drawdown
    equity = engine["equity_curve"]
    peak = equity[0]
    max_dd = 0
    for value in equity:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd

    roi = ((engine["balance"] - START_BALANCE) / START_BALANCE) * 100

    return {
        "total_trades": len(profits),
        "win_rate": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "roi": round(roi, 2)
    }

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

            if engine["current_symbol"] is None and rsi < 30:
                risk_amount = engine["balance"] * RISK_PER_TRADE
                position_size = risk_amount / price

                engine["current_symbol"] = signal["symbol"]
                engine["entry_price"] = price
                engine["position_size"] = position_size
                engine["last_action"] = f"BUY {signal['symbol']}"

            elif engine["current_symbol"] is not None:
                if rsi > 60:
                    profit = (price - engine["entry_price"]) * engine["position_size"]
                    engine["balance"] += profit

                    engine["trades"].append({
                        "symbol": engine["current_symbol"],
                        "profit": profit
                    })

                    engine["equity_curve"].append(engine["balance"])

                    if engine["balance"] > engine["peak_balance"]:
                        engine["peak_balance"] = engine["balance"]

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
    stats = calculate_stats()
    return render_template("dashboard.html", engine=engine, stats=stats)

# =============================
# START THREAD
# =============================

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)