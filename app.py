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

TIMEFRAME = "1m"
START_BALANCE = 50
RISK_BASE = 0.15
TP_MULTIPLIER = 1.5
SL_MULTIPLIER = 1.0
MAX_POSITIONS = 3

# =============================
# EXCHANGE (PUBLIC ONLY)
# =============================

exchange = ccxt.binanceus({
    "enableRateLimit": True
})

# =============================
# GLOBAL STATE
# =============================

cash = START_BALANCE
equity = START_BALANCE
wins = 0
losses = 0
trades = 0
risk_modifier = 1.0

open_positions = {}
recent_signals = []

# =============================
# UTILS
# =============================

def get_symbols():
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and markets[s]["active"]]
    return symbols[:30]

def indicators(df):
    df["ema_fast"] = df["close"].ewm(span=9).mean()
    df["ema_slow"] = df["close"].ewm(span=21).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["vol_ma"] = df["volume"].rolling(20).mean()
    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()
    return df

def strength_score(df):
    last = df.iloc[-1]
    score = 0
    if last["ema_fast"] > last["ema_slow"]:
        score += 1
    if last["rsi"] > 55:
        score += 1
    if last["volume"] > last["vol_ma"]:
        score += 1
    return score

# =============================
# TRADING LOGIC
# =============================

def trade():
    global cash, equity, wins, losses, trades, risk_modifier

    symbols = get_symbols()
    ranked = []

    for symbol in symbols:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=50)
            df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])
            df = indicators(df)
            ranked.append((symbol, df, strength_score(df)))
        except:
            continue

    ranked.sort(key=lambda x: x[2], reverse=True)
    top_symbols = ranked[:10]

    # ENTRY
    for symbol, df, score in top_symbols:
        if symbol in open_positions or len(open_positions) >= MAX_POSITIONS:
            continue

        last = df.iloc[-1]
        momentum = last["ema_fast"] > last["ema_slow"]
        rsi_push = last["rsi"] > 52

        if momentum and rsi_push:
            risk_amount = cash * RISK_BASE * risk_modifier
            qty = risk_amount / last["close"]

            open_positions[symbol] = {
                "entry": last["close"],
                "qty": qty,
                "atr": last["atr"]
            }

            cash -= risk_amount
            recent_signals.append(f"BUY {symbol} @ {round(last['close'],4)}")

    # EXIT
    for symbol in list(open_positions.keys()):
        pos = open_positions[symbol]
        ticker = exchange.fetch_ticker(symbol)
        price = ticker["last"]

        tp = pos["entry"] + (pos["atr"] * TP_MULTIPLIER)
        sl = pos["entry"] - (pos["atr"] * SL_MULTIPLIER)

        if price >= tp or price <= sl:
            pnl = (price - pos["entry"]) * pos["qty"]
            cash += pos["qty"] * price
            trades += 1

            if pnl > 0:
                wins += 1
                risk_modifier *= 1.1
            else:
                losses += 1
                risk_modifier *= 0.9

            recent_signals.append(f"SELL {symbol} @ {round(price,4)} | PnL: {round(pnl,2)}")
            del open_positions[symbol]

    equity = cash + sum(
        exchange.fetch_ticker(s)["last"] * open_positions[s]["qty"]
        for s in open_positions
    )

# =============================
# BACKGROUND LOOP
# =============================

def loop():
    while True:
        try:
            trade()
        except:
            pass
        time.sleep(15)

threading.Thread(target=loop, daemon=True).start()

# =============================
# DASHBOARD
# =============================

TEMPLATE = """
<html>
<head>
<style>
body { background:#0f172a; color:white; font-family:Arial; padding:20px;}
.card { background:#1e293b; padding:15px; margin-bottom:15px; border-radius:10px;}
.green { color:#22c55e;}
.red { color:#ef4444;}
</style>
<meta http-equiv="refresh" content="5">
</head>
<body>

<h2>🔥 Adaptive AI Trader</h2>

<div class="card">
<b>Equity:</b> ${{equity}}<br>
<b>Cash:</b> ${{cash}}<br>
<b>Trades:</b> {{trades}}<br>
<b>Wins:</b> <span class="green">{{wins}}</span><br>
<b>Losses:</b> <span class="red">{{losses}}</span><br>
<b>Win Rate:</b> {{winrate}}%
</div>

<div class="card">
<h3>Open Positions</h3>
{% for s,p in positions.items() %}
{{s}} — Entry: {{p["entry"]}}<br>
{% else %}
None
{% endfor %}
</div>

<div class="card">
<h3>Recent Signals</h3>
{% for r in signals[-10:] %}
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