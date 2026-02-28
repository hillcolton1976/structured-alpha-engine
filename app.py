import ccxt
import pandas as pd
import numpy as np
import time
import threading
from flask import Flask, jsonify

# =========================
# CONFIG
# =========================

TIMEFRAME = "1m"
START_BALANCE = 50

BASE_RISK = 0.22
MAX_RISK = 0.45

TP_MULTIPLIER = 3.0
SL_MULTIPLIER = 1.4

MAX_POSITIONS = 5
MIN_HOLD_SECONDS = 40
SCAN_DELAY = 6

# =========================
# STATE
# =========================

balance = START_BALANCE
wins = 0
losses = 0
trades = 0
aggression = 1.0
positions = {}
recent_signals = []

# =========================
# EXCHANGE (PUBLIC ONLY)
# =========================

exchange = ccxt.binanceus({
    "enableRateLimit": True
})

# =========================
# SYMBOL LIST
# =========================

SYMBOLS = [
    "BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT",
    "DOGE/USDT","AVAX/USDT","LINK/USDT","ADA/USDT","MATIC/USDT",
    "LTC/USDT","DOT/USDT","SHIB/USDT","ATOM/USDT","ARB/USDT"
]

# =========================
# DATA FUNCTIONS
# =========================

def get_ohlcv(symbol):
    data = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
    df = pd.DataFrame(data, columns=["ts","open","high","low","close","volume"])

    df["ema_fast"] = df["close"].ewm(span=9).mean()
    df["ema_slow"] = df["close"].ewm(span=21).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
    df["vol_ma"] = df["volume"].rolling(20).mean()

    return df.dropna()

def rank_by_volatility():
    scored = []
    for s in SYMBOLS:
        try:
            df = get_ohlcv(s)
            atr = df["atr"].iloc[-1]
            price = df["close"].iloc[-1]
            score = atr / price
            scored.append((s, score))
        except:
            continue

    scored.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in scored[:10]]

# =========================
# TRADING ENGINE
# =========================

def evaluate_entry(symbol):
    df = get_ohlcv(symbol)
    last = df.iloc[-1]

    strength = 0

    if last["ema_fast"] > last["ema_slow"]:
        strength += 1.5

    if last["rsi"] > 58:
        strength += 1.3

    if last["volume"] > last["vol_ma"] * 1.2:
        strength += 1.5

    recent_high = df["high"].rolling(12).max().iloc[-2]
    if last["close"] > recent_high:
        strength += 2

    volatility = last["atr"] / last["close"]
    strength += volatility * 20

    if strength < 3.5:
        return None

    return last

def open_position(symbol, data):
    global balance, aggression, trades

    if len(positions) >= MAX_POSITIONS:
        return

    risk_percent = min(BASE_RISK * aggression, MAX_RISK)
    size = balance * risk_percent

    entry = data["close"]
    atr = data["atr"]

    positions[symbol] = {
        "entry": entry,
        "size": size,
        "tp": entry + (atr * TP_MULTIPLIER),
        "sl": entry - (atr * SL_MULTIPLIER),
        "time": time.time()
    }

    recent_signals.append(f"BUY {symbol} @ {round(entry,4)}")

def manage_positions():
    global balance, wins, losses, trades, aggression

    for symbol in list(positions.keys()):
        df = get_ohlcv(symbol)
        price = df["close"].iloc[-1]

        pos = positions[symbol]

        if time.time() - pos["time"] < MIN_HOLD_SECONDS:
            continue

        pnl = 0

        if price >= pos["tp"]:
            pnl = pos["size"] * 0.03
        elif price <= pos["sl"]:
            pnl = -pos["size"] * 0.02
        else:
            continue

        balance += pnl
        trades += 1

        if pnl > 0:
            wins += 1
            aggression *= 1.25
        else:
            losses += 1
            aggression *= 0.65

        aggression = max(0.6, min(aggression, 3.0))

        recent_signals.append(
            f"SELL {symbol} @ {round(price,4)} | PnL: {round(pnl,2)}"
        )

        del positions[symbol]

def trading_loop():
    while True:
        try:
            volatile = rank_by_volatility()

            for symbol in volatile:
                if symbol not in positions:
                    data = evaluate_entry(symbol)
                    if data is not None:
                        open_position(symbol, data)

            manage_positions()

        except Exception as e:
            print("Error:", e)

        time.sleep(SCAN_DELAY)

# =========================
# FLASK APP
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    equity = balance
    win_rate = (wins / trades * 100) if trades > 0 else 0

    return jsonify({
        "Mode": "NUCLEAR AI v3",
        "Equity": round(equity,2),
        "Cash": round(balance,2),
        "Trades": trades,
        "Wins": wins,
        "Losses": losses,
        "Win Rate %": round(win_rate,2),
        "Aggression": round(aggression,2),
        "Open Positions": positions,
        "Recent Signals": recent_signals[-10:]
    })

# =========================
# START BOT THREAD
# =========================

thread = threading.Thread(target=trading_loop)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)