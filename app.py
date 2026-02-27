import ccxt
import pandas as pd
import numpy as np
import time
from flask import Flask, render_template

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50.0
cash_balance = START_BALANCE
equity = START_BALANCE

MAX_POSITIONS = 5
POSITION_SIZE = 0.14
STOP_LOSS = -0.006
TAKE_PROFIT = 0.018
TRAIL_TRIGGER = 0.01
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
    try:
        markets = exchange.load_markets()
        pairs = [
            s for s in markets
            if "/USDT" in s and markets[s]['active']
        ]
        return pairs[:limit]
    except:
        return []


def fetch_dataframe(symbol, timeframe, limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv or len(ohlcv) < 30:
            return None
        df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
        return df
    except:
        return None


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# =============================
# STRATEGY LOGIC (SAFE)
# =============================

def trend_filter(symbol):
    df = fetch_dataframe(symbol, '5m', 100)
    if df is None or len(df) < 60:
        return False

    df['ema50'] = ema(df['close'], 50)

    if df['ema50'].isna().any():
        return False

    if df['close'].iloc[-1] > df['ema50'].iloc[-1]:
        if df['ema50'].iloc[-1] > df['ema50'].iloc[-2]:
            return True

    return False


def momentum_entry(symbol):
    df = fetch_dataframe(symbol, '1m', 50)
    if df is None or len(df) < 25:
        return False

    df['ema9'] = ema(df['close'], 9)
    df['ema21'] = ema(df['close'], 21)

    if df[['ema9','ema21']].isna().any().any():
        return False

    if len(df) < 3:
        return False

    if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
        if df['ema9'].iloc[-2] <= df['ema21'].iloc[-2]:
            return True

    return False


# =============================
# ENGINE
# =============================

def evaluate():
    global cash_balance, equity, total_trades, wins, losses, last_action

    symbols = get_top_markets()

    # --- Manage Positions ---
    for symbol in list(open_positions.keys()):
        try:
            ticker = exchange.fetch_ticker(symbol)
            current = ticker['last']
        except:
            continue

        entry = open_positions[symbol]['entry']
        size = open_positions[symbol]['size']
        change = (current - entry) / entry

        # trailing
        if change >= TRAIL_TRIGGER:
            open_positions[symbol]['trail'] = current * 0.995

        if 'trail' in open_positions[symbol]:
            if current < open_positions[symbol]['trail']:
                close_position(symbol, change)
                continue
            else:
                open_positions[symbol]['trail'] = max(
                    open_positions[symbol]['trail'],
                    current * 0.995
                )

        if change <= STOP_LOSS:
            close_position(symbol, change)
            continue

        if change >= TAKE_PROFIT:
            close_position(symbol, change)
            continue

    # --- Open New Positions ---
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
                    entry = ticker['last']
                except:
                    continue

                allocation = cash_balance * POSITION_SIZE
                if allocation <= 1:
                    continue

                cash_balance -= allocation

                open_positions[symbol] = {
                    'entry': entry,
                    'size': allocation
                }

                last_action = f"Entered {symbol}"
                break

    # --- Update Equity ---
    equity = cash_balance
    for symbol in open_positions:
        try:
            ticker = exchange.fetch_ticker(symbol)
            current = ticker['last']
            entry = open_positions[symbol]['entry']
            size = open_positions[symbol]['size']
            change = (current - entry) / entry
            equity += size * (1 + change)
        except:
            continue


def close_position(symbol, change):
    global cash_balance, total_trades, wins, losses, last_action

    pos = open_positions[symbol]
    size = pos['size']
    pnl = size * change

    cash_balance += size + pnl

    total_trades += 1
    if pnl > 0:
        wins += 1
    else:
        losses += 1

    last_exit_time[symbol] = time.time()
    last_action = f"Closed {symbol} ({round(change*100,2)}%)"

    del open_positions[symbol]


# =============================
# FLASK
# =============================

@app.route('/')
def dashboard():
    evaluate()

    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0
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


if __name__ == "__main__":
    while True:
        evaluate()
        time.sleep(EVALUATION_INTERVAL)