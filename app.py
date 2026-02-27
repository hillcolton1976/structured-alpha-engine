import ccxt
import pandas as pd
import numpy as np
from flask import Flask, render_template
import os

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50
TIMEFRAME = "5m"
CANDLE_LIMIT = 100
MAX_POSITIONS = 5

exchange = ccxt.kraken()

# =============================
# GLOBAL STATE
# =============================

equity = START_BALANCE
cash = START_BALANCE
open_positions = {}
last_action = "Starting..."
total_trades = 0
wins = 0
losses = 0

# =============================
# GET TOP 50 USDT PAIRS
# =============================

def get_top_50():
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and markets[s]["active"]]
    return symbols[:50]

TOP_50 = get_top_50()

# =============================
# DATA FETCH
# =============================

def get_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        if len(df) < 30:
            return None

        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        return df

    except:
        return None

# =============================
# STRATEGY
# =============================

def trend_filter(symbol):
    df = get_data(symbol)
    if df is None or len(df) < 50:
        return False
    return df["ema21"].iloc[-1] > df["ema50"].iloc[-1]


def momentum_entry(symbol):
    df = get_data(symbol)
    if df is None or len(df) < 21:
        return False
    return df["ema9"].iloc[-1] > df["ema21"].iloc[-1]


def momentum_exit(symbol):
    df = get_data(symbol)
    if df is None or len(df) < 21:
        return False
    return df["ema9"].iloc[-1] < df["ema21"].iloc[-1]

# =============================
# ENGINE
# =============================

def evaluate():
    global equity, cash, open_positions
    global last_action, total_trades, wins, losses

    for symbol in TOP_50:

        df = get_data(symbol)
        if df is None:
            continue

        price = df["close"].iloc[-1]

        # EXIT
        if symbol in open_positions:
            if momentum_exit(symbol):
                entry_price = open_positions[symbol]["entry"]
                position_size = open_positions[symbol]["size"]

                pnl = (price - entry_price) * position_size
                cash += (position_size * price)
                equity = cash

                total_trades += 1

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                del open_positions[symbol]
                last_action = f"Exited {symbol}"
                continue

        # ENTRY
        if len(open_positions) >= MAX_POSITIONS:
            continue

        if symbol not in open_positions:
            if trend_filter(symbol) and momentum_entry(symbol):

                position_value = cash / (MAX_POSITIONS - len(open_positions))
                size = position_value / price

                open_positions[symbol] = {
                    "entry": price,
                    "size": size
                }

                cash -= position_value
                last_action = f"Entered {symbol}"

    # Update equity
    equity = cash
    for symbol, pos in open_positions.items():
        df = get_data(symbol)
        if df is None:
            continue
        current_price = df["close"].iloc[-1]
        equity += pos["size"] * current_price

# =============================
# DASHBOARD
# =============================

@app.route("/")
def dashboard():
    evaluate()

    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0
    roi = round(((equity - START_BALANCE) / START_BALANCE) * 100, 2)

    return render_template(
        "dashboard.html",
        balance=round(equity, 2),
        roi=roi,
        last_action=last_action,
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        positions=open_positions
    )

# =============================
# RUN
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)