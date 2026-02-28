import ccxt
import pandas as pd
import time
from flask import Flask, jsonify

app = Flask(__name__)

# ===== CONFIG =====
TIMEFRAME = '1m'
MAX_POSITIONS = 3
RISK_PER_TRADE = 0.20
STOP_LOSS = 0.006
TAKE_PROFIT = 0.012
TRAILING_STOP = 0.005

# ===== EXCHANGE (PUBLIC ONLY) =====
exchange = ccxt.binanceus()

# ===== STATE =====
state = {
    "cash": 50.0,
    "equity": 50.0,
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "positions": {},
    "signals": []
}

# ===== COINS TO TRADE =====
SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "AVAX/USDT",
    "ADA/USDT",
    "LINK/USDT"
]

# ===== INDICATORS =====
def indicators(df):
    df["ema_fast"] = df["close"].ewm(span=9).mean()
    df["ema_slow"] = df["close"].ewm(span=21).mean()
    df["rsi"] = rsi(df["close"], 14)
    df["vol_ma"] = df["volume"].rolling(20).mean()
    return df

def rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ===== FETCH DATA =====
def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
    return indicators(df)

# ===== UPDATE EQUITY =====
def update_equity():
    total = state["cash"]
    for symbol, pos in state["positions"].items():
        price = exchange.fetch_ticker(symbol)["last"]
        total += pos["qty"] * price
    state["equity"] = round(total, 2)

# ===== BUY =====
def open_position(symbol, price):
    size = state["equity"] * RISK_PER_TRADE
    if state["cash"] < size:
        return
    qty = size / price
    state["positions"][symbol] = {
        "entry": price,
        "qty": qty,
        "trail_high": price
    }
    state["cash"] -= size
    state["signals"].append(f"BUY {symbol} @ {price}")

# ===== SELL =====
def close_position(symbol, price):
    pos = state["positions"][symbol]
    value = pos["qty"] * price
    pnl = value - (pos["qty"] * pos["entry"])

    state["cash"] += value
    state["trades"] += 1

    if pnl > 0:
        state["wins"] += 1
    else:
        state["losses"] += 1

    del state["positions"][symbol]
    state["signals"].append(f"SELL {symbol} @ {price} | PnL: {round(pnl,2)}")

# ===== STRATEGY LOOP =====
def trade():
    for symbol in SYMBOLS:
        df = get_data(symbol)
        last = df.iloc[-1]

        price = last["close"]

        # ===== MANAGE OPEN =====
        if symbol in state["positions"]:
            pos = state["positions"][symbol]

            # update trailing
            if price > pos["trail_high"]:
                pos["trail_high"] = price

            stop = pos["entry"] * (1 - STOP_LOSS)
            tp = pos["entry"] * (1 + TAKE_PROFIT)
            trail = pos["trail_high"] * (1 - TRAILING_STOP)

            if price <= stop or price >= tp or price <= trail:
                close_position(symbol, price)

        # ===== LOOK FOR ENTRY =====
        else:
            if len(state["positions"]) >= MAX_POSITIONS:
                continue

            momentum = last["ema_fast"] > last["ema_slow"]
            strong_rsi = 55 < last["rsi"] < 70
            volume_spike = last["volume"] > last["vol_ma"]

            if momentum and strong_rsi and volume_spike:
                open_position(symbol, price)

    update_equity()

# ===== API =====
@app.route("/")
def home():
    trade()
    winrate = 0
    if state["trades"] > 0:
        winrate = round((state["wins"] / state["trades"]) * 100, 1)

    return jsonify({
        "Cash": round(state["cash"],2),
        "Equity": state["equity"],
        "Open Positions": state["positions"],
        "Trades": state["trades"],
        "Wins": state["wins"],
        "Losses": state["losses"],
        "Win Rate %": winrate,
        "Recent Signals": state["signals"][-6:]
    })

if __name__ == "__main__":
    app.run()