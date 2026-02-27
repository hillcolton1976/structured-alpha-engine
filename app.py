import ccxt
import pandas as pd
from flask import Flask, render_template_string

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================
SYMBOLS = ["BTC/USDT","ETH/USDT","XRP/USDT","BNB/USDT","ADA/USDT"]
TIMEFRAME_ENTRY = "1m"
TIMEFRAME_TREND = "5m"

TP_PERCENT = 0.004
SL_PERCENT = 0.0025

POSITION_SIZE = 10
START_BALANCE = 50

# ==============================
# STATE
# ==============================
balance = START_BALANCE
positions = {}
total_trades = 0
wins = 0
losses = 0
last_action = "Starting..."
recent_signals = []

exchange = ccxt.kraken({"enableRateLimit": True})

# ==============================
# DATA
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
# STRATEGY
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

    if not (
        df["ema9"].iloc[-1] > df["ema21"].iloc[-1] and
        df["ema9"].iloc[-2] <= df["ema21"].iloc[-2]
    ):
        return False

    if not (55 < df["rsi"].iloc[-1] < 70):
        return False

    if df["volume"].iloc[-1] < df["vol_avg"].iloc[-1] * 1.5:
        return False

    return True

# ==============================
# MANAGEMENT
# ==============================
def check_positions():
    global balance, wins, losses, total_trades, last_action

    for symbol in list(positions.keys()):
        df = get_df(symbol, TIMEFRAME_ENTRY)
        if df is None:
            continue

        current = df["close"].iloc[-1]
        entry = positions[symbol]["entry"]
        size = positions[symbol]["size"]

        change = (current - entry) / entry

        if change >= TP_PERCENT:
            balance += size + size * change
            wins += 1
            total_trades += 1
            last_action = f"TP hit {symbol}"
            del positions[symbol]

        elif change <= -SL_PERCENT:
            balance -= size * abs(change)
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
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body {
                background: #0f172a;
                color: #e2e8f0;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                padding: 20px;
            }
            .card {
                background: #1e293b;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            }
            h1 { color: #38bdf8; }
            h2 { color: #a78bfa; margin-bottom: 10px; }
            .stat { font-size: 18px; margin: 5px 0; }
        </style>
    </head>
    <body>

    <h1>🚀 Hybrid Momentum Engine</h1>

    <div class="card">
        <div class="stat"><b>Balance:</b> ${{balance}}</div>
        <div class="stat"><b>ROI:</b> {{roi}}%</div>
        <div class="stat"><b>Last Action:</b> {{last_action}}</div>
    </div>

    <div class="card">
        <h2>Performance</h2>
        <div class="stat">Trades: {{total_trades}}</div>
        <div class="stat">Wins: {{wins}}</div>
        <div class="stat">Losses: {{losses}}</div>
        <div class="stat">Win Rate: {{win_rate}}%</div>
    </div>

    <div class="card">
        <h2>Open Positions</h2>
        {% for sym,pos in positions.items() %}
            <div>{{sym}} @ {{pos.entry}}</div>
        {% else %}
            <div>No open positions</div>
        {% endfor %}
    </div>

    <div class="card">
        <h2>Recent Signals</h2>
        {% for s in signals %}
            <div>{{s}}</div>
        {% else %}
            <div>No signals yet</div>
        {% endfor %}
    </div>

    </body>
    </html>
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