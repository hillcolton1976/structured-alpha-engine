import os
import ccxt
import pandas as pd
import numpy as np
import threading
import time
from flask import Flask, jsonify

app = Flask(__name__)

# =============================
# CONFIG
# =============================
API_KEY = os.getenv("API_KEY")
SECRET = os.getenv("SECRET")

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT"]
TIMEFRAME = "1m"
RISK_PER_TRADE = 0.25   # 25% of equity per trade (AGGRESSIVE)
TAKE_PROFIT = 0.015     # 1.5%
STOP_LOSS = 0.01        # 1%
SLEEP_TIME = 5          # seconds

# =============================
# EXCHANGE SETUP
# =============================

public_exchange = ccxt.binanceus({
    "enableRateLimit": True
})

private_exchange = None
if API_KEY and SECRET:
    private_exchange = ccxt.binanceus({
        "apiKey": API_KEY,
        "secret": SECRET,
        "enableRateLimit": True
    })

# =============================
# STATE
# =============================

equity = 50.0
cash = 50.0
positions = {}
wins = 0
losses = 0
trades = 0
signals = []

lock = threading.Lock()

# =============================
# INDICATORS
# =============================

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =============================
# DATA FETCH
# =============================

def get_data(symbol):
    try:
        ohlcv = public_exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=50)
        df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
        df["rsi"] = calculate_rsi(df)
        return df
    except Exception as e:
        print("Data error:", e)
        return None

# =============================
# TRADING LOGIC
# =============================

def trade_symbol(symbol):
    global cash, equity, wins, losses, trades

    df = get_data(symbol)
    if df is None:
        return

    latest = df.iloc[-1]
    price = latest["close"]
    rsi = latest["rsi"]

    with lock:

        # ENTRY
        if symbol not in positions and rsi < 30 and cash > 5:
            position_size = equity * RISK_PER_TRADE
            qty = position_size / price

            positions[symbol] = {
                "entry": price,
                "qty": qty
            }

            cash -= position_size
            signals.append(f"BUY {symbol} @ {price}")
            print("BUY", symbol)

        # EXIT
        elif symbol in positions:
            entry = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]

            change = (price - entry) / entry

            if change >= TAKE_PROFIT or change <= -STOP_LOSS:
                pnl = qty * price
                result = pnl - (qty * entry)

                cash += pnl
                equity = cash

                trades += 1
                if result > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]
                signals.append(f"SELL {symbol} @ {price}")
                print("SELL", symbol)

# =============================
# MAIN LOOP
# =============================

def aggressive_loop():
    global equity

    while True:
        try:
            for symbol in SYMBOLS:
                trade_symbol(symbol)

            equity = cash
            time.sleep(SLEEP_TIME)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(3)

# =============================
# WEB ROUTES
# =============================

@app.route("/")
def dashboard():
    winrate = (wins / trades * 100) if trades > 0 else 0

    return jsonify({
        "Equity": round(equity,2),
        "Cash": round(cash,2),
        "Trades": trades,
        "Wins": wins,
        "Losses": losses,
        "Win Rate %": round(winrate,2),
        "Open Positions": positions,
        "Recent Signals": signals[-5:]
    })

# =============================
# START BOT
# =============================

threading.Thread(target=aggressive_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)