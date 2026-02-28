import asyncio
import json
import math
import statistics
from datetime import datetime

import requests
import websockets
from flask import Flask, render_template_string

app = Flask(__name__)

START_BALANCE = 50.0

account = {
    "balance": START_BALANCE,
    "equity": START_BALANCE,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "aggression": 0.18,
    "drawdown": 0.0,
}

positions = {}
signals = []
price_data = {}
confidence_scores = {}
win_streak = 0
loss_streak = 0

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

# ---------------------------
# Indicator Functions
# ---------------------------

def ema(values, period):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val

def rsi(values, period=14):
    if len(values) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, period+1):
        diff = values[-i] - values[-i-1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains)/period if gains else 0.0001
    avg_loss = sum(losses)/period if losses else 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(values, period=14):
    if len(values) < period+1:
        return 0
    trs = [abs(values[-i] - values[-i-1]) for i in range(1, period+1)]
    return sum(trs) / period

# ---------------------------
# Trading Logic
# ---------------------------

def evaluate_symbol(symbol):
    global account
    prices = price_data.get(symbol, [])
    if len(prices) < 50:
        return

    ema_fast = ema(prices[-30:], 9)
    ema_slow = ema(prices[-30:], 21)
    current_rsi = rsi(prices)
    current_atr = atr(prices)

    volume_factor = 1  # placeholder (can upgrade later)

    confidence = 0

    if ema_fast and ema_slow and ema_fast > ema_slow:
        confidence += 30
    if 55 < current_rsi < 72:
        confidence += 25
    if current_atr > statistics.mean(prices[-20:]) * 0.002:
        confidence += 25
    confidence += 20  # base momentum score

    confidence_scores[symbol] = confidence

    if (
        confidence >= 75
        and symbol not in positions
        and len(positions) < 5
    ):
        enter_trade(symbol, prices[-1], current_atr)

def enter_trade(symbol, price, atr_val):
    global account

    risk_amount = account["balance"] * account["aggression"]
    size = risk_amount / price

    stop = price - (atr_val * 1.5)
    target = price + (atr_val * 2)

    positions[symbol] = {
        "entry": price,
        "size": size,
        "stop": stop,
        "target": target,
    }

    account["balance"] -= risk_amount

    signals.append(f"{datetime.now().strftime('%H:%M:%S')} ENTRY {symbol}")

def update_positions():
    global account, win_streak, loss_streak

    for symbol in list(positions.keys()):
        price = price_data[symbol][-1]
        pos = positions[symbol]

        if price <= pos["stop"] or price >= pos["target"]:
            pnl = (price - pos["entry"]) * pos["size"]
            account["balance"] += pos["size"] * price
            account["trades"] += 1

            if pnl > 0:
                account["wins"] += 1
                win_streak += 1
                loss_streak = 0
                account["aggression"] = min(0.25, account["aggression"] + 0.02)
            else:
                account["losses"] += 1
                loss_streak += 1
                win_streak = 0
                account["aggression"] = max(0.10, account["aggression"] - 0.03)

            signals.append(f"{datetime.now().strftime('%H:%M:%S')} EXIT {symbol}")
            del positions[symbol]

    account["equity"] = account["balance"] + sum(
        (price_data[s][-1] - positions[s]["entry"]) * positions[s]["size"]
        for s in positions
    )

# ---------------------------
# WebSocket Live Feed
# ---------------------------

async def stream_prices():
    streams = "/".join([f"{s.lower()}@trade" for s in TOP_20])
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    async with websockets.connect(url) as ws:
        while True:
            data = json.loads(await ws.recv())
            symbol = data["data"]["s"]
            price = float(data["data"]["p"])

            price_data.setdefault(symbol, []).append(price)
            if len(price_data[symbol]) > 200:
                price_data[symbol].pop(0)

            evaluate_symbol(symbol)
            update_positions()

# ---------------------------
# UI
# ---------------------------

@app.route("/")
def dashboard():
    winrate = (
        (account["wins"] / account["trades"]) * 100
        if account["trades"] > 0
        else 0
    )

    open_pos_html = ""
    for s, p in positions.items():
        open_pos_html += f"<div>{s} @ {round(p['entry'],4)}</div>"

    recent_html = ""
    for sig in signals[-10:]:
        recent_html += f"<div>{sig}</div>"

    return f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body {{
        background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
        color:white;
        font-family:Arial;
        padding:20px;
    }}
    .card {{
        background:rgba(255,255,255,0.05);
        padding:20px;
        border-radius:15px;
        margin-bottom:20px;
    }}
    h1 {{color:orange;}}
    </style>
    </head>
    <body>
    <h1>🔥 ELITE AI TRADER (LIVE)</h1>

    <div class="card">
        <h2>Account</h2>
        Equity: ${round(account["equity"],2)}<br>
        Balance: ${round(account["balance"],2)}<br>
        Trades: {account["trades"]}<br>
        Wins: {account["wins"]}<br>
        Losses: {account["losses"]}<br>
        Win Rate: {round(winrate,1)}%<br>
        Drawdown: {round(account["drawdown"],1)}%<br>
        Aggression: {round(account["aggression"]*100,1)}%
    </div>

    <div class="card">
        <h2>Open Positions</h2>
        {open_pos_html or "None"}
    </div>

    <div class="card">
        <h2>Recent Signals</h2>
        {recent_html}
    </div>

    </body>
    </html>
    """

# ---------------------------
# Start Background Loop
# ---------------------------

def start_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(stream_prices())

import threading
threading.Thread(target=start_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)