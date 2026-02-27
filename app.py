import ccxt
import pandas as pd
import time
from flask import Flask, render_template_string

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================
SYMBOLS = ["BTC/USDT","ETH/USDT","XRP/USDT","BNB/USDT","ADA/USDT"]
TIMEFRAME_ENTRY = "1m"
TIMEFRAME_TREND = "5m"

TP_PERCENT = 0.004      # 0.4%
SL_PERCENT = 0.0025     # 0.25%
TRAIL_PERCENT = 0.0025

POSITION_SIZE = 10
START_BALANCE = 50

# ==============================
# GLOBAL STATE
# ==============================
balance = START_BALANCE
positions = {}
total_trades = 0
wins = 0
losses = 0
last_action = "Starting..."
recent_signals = []

exchange = ccxt.kraken({
    "enableRateLimit": True
})

# ==============================
# DATA FETCH
# ==============================
def get_df(symbol, timeframe, limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return None

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp","open","high","low","close","volume"]
        )

        if len(df) < 50:
            return None

        df["ema9"] = df["close"].ewm(span=9).mean()
        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()

        df["rsi"] = compute_rsi(df["close"])
        df["vol_avg"] = df["volume"].rolling(20).mean()

        return df
    except:
        return None

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ==============================
# STRATEGY LOGIC
# ==============================
def trend_filter(symbol):
    df = get_df(symbol, TIMEFRAME_TREND)
    if df is None:
        return False
    return df["ema50"].iloc[-1] > df["ema200"].iloc[-1]

def momentum_entry(symbol):
    df = get_df(symbol, TIMEFRAME_ENTRY)
    if df is None:
        return False

    # fresh EMA cross
    if not (
        df["ema9"].iloc[-1] > df["ema21"].iloc[-1] and
        df["ema9"].iloc[-2] <= df["ema21"].iloc[-2]
    ):
        return False

    # RSI filter
    if not (55 < df["rsi"].iloc[-1] < 70):
        return False

    # volume spike
    if df["volume"].iloc[-1] < df["vol_avg"].iloc[-1] * 1.5:
        return False

    return True

# ==============================
# TRADE MANAGEMENT
# ==============================
def check_positions():
    global balance, wins, losses, total_trades, last_action

    for symbol in list(positions.keys()):
        df = get_df(symbol, TIMEFRAME_ENTRY)
        if df is None:
            continue

        current_price = df["close"].iloc[-1]
        entry = positions[symbol]["entry"]
        size = positions[symbol]["size"]

        change = (current_price - entry) / entry

        # Take Profit
        if change >= TP_PERCENT:
            profit = size * change
            balance += size + profit
            wins += 1
            total_trades += 1
            last_action = f"TP hit {symbol}"
            del positions[symbol]

        # Stop Loss
        elif change <= -SL_PERCENT:
            loss_amount = size * abs(change)
            balance -= loss_amount
            losses += 1
            total_trades += 1
            last_action = f"SL hit {symbol}"
            del positions[symbol]

def evaluate():
    global balance, last_action

    check_positions()

    if balance < POSITION_SIZE:
        return

    for symbol in SYMBOLS:
        if symbol in positions:
            continue

        if trend_filter(symbol) and momentum_entry(symbol):
            df = get_df(symbol, TIMEFRAME_ENTRY)
            if df is None:
                continue

            price = df["close"].iloc[-1]

            positions[symbol] = {
                "entry": price,
                "size": POSITION_SIZE
            }

            balance -= POSITION_SIZE
            last_action = f"Entered {symbol}"
            recent_signals.append(symbol)
            break

# ==============================
# DASHBOARD
# ==============================
@app.route("/")
def dashboard():
    evaluate()

    roi = ((balance - START_BALANCE) / START_BALANCE) * 100
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    return render_template_string("""
    <body style="background:black;color:#00ff00;font-family:monospace">
    <h1>🚀 Hybrid Momentum Engine</h1>

    <h3>Balance: ${{balance}}</h3>
    <p>ROI: {{roi}}%</p>
    <p>Last Action: {{last_action}}</p>

    <h2>Stats</h2>
    <p>Trades: {{total_trades}}</p>
    <p>Wins: {{wins}}</p>
    <p>Losses: {{losses}}</p>
    <p>Win Rate: {{win_rate}}%</p>

    <h2>Open Positions</h2>
    {% for sym,pos in positions.items() %}
        <p>{{sym}} @ {{pos.entry}}</p>
    {% endfor %}

    <h2>Recent Signals</h2>
    {% for s in signals %}
        <p>{{s}}</p>
    {% endfor %}
    </body>
    """,
    balance=round(balance,2),
    roi=round(roi,2),
    last_action=last_action,
    total_trades=total_trades,
    wins=wins,
    losses=losses,
    win_rate=round(win_rate,2),
    positions=positions,
    signals=recent_signals[-5:]
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)