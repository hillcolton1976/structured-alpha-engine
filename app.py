import ccxt
import pandas as pd
import numpy as np
import time
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50.0
cash_balance = START_BALANCE
equity = START_BALANCE

MAX_POSITIONS = 5
POSITION_SIZE = 0.14  # 14% per position
STOP_LOSS = -0.006    # -0.6%
TAKE_PROFIT = 0.018   # +1.8%
TRAIL_TRIGGER = 0.01  # start trailing after +1%
COOLDOWN_SECONDS = 300
EVALUATION_INTERVAL = 60

exchange = ccxt.coinbase()

open_positions = {}
last_exit_time = {}

total_trades = 0
wins = 0
losses = 0
last_action = "Starting..."

# =============================
# UTILITIES
# =============================

def get_top_markets(limit=50):
    markets = exchange.load_markets()
    usdt_pairs = [
        symbol for symbol in markets
        if "/USDT" in symbol and markets[symbol]['active']
    ]
    return usdt_pairs[:limit]


def fetch_dataframe(symbol, timeframe, limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        return df
    except:
        return None


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def trend_filter(symbol):
    df = fetch_dataframe(symbol, '5m', 100)
    if df is None:
        return False

    df['ema50'] = ema(df['close'], 50)

    if df['close'].iloc[-1] > df['ema50'].iloc[-1]:
        if df['ema50'].iloc[-1] > df['ema50'].iloc[-2]:
            return True

    return False


def momentum_entry(symbol):
    df = fetch_dataframe(symbol, '1m', 50)
    if df is None:
        return False

    df['ema9'] = ema(df['close'], 9)
    df['ema21'] = ema(df['close'], 21)

    if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
        if df['ema9'].iloc[-2] <= df['ema21'].iloc[-2]:
            return True

    return False


# =============================
# CORE ENGINE
# =============================

def evaluate():
    global cash_balance, equity, total_trades, wins, losses, last_action

    symbols = get_top_markets()

    # === Manage Open Positions ===
    for symbol in list(open_positions.keys()):
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
        except:
            continue

        entry = open_positions[symbol]['entry']
        change_pct = (current_price - entry) / entry

        # Trailing Stop Activation
        if change_pct >= TRAIL_TRIGGER:
            open_positions[symbol]['trail'] = current_price * 0.995

        # Update trailing
        if 'trail' in open_positions[symbol]:
            if current_price < open_positions[symbol]['trail']:
                change_pct = (current_price - entry) / entry
                close_position(symbol, change_pct)
                continue
            else:
                open_positions[symbol]['trail'] = max(
                    open_positions[symbol]['trail'],
                    current_price * 0.995
                )

        # Stop Loss
        if change_pct <= STOP_LOSS:
            close_position(symbol, change_pct)
            continue

        # Take Profit
        if change_pct >= TAKE_PROFIT:
            close_position(symbol, change_pct)
            continue

    # === Open New Positions ===
    if len(open_positions) < MAX_POSITIONS:
        for symbol in symbols:

            if symbol in open_positions:
                continue

            if symbol in last_exit_time:
                if time.time() - last_exit_time[symbol] < COOLDOWN_SECONDS:
                    continue

            if trend_filter(symbol) and momentum_entry(symbol):
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    entry_price = ticker['last']
                except:
                    continue

                allocation = cash_balance * POSITION_SIZE
                if allocation <= 1:
                    continue

                cash_balance -= allocation

                open_positions[symbol] = {
                    'entry': entry_price,
                    'size': allocation
                }

                last_action = f"Entered {symbol}"
                break


    # === Update Equity ===
    equity = cash_balance
    for symbol in open_positions:
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            entry = open_positions[symbol]['entry']
            allocation = open_positions[symbol]['size']
            change_pct = (current_price - entry) / entry
            equity += allocation * (1 + change_pct)
        except:
            continue


def close_position(symbol, change_pct):
    global cash_balance, total_trades, wins, losses, last_action

    position = open_positions[symbol]
    allocation = position['size']

    pnl = allocation * change_pct
    cash_balance += allocation + pnl

    total_trades += 1
    if pnl > 0:
        wins += 1
    else:
        losses += 1

    last_exit_time[symbol] = time.time()
    last_action = f"Closed {symbol} ({round(change_pct*100,2)}%)"

    del open_positions[symbol]


# =============================
# FLASK ROUTE
# =============================

@app.route('/')
def dashboard():
    evaluate()

    win_rate = 0
    if total_trades > 0:
        win_rate = round((wins / total_trades) * 100, 2)

    roi = round(((equity - START_BALANCE) / START_BALANCE) * 100, 2)

    return render_template(
        "dashboard.html",
        equity=round(equity, 2),
        cash=round(cash_balance, 2),
        roi=roi,
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        win_rate=win_rate,
        positions=open_positions,
        last_action=last_action
    )


# =============================
# AUTO LOOP
# =============================

if __name__ == "__main__":
    while True:
        evaluate()
        time.sleep(EVALUATION_INTERVAL)