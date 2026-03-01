from flask import Flask
import requests
import random
import time
from datetime import datetime

app = Flask(__name__)

START_BALANCE = 50.0
cash = START_BALANCE
positions = {}
trade_history = []
level = 1
win_count = 0
loss_count = 0

MAX_POSITIONS = 7
MIN_POSITIONS = 3

def safe_request(url):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        return None
    return None

def get_market():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = safe_request(url)
    if not data:
        return []

    usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)

    top = sorted_pairs[:35]

    coins = []
    for c in top:
        try:
            price = float(c["lastPrice"])
            change = float(c["priceChangePercent"])
            volume = float(c["quoteVolume"])
            score = change * 0.6 + (volume / 100000000)
            coins.append({
                "symbol": c["symbol"],
                "price": price,
                "change": change,
                "score": score
            })
        except:
            continue

    coins.sort(key=lambda x: x["score"], reverse=True)
    return coins

def total_equity(market):
    total = cash
    for sym, pos in positions.items():
        price = next((c["price"] for c in market if c["symbol"] == sym), pos["entry"])
        total += pos["amount"] * price
    return total

def adjust_level(equity):
    global level
    if equity > 100:
        level = 2
    if equity > 200:
        level = 3
    if equity > 400:
        level = 4

def trade_logic(market):
    global cash, win_count, loss_count

    if not market:
        return

    equity = total_equity(market)
    adjust_level(equity)

    desired_positions = min(MAX_POSITIONS, max(MIN_POSITIONS, int(level + 2)))

    # SELL LOGIC
    for sym in list(positions.keys()):
        price = next((c["price"] for c in market if c["symbol"] == sym), None)
        if not price:
            continue

        entry = positions[sym]["entry"]
        pnl = (price - entry) / entry * 100

        if pnl <= -4 or pnl >= 6:
            amount = positions[sym]["amount"]
            cash += amount * price

            if pnl > 0:
                win_count += 1
            else:
                loss_count += 1

            trade_history.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "symbol": sym,
                "pnl": round(pnl, 2)
            })

            del positions[sym]

    # BUY LOGIC
    open_slots = desired_positions - len(positions)
    if open_slots > 0 and cash > 5:
        for coin in market:
            if coin["symbol"] not in positions:
                allocation = (cash / open_slots) * (1 + level * 0.1)
                if allocation > cash:
                    allocation = cash
                amount = allocation / coin["price"]
                positions[coin["symbol"]] = {
                    "entry": coin["price"],
                    "amount": amount
                }
                cash -= allocation
                open_slots -= 1
                if open_slots <= 0:
                    break

@app.route("/")
def dashboard():
    market = get_market()
    trade_logic(market)

    equity = total_equity(market)

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="15">
    <style>
        body { background:#0f172a; color:white; font-family:Arial; }
        table { width:100%; border-collapse:collapse; }
        th, td { padding:8px; text-align:center; }
        th { background:#1e293b; }
        tr:nth-child(even) { background:#1e293b; }
        .green { color:#22c55e; }
        .red { color:#ef4444; }
        .card { background:#1e293b; padding:15px; margin:10px 0; border-radius:8px; }
    </style>
    </head>
    <body>
    <h1>🔥 ELITE AI TRADER – LIVE SIM</h1>

    <div class="card">
        <h2>Account</h2>
        <p>Level: """ + str(level) + """</p>
        <p>Cash: $""" + str(round(cash,2)) + """</p>
        <p>Total Equity: $""" + str(round(equity,2)) + """</p>
        <p>Wins: """ + str(win_count) + """ | Losses: """ + str(loss_count) + """</p>
    </div>

    <div class="card">
        <h2>Open Positions</h2>
        <table>
        <tr><th>Coin</th><th>Entry</th><th>Current</th><th>$ Value</th></tr>
    """

    for sym, pos in positions.items():
        current = next((c["price"] for c in market if c["symbol"] == sym), pos["entry"])
        value = pos["amount"] * current
        html += f"<tr><td>{sym}</td><td>{round(pos['entry'],4)}</td><td>{round(current,4)}</td><td>${round(value,2)}</td></tr>"

    html += """
        </table>
    </div>

    <div class="card">
        <h2>Trade History</h2>
        <table>
        <tr><th>Time</th><th>Coin</th><th>PNL %</th></tr>
    """

    for t in reversed(trade_history[-10:]):
        color = "green" if t["pnl"] > 0 else "red"
        html += f"<tr><td>{t['time']}</td><td>{t['symbol']}</td><td class='{color}'>{t['pnl']}%</td></tr>"

    html += """
        </table>
    </div>

    </body>
    </html>
    """

    return html

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)