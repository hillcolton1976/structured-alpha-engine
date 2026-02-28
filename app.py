import ccxt
import pandas as pd
import numpy as np
import time
import threading
from flask import Flask, render_template_string

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

SYMBOLS = [
    "BTC/USDT","ETH/USDT","SOL/USDT","BNB/USDT","XRP/USDT",
    "DOGE/USDT","AVAX/USDT","LINK/USDT","ADA/USDT","MATIC/USDT"
]

# =========================
# DATA
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

# =========================
# STRATEGY
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

    if strength < 3:
        return None

    return last

def open_position(symbol, data):
    global balance, aggression

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

    recent_signals.append(f"🟢 BUY {symbol} @ {round(entry,4)}")

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
            aggression *= 1.2
        else:
            losses += 1
            aggression *= 0.7

        aggression = max(0.6, min(aggression, 3))

        emoji = "🟢" if pnl > 0 else "🔴"
        recent_signals.append(f"{emoji} SELL {symbol} | PnL: {round(pnl,2)}")

        del positions[symbol]

def trading_loop():
    while True:
        try:
            for symbol in SYMBOLS:
                if symbol not in positions:
                    data = evaluate_entry(symbol)
                    if data is not None:
                        open_position(symbol, data)

            manage_positions()

        except Exception as e:
            print("Error:", e)

        time.sleep(SCAN_DELAY)

# =========================
# FLASK UI
# =========================

app = Flask(__name__)

@app.route("/")
def dashboard():
    win_rate = (wins / trades * 100) if trades > 0 else 0

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            background: linear-gradient(135deg,#0f172a,#020617);
            color: white;
            font-family: Arial;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            padding: 18px;
            border-radius: 14px;
            margin-bottom: 15px;
            box-shadow: 0 0 20px rgba(0,0,0,0.4);
        }
        .big {
            font-size: 22px;
            font-weight: bold;
        }
        .green { color:#22c55e; }
        .red { color:#ef4444; }
        .yellow { color:#facc15; }
        .positions div {
            margin-bottom:6px;
        }
        .signals {
            max-height:200px;
            overflow-y:auto;
            font-size:14px;
        }
    </style>
    </head>
    <body>

    <h2>🔥 NUCLEAR AI Trader</h2>

    <div class="card">
        <div class="big">Equity: ${{ equity }}</div>
        <div>Trades: {{ trades }}</div>
        <div class="green">Wins: {{ wins }}</div>
        <div class="red">Losses: {{ losses }}</div>
        <div class="yellow">Win Rate: {{ win_rate }}%</div>
        <div>Aggression: {{ aggression }}</div>
    </div>

    <div class="card positions">
        <div class="big">Open Positions</div>
        {% if positions %}
            {% for sym, p in positions.items() %}
                <div>{{ sym }} @ {{ p['entry'] }}</div>
            {% endfor %}
        {% else %}
            <div>None</div>
        {% endif %}
    </div>

    <div class="card signals">
        <div class="big">Recent Signals</div>
        {% for s in signals %}
            <div>{{ s }}</div>
        {% endfor %}
    </div>

    </body>
    </html>
    """,
    equity=round(balance,2),
    trades=trades,
    wins=wins,
    losses=losses,
    win_rate=round(win_rate,2),
    aggression=round(aggression,2),
    positions=positions,
    signals=recent_signals[-12:]
    )

# =========================

thread = threading.Thread(target=trading_loop)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)