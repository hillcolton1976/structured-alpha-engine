from flask import Flask, render_template_string
import requests
import threading
import time
import statistics

app = Flask(__name__)

# -------------------------
# SETTINGS
# -------------------------
START_BALANCE = 50.0
balance = START_BALANCE
trades = 0
wins = 0
losses = 0

MAX_POSITIONS = 5
BASE_POSITION_SIZE = 10

# Smaller / more volatile coins
symbols = [
    "PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","JASMYUSDT",
    "SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","INJUSDT",
    "ORDIUSDT","RNDRUSDT","FETUSDT","GALAUSDT","BLURUSDT",
    "DYDXUSDT","IMXUSDT","OPUSDT","ARBUSDT","APTUSDT"
]

price_history = {s: [] for s in symbols}
positions = {}
aggression_multiplier = 1.0


# -------------------------
# GET LIVE PRICE
# -------------------------
def get_price(symbol):
    try:
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return None


# -------------------------
# EMA
# -------------------------
def ema(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    val = prices[0]
    for p in prices[1:]:
        val = p * k + val * (1 - k)
    return val


# -------------------------
# SCORE SYSTEM
# -------------------------
def calculate_scores():
    scores = {}

    for symbol in symbols:
        history = price_history[symbol]

        if len(history) < 20:
            scores[symbol] = 0
            continue

        if history[-5] == 0 or history[-15] == 0:
            scores[symbol] = 0
            continue

        short = (history[-1] - history[-5]) / history[-5]
        medium = (history[-1] - history[-15]) / history[-15]

        fast = ema(history[-20:], 5)
        slow = ema(history[-20:], 12)

        trend = 1 if fast and slow and fast > slow else -1

        volatility = statistics.pstdev(history[-15:]) if len(history[-15:]) > 5 else 0

        score = (short * 0.6 + medium * 0.4)
        score *= trend
        score *= (1 + volatility)

        scores[symbol] = round(score * 100, 2)

    return scores


# -------------------------
# TRADING LOOP
# -------------------------
def trader():
    global balance, trades, wins, losses, aggression_multiplier

    while True:

        for s in symbols:
            price = get_price(s)
            if price and price > 0:
                price_history[s].append(price)
                if len(price_history[s]) > 60:
                    price_history[s].pop(0)

        scores = calculate_scores()
        sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # BUY
        for symbol, score in sorted_coins[:8]:
            if score > 0.9 and symbol not in positions:
                if len(positions) < MAX_POSITIONS and balance > 5:

                    size = BASE_POSITION_SIZE * aggression_multiplier
                    size = min(size, balance)

                    entry = price_history[symbol][-1]
                    quantity = size / entry

                    positions[symbol] = (entry, size, quantity)
                    balance -= size
                    trades += 1

        # SELL
        for symbol in list(positions.keys()):
            entry, size, quantity = positions[symbol]
            current = price_history[symbol][-1]

            change = (current - entry) / entry

            if change >= 0.025 or change <= -0.015:

                profit = size * change
                balance += size + profit

                if profit > 0:
                    wins += 1
                    aggression_multiplier *= 1.05
                else:
                    losses += 1
                    aggression_multiplier *= 0.95

                aggression_multiplier = max(0.5, min(2.0, aggression_multiplier))

                del positions[symbol]

        time.sleep(4)


threading.Thread(target=trader, daemon=True).start()


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/")
def dashboard():

    scores = calculate_scores()

    total_positions_value = 0
    rows = ""

    for s in symbols:
        price = price_history[s][-1] if price_history[s] else 0
        rows += f"<tr><td>{s}</td><td>${price:.6f}</td><td>{scores[s]}</td></tr>"

    open_rows = ""
    for s, (entry, size, quantity) in positions.items():
        current = price_history[s][-1]
        value = quantity * current
        total_positions_value += value
        pnl = ((current - entry) / entry) * 100

        open_rows += f"""
        <tr>
            <td>{s}</td>
            <td>{quantity:.4f}</td>
            <td>${entry:.6f}</td>
            <td>${current:.6f}</td>
            <td>{pnl:.2f}%</td>
        </tr>
        """

    total_equity = balance + total_positions_value
    winrate = round((wins / trades) * 100, 2) if trades > 0 else 0

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="4">
        <style>
            body {{
                font-family: Arial;
                background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                color: white;
                padding: 20px;
            }}
            h1 {{ color:#f5a623; }}
            .card {{
                background: rgba(255,255,255,0.05);
                padding:20px;
                margin-bottom:20px;
                border-radius:10px;
            }}
            table {{ width:100%; border-collapse:collapse; }}
            th,td {{ padding:8px; text-align:left; }}
            th {{ color:#00c6ff; }}
        </style>
    </head>
    <body>

    <h1>🔥 ELITE SMALL-CAP AI TRADER</h1>

    <div class="card">
        <h2>Account</h2>
        Cash Balance: ${balance:.2f}<br>
        Positions Value: ${total_positions_value:.2f}<br>
        Total Equity: <b>${total_equity:.2f}</b><br><br>
        Trades: {trades}<br>
        Wins: {wins}<br>
        Losses: {losses}<br>
        Win Rate: {winrate}%<br>
        Aggression: {aggression_multiplier:.2f}
    </div>

    <div class="card">
        <h2>Open Positions</h2>
        <table>
        <tr><th>Coin</th><th>Quantity</th><th>Entry</th><th>Current</th><th>P/L</th></tr>
        {open_rows if open_rows else "<tr><td colspan='5'>None</td></tr>"}
        </table>
    </div>

    <div class="card">
        <h2>Live Market Scores</h2>
        <table>
        <tr><th>Coin</th><th>Price</th><th>Score</th></tr>
        {rows}
        </table>
    </div>

    </body>
    </html>
    """

    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)