import ccxt
import pandas as pd
import numpy as np
import threading
import time
from flask import Flask, render_template_string

app = Flask(__name__)

# =============================
# CONFIG
# =============================

TIMEFRAME = "5m"
START_BALANCE = 50
RISK_BASE = 0.12
TP_MULTIPLIER = 2.2
SL_MULTIPLIER = 1.2
MAX_POSITIONS = 2
MIN_HOLD_SECONDS = 90
COOLDOWN_SECONDS = 120

# =============================
# EXCHANGE (PUBLIC ONLY)
# =============================

exchange = ccxt.binanceus({
    "enableRateLimit": True
})

# =============================
# STATE
# =============================

cash = START_BALANCE
equity = START_BALANCE
wins = 0
losses = 0
trades = 0
risk_modifier = 1.0
loss_streak = 0

open_positions = {}
recent_signals = []
cooldowns = {}

# =============================
# INDICATORS
# =============================

def calculate_indicators(df):
    df["ema_fast"] = df["close"].ewm(span=9).mean()
    df["ema_slow"] = df["close"].ewm(span=21).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.rolling(14).mean() / loss.rolling(14).mean()
    df["rsi"] = 100 - (100 / (1 + rs))

    df["tr"] = np.maximum(
        df["high"] - df["low"],
        np.maximum(
            abs(df["high"] - df["close"].shift()),
            abs(df["low"] - df["close"].shift())
        )
    )
    df["atr"] = df["tr"].rolling(14).mean()

    df["vol_ma"] = df["volume"].rolling(20).mean()

    return df

# =============================
# SYMBOL SELECTION
# =============================

def get_symbols():
    markets = exchange.load_markets()
    symbols = [
        s for s in markets
        if "/USDT" in s and markets[s]["active"]
    ]
    return symbols[:25]

# =============================
# TRADING ENGINE
# =============================

def trade():
    global cash, equity, wins, losses, trades, risk_modifier, loss_streak

    symbols = get_symbols()
    ranked = []

    for symbol in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
            df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])
            df.columns = ["time","open","high","low","close","volume"]
            df = calculate_indicators(df)

            last = df.iloc[-1]

            strength = 0
            if last["ema_fast"] > last["ema_slow"]:
                strength += 1
            if last["rsi"] > 55:
                strength += 1
            if last["volume"] > last["vol_ma"]:
                strength += 1

            ranked.append((symbol, df, strength))
        except:
            continue

    ranked.sort(key=lambda x: x[2], reverse=True)
    top = ranked[:8]

    # ===== ENTRY =====
    for symbol, df, score in top:

        if symbol in open_positions:
            continue

        if len(open_positions) >= MAX_POSITIONS:
            break

        if score < 3:
            continue

        if symbol in cooldowns and time.time() < cooldowns[symbol]:
            continue

        last = df.iloc[-1]
        risk_amount = cash * RISK_BASE * risk_modifier
        qty = risk_amount / last["close"]

        open_positions[symbol] = {
            "entry": last["close"],
            "qty": qty,
            "atr": last["atr"],
            "time": time.time()
        }

        cash -= risk_amount
        recent_signals.append(f"BUY {symbol} @ {round(last['close'],4)}")

    # ===== EXIT =====
    for symbol in list(open_positions.keys()):
        pos = open_positions[symbol]
        ticker = exchange.fetch_ticker(symbol)
        price = ticker["last"]

        held_time = time.time() - pos["time"]
        if held_time < MIN_HOLD_SECONDS:
            continue

        tp = pos["entry"] + (pos["atr"] * TP_MULTIPLIER)
        sl = pos["entry"] - (pos["atr"] * SL_MULTIPLIER)

        if price >= tp or price <= sl:
            pnl = (price - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * price
            trades += 1

            if pnl > 0:
                wins += 1
                risk_modifier *= 1.05
                loss_streak = 0
            else:
                losses += 1
                risk_modifier *= 0.9
                loss_streak += 1

            cooldowns[symbol] = time.time() + COOLDOWN_SECONDS
            recent_signals.append(f"SELL {symbol} @ {round(price,4)} | PnL: {round(pnl,2)}")

            del open_positions[symbol]

    equity = cash + sum(
        exchange.fetch_ticker(s)["last"] * open_positions[s]["qty"]
        for s in open_positions
    )

# =============================
# LOOP
# =============================

def loop():
    while True:
        try:
            trade()
        except:
            pass
        time.sleep(20)

threading.Thread(target=loop, daemon=True).start()

# =============================
# DASHBOARD
# =============================

TEMPLATE = """
<html>
<head>
<style>
body { background:#0f172a; color:white; font-family:Arial; padding:20px;}
.card { background:#1e293b; padding:20px; margin-bottom:15px; border-radius:12px;}
.green { color:#22c55e;}
.red { color:#ef4444;}
</style>
<meta http-equiv="refresh" content="5">
</head>
<body>

<h2>🔥 Adaptive AI Trader v2</h2>

<div class="card">
<h3>Account</h3>
Equity: <b>${{equity}}</b><br>
Cash: ${{cash}}<br>
Trades: {{trades}}<br>
Wins: <span class="green">{{wins}}</span><br>
Losses: <span class="red">{{losses}}</span><br>
Win Rate: {{winrate}}%
</div>

<div class="card">
<h3>Open Positions</h3>
{% if positions %}
{% for s,p in positions.items() %}
<b>{{s}}</b><br>
Entry: {{p["entry"]}}<br><br>
{% endfor %}
{% else %}
None
{% endif %}
</div>

<div class="card">
<h3>Recent Signals</h3>
{% for r in signals[-8:] %}
{{r}}<br>
{% endfor %}
</div>

</body>
</html>
"""

@app.route("/")
def dashboard():
    winrate = round((wins/trades)*100,2) if trades else 0
    return render_template_string(
        TEMPLATE,
        equity=round(equity,2),
        cash=round(cash,2),
        wins=wins,
        losses=losses,
        trades=trades,
        winrate=winrate,
        positions=open_positions,
        signals=recent_signals
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)