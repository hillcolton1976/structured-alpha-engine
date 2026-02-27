import os
import time
import threading
from datetime import datetime
from flask import Flask, render_template
import ccxt
import pandas as pd

app = Flask(__name__)

# =========================
# CONFIG
# =========================
START_BALANCE = 50.0
RISK_PER_TRADE = 0.04      # 4%
TAKE_PROFIT = 0.012        # 1.2%
STOP_LOSS = 0.006          # 0.6%
TIMEFRAME = '1m'
MAX_OPEN_TRADES = 1
SYMBOL_LIMIT = 15

# =========================
# ENGINE STATE
# =========================
engine = {
    "balance": START_BALANCE,
    "roi": 0.0,
    "level": 1,
    "last_action": "Starting...",
    "total_trades": 0,
    "wins": 0,
    "losses": 0,
    "total_profit": 0.0,
    "max_drawdown": 0.0,
    "recent_trades": [],
    "active_trade": None
}

exchange = ccxt.kraken()

# =========================
# MARKET SCANNER
# =========================
def get_symbols():
    markets = exchange.load_markets()
    symbols = [
        s for s in markets
        if "/USDT" in s and markets[s]['active']
    ]
    return symbols[:SYMBOL_LIMIT]

def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=50)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
    return df

def check_entry(df):
    if len(df) < 3:
        return False

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Simple momentum breakout
    if last["close"] > prev["high"]:
        return "LONG"
    return None

# =========================
# TRADE LOGIC
# =========================
def open_trade(symbol, direction, price):
    risk_amount = engine["balance"] * RISK_PER_TRADE
    position_size = risk_amount / (price * STOP_LOSS)

    engine["active_trade"] = {
        "symbol": symbol,
        "direction": direction,
        "entry": price,
        "size": position_size,
        "stop": price * (1 - STOP_LOSS),
        "target": price * (1 + TAKE_PROFIT)
    }

    engine["last_action"] = f"Entered {symbol}"

def close_trade(price, reason):
    trade = engine["active_trade"]
    if not trade:
        return

    entry = trade["entry"]
    size = trade["size"]

    pnl = (price - entry) * size
    engine["balance"] += pnl
    engine["total_profit"] += pnl
    engine["total_trades"] += 1

    if pnl > 0:
        engine["wins"] += 1
    else:
        engine["losses"] += 1

    engine["roi"] = ((engine["balance"] - START_BALANCE) / START_BALANCE) * 100

    engine["recent_trades"].append({
        "symbol": trade["symbol"],
        "result": round(pnl, 2),
        "balance": round(engine["balance"], 2)
    })

    engine["active_trade"] = None
    engine["last_action"] = f"Closed: {reason}"

# =========================
# MAIN LOOP
# =========================
def trading_loop():
    while True:
        try:
            symbols = get_symbols()

            if engine["active_trade"] is None:
                for symbol in symbols:
                    df = get_data(symbol)
                    signal = check_entry(df)

                    if signal:
                        price = df.iloc[-1]["close"]
                        open_trade(symbol, signal, price)
                        break

            else:
                trade = engine["active_trade"]
                df = get_data(trade["symbol"])
                price = df.iloc[-1]["close"]
                prev_close = df.iloc[-2]["close"]

                # Stop loss
                if price <= trade["stop"]:
                    close_trade(price, "Stop Loss")

                # Take profit
                elif price >= trade["target"]:
                    close_trade(price, "Take Profit")

                # Early exit momentum flip
                elif price < prev_close:
                    close_trade(price, "Momentum Flip")

            time.sleep(20)

        except Exception as e:
            print("Error:", e)
            engine["last_action"] = "Error"
            time.sleep(10)

# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():
    win_rate = 0
    if engine["total_trades"] > 0:
        win_rate = (engine["wins"] / engine["total_trades"]) * 100

    return render_template(
        "dashboard.html",
        balance=round(engine["balance"], 2),
        roi=round(engine["roi"], 2),
        level=engine["level"],
        last_action=engine["last_action"],
        total_trades=engine["total_trades"],
        win_rate=round(win_rate, 2),
        total_profit=round(engine["total_profit"], 2),
        max_drawdown=round(engine["max_drawdown"], 2),
        trades=engine["recent_trades"][-15:]
    )

# =========================
# START ENGINE
# =========================
if __name__ == "__main__":
    thread = threading.Thread(target=trading_loop)
    thread.daemon = True
    thread.start()
    app.run(host="0.0.0.0", port=8080)