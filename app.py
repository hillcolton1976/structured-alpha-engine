import ccxt
import pandas as pd
import numpy as np
import time
import threading
from flask import Flask, render_template_string

# =========================
# CONFIG
# =========================

START_BALANCE = 50
TIMEFRAME = "1m"
HIGHER_TIMEFRAME = "5m"

BASE_RISK = 0.25
MAX_RISK = 0.45

MAX_POSITIONS = 6
SCAN_DELAY = 5
COOLDOWN_AFTER_LOSS = 30

ENTRY_SCORE_THRESHOLD = 3

# =========================
# STATE
# =========================

balance = START_BALANCE
wins = 0
losses = 0
trades = 0
aggression = 1.2
cooldown_until = 0

positions = {}
recent_signals = []

# =========================
# EXCHANGE
# =========================

exchange = ccxt.binanceus({
    "enableRateLimit": True
})

def get_top_symbols():
    markets = exchange.load_markets()
    usdt_pairs = [
        s for s in markets
        if "/USDT" in s and markets[s]["active"]
    ]
    return usdt_pairs[:50]

SYMBOLS = get_top_symbols()

# =========================
# DATA
# =========================

def fetch_df(symbol, tf):
    data = exchange.fetch_ohlcv(symbol, tf, limit=100)
    df = pd.DataFrame(data, columns=["ts","open","high","low","close","volume"])

    df["ema9"] = df["close"].ewm(span=9).mean()
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
    df["vol_ma"] = df["volume"].rolling(20).mean()

    return df.dropna()

# =========================
# SCORING
# =========================

def score_symbol(symbol):
    df1 = fetch_df(symbol, TIMEFRAME)
    df5 = fetch_df(symbol, HIGHER_TIMEFRAME)

    last1 = df1.iloc[-1]
    last5 = df5.iloc[-1]

    score = 0

    if last1["ema9"] > last1["ema21"]:
        score += 1

    if last1["ema21"] > last1["ema50"]:
        score += 1

    if last5["ema9"] > last5["ema21"]:
        score += 1

    if last1["rsi"] > 52:
        score += 1

    if last1["volume"] > last1["vol_ma"]:
        score += 1

    if last1["atr"] / last1["close"] > 0.0015:
        score += 1

    return score, last1

# =========================
# TRADES
# =========================

def open_trade(symbol, data):
    global balance

    risk = min(BASE_RISK * aggression, MAX_RISK)
    size = balance * risk

    entry = data["close"]
    atr = data["atr"]

    tp = entry + atr * 1.8
    sl = entry - atr * 1.1

    positions[symbol] = {
        "entry": entry,
        "size": size,
        "tp": tp,
        "sl": sl,
        "time": time.time()
    }

    recent_signals.append(f"🟢 BUY {symbol} @ {round(entry,4)}")

def manage_trades():
    global balance, wins, losses, trades, aggression, cooldown_until

    for symbol in list(positions.keys()):
        df = fetch_df(symbol, TIMEFRAME)
        price = df["close"].iloc[-1]
        pos = positions[symbol]

        pnl = 0

        if price >= pos["tp"]:
            pnl = pos["size"] * 0.025
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
            aggression *= 0.8
            cooldown_until = time.time() + COOLDOWN_AFTER_LOSS

        aggression = max(0.8, min(aggression, 4))

        emoji = "🟢" if pnl > 0 else "🔴"
        recent_signals.append(f"{emoji} SELL {symbol} | {round(pnl,2)}")

        del positions[symbol]

# =========================
# LOOP
# =========================

def trading_loop():
    global cooldown_until

    while True:
        try:
            if time.time() > cooldown_until:

                ranked = []

                for symbol in SYMBOLS:
                    if symbol not in positions:
                        score, data = score_symbol(symbol)
                        if score >= ENTRY_SCORE_THRESHOLD:
                            ranked.append((score, symbol, data))

                ranked.sort(reverse=True)

                for r in ranked[:3]:
                    if len(positions) < MAX_POSITIONS:
                        open_trade(r[1], r[2])

            manage_trades()

        except Exception as e:
            print("Error:", e)

        time.sleep(SCAN_DELAY)

# =========================
# UI
# =========================

app = Flask(__name__)

@app.route("/")
def dashboard():
    win_rate = (wins / trades * 100) if trades else 0

    return render_template_string("""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body { background:#111827; color:#e5e7eb; font-family:Arial; padding:20px; }
    .card { background:#1f2937; padding:18px; border-radius:12px; margin-bottom:15px; }
    .big { font-size:22px; font-weight:bold; }
    .green{color:#22c55e;}
    .red{color:#ef4444;}
    .yellow{color:#facc15;}
    </style>
    </head>
    <body>
    <h2>🚀 Aggressive Adaptive AI Trader</h2>

    <div class="card">
    <div class="big">Equity: ${{equity}}</div>
    <div>Trades: {{trades}}</div>
    <div class="green">Wins: {{wins}}</div>
    <div class="red">Losses: {{losses}}</div>
    <div class="yellow">Win Rate: {{win_rate}}%</div>
    <div>Aggression Multiplier: {{aggression}}</div>
    </div>

    <div class="card">
    <div class="big">Open Positions</div>
    {% for sym,p in positions.items() %}
        <div>{{sym}} @ {{p["entry"]}}</div>
    {% endfor %}
    </div>

    <div class="card">
    <div class="big">Recent Signals</div>
    {% for s in signals %}
        <div>{{s}}</div>
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

thread = threading.Thread(target=trading_loop)
thread.daemon = True
thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)