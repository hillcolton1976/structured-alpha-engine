import requests
import math
import statistics
from flask import Flask, render_template_string
from datetime import datetime
import time
import threading

app = Flask(__name__)

START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH_SECONDS = 5

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

account = {
    "balance": START_BALANCE,
    "equity": START_BALANCE,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "aggression": 0.20,
    "drawdown": 0.0
}

price_data = {s: [] for s in TOP_20}
positions = {}
signals = []
peak_equity = START_BALANCE
win_streak = 0
loss_streak = 0

# ---------------------------
# DATA FETCH
# ---------------------------

def get_prices():
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        data = requests.get(url, timeout=10).json()
        prices = {}
        for item in data:
            if item["symbol"] in TOP_20:
                prices[item["symbol"]] = float(item["price"])
        return prices
    except:
        return {}

# ---------------------------
# SCORING ENGINE (ELITE)
# ---------------------------

def score_symbol(symbol):
    prices = price_data[symbol]
    if len(prices) < 6:
        return 0

    short_momentum = (prices[-1] - prices[-3]) / prices[-3]
    mid_momentum = (prices[-1] - prices[-6]) / prices[-6]

    volatility = statistics.stdev(prices[-6:]) if len(prices) >= 6 else 0

    trend = 1 if prices[-1] > statistics.mean(prices[-6:]) else -1

    score = (short_momentum * 3) + (mid_momentum * 2)
    score += volatility * 0.1
    score *= trend

    return round(score * 100, 4)

# ---------------------------
# TRADING LOGIC
# ---------------------------

def trade_logic():
    global peak_equity, win_streak, loss_streak

    prices = get_prices()
    if not prices:
        return

    for s in prices:
        price_data[s].append(prices[s])
        if len(price_data[s]) > 50:
            price_data[s].pop(0)

    scores = {s: score_symbol(s) for s in TOP_20}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Close weak positions
    for s in list(positions.keys()):
        if scores[s] < 0:
            entry = positions[s]["entry"]
            current = prices[s]
            pnl = (current - entry) / entry
            size = positions[s]["size"]
            profit = size * pnl

            account["balance"] += size + profit
            account["trades"] += 1

            if profit > 0:
                account["wins"] += 1
                win_streak += 1
                loss_streak = 0
                account["aggression"] = min(0.30, account["aggression"] + 0.01)
            else:
                account["losses"] += 1
                loss_streak += 1
                win_streak = 0
                account["aggression"] = max(0.10, account["aggression"] - 0.01)

            signals.append(f"{datetime.now().strftime('%H:%M:%S')} CLOSED {s} PnL: {round(profit,2)}")
            del positions[s]

    # Open strong positions
    for s, sc in ranked:
        if len(positions) >= MAX_POSITIONS:
            break
        if s not in positions and sc > 0.5:
            allocation = account["balance"] * account["aggression"]
            if allocation > 5:
                account["balance"] -= allocation
                positions[s] = {
                    "entry": prices[s],
                    "size": allocation
                }
                signals.append(f"{datetime.now().strftime('%H:%M:%S')} BUY {s} @ {prices[s]}")

    # Update equity
    equity = account["balance"]
    for s in positions:
        entry = positions[s]["entry"]
        current = prices[s]
        pnl = (current - entry) / entry
        equity += positions[s]["size"] * (1 + pnl)

    account["equity"] = round(equity,2)

    if equity > peak_equity:
        peak_equity = equity

    drawdown = (peak_equity - equity) / peak_equity
    account["drawdown"] = round(drawdown * 100,2)

# ---------------------------
# BACKGROUND LOOP
# ---------------------------

def engine_loop():
    while True:
        trade_logic()
        time.sleep(REFRESH_SECONDS)

threading.Thread(target=engine_loop, daemon=True).start()

# ---------------------------
# DASHBOARD
# ---------------------------

@app.route("/")
def dashboard():

    scores = {s: score_symbol(s) for s in TOP_20}
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    win_rate = 0
    if account["trades"] > 0:
        win_rate = round((account["wins"] / account["trades"]) * 100,2)

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body { font-family: Arial; background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); color:white; padding:20px; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
    .card { background:#1c2b36; padding:20px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.4); }
    h1 { color:#ffb347; }
    table { width:100%; }
    th, td { padding:6px; }
    </style>
    </head>
    <body>
    <h1>🔥 ELITE AI TRADER</h1>

    <div class="grid">

    <div class="card">
    <h3>Account</h3>
    Equity: ${{equity}}<br>
    Balance: ${{balance}}<br>
    Trades: {{trades}}<br>
    Wins: {{wins}}<br>
    Losses: {{losses}}<br>
    Win Rate: {{win_rate}}%<br>
    Drawdown: {{drawdown}}%<br>
    Aggression: {{aggression}}%
    </div>

    <div class="card">
    <h3>Open Positions</h3>
    {% if positions %}
    {% for s,p in positions.items() %}
    {{s}} - ${{p["size"]}}<br>
    {% endfor %}
    {% else %}
    None
    {% endif %}
    </div>

    <div class="card">
    <h3>Top 20 Momentum</h3>
    <table>
    <tr><th>Symbol</th><th>Score</th></tr>
    {% for s,sc in ranked %}
    <tr><td>{{s}}</td><td>{{sc}}</td></tr>
    {% endfor %}
    </table>
    </div>

    <div class="card">
    <h3>Recent Signals</h3>
    {% for sig in signals[-10:] %}
    {{sig}}<br>
    {% endfor %}
    </div>

    </div>
    </body>
    </html>
    """

    return render_template_string(
        html,
        equity=account["equity"],
        balance=account["balance"],
        trades=account["trades"],
        wins=account["wins"],
        losses=account["losses"],
        win_rate=win_rate,
        drawdown=account["drawdown"],
        aggression=round(account["aggression"]*100,2),
        positions=positions,
        ranked=ranked,
        signals=signals
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)