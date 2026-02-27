import ccxt
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50
TIMEFRAME = "5m"
CANDLE_LIMIT = 60
MAX_POSITIONS = 5

exchange = ccxt.kraken({
    "enableRateLimit": True
})

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
    symbols = [
        s for s in markets
        if "/USDT" in s and markets[s]["active"]
    ]
    return symbols[:50]

TOP_50 = get_top_50()

# =============================
# ENGINE
# =============================

def evaluate():
    global equity, cash, open_positions
    global last_action, total_trades, wins, losses

    for symbol in TOP_50:

        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
        except:
            continue

        if len(ohlcv) < 30:
            continue

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        price = df["close"].iloc[-1]

        # ================= EXIT =================
        if symbol in open_positions:
            if df["ema9"].iloc[-1] < df["ema21"].iloc[-1]:

                entry_price = open_positions[symbol]["entry"]
                size = open_positions[symbol]["size"]

                pnl = (price - entry_price) * size
                cash += size * price
                total_trades += 1

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                del open_positions[symbol]
                last_action = f"Exited {symbol}"
                continue

        # ================= ENTRY =================
        if len(open_positions) >= MAX_POSITIONS:
            continue

        if symbol not in open_positions:

            trend = df["ema21"].iloc[-1] > df["ema50"].iloc[-1]
            momentum = df["ema9"].iloc[-1] > df["ema21"].iloc[-1]

            if trend and momentum and cash > 1:

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
        try:
            ticker = exchange.fetch_ticker(symbol)
            equity += pos["size"] * ticker["last"]
        except:
            continue

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)