from flask import Flask, render_template_string
import requests
import threading
import time
import statistics

app = Flask(__name__)

START_BALANCE = 50.0
balance = START_BALANCE
trades = 0
wins = 0
losses = 0

MAX_POSITIONS = 5
BASE_POSITION_SIZE = 8  # adaptive sizing base

symbols = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

price_history = {s: [] for s in symbols}
positions = {}
aggression_multiplier = 1.0


# -------------------------
# LIVE PRICE
# -------------------------
def get_price(symbol):
    try:
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        return float(r.json()["price"])
    except:
        return 0.0


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
# SMART SCORE
# -------------------------
def calculate_scores():
    scores = {}

    for symbol in symbols:
        history = price_history[symbol]

        if len(history) < 20 or history[-15] == 0:
            scores[symbol] = 0
            continue

        short_momentum = (history[-1] - history[-5]) / history[-5]
        medium_momentum = (history[-1] - history[-15]) / history[-15]

        fast = ema(history[-20:], 5)
        slow = ema(history[-20:], 12)

        trend_boost = 1 if fast and slow and fast > slow else -1

        volatility = statistics.pstdev(history[-15:]) if len(history[-15:]) > 5 else 0

        score = (short_momentum * 0.6 + medium_momentum * 0.4)
        score *= trend_boost
        score *= (1 + volatility)

        scores[symbol] = round(score * 100, 2)

    return scores


# -------------------------
# TRADER
# -------------------------
def trader():
    global balance, trades, wins, losses, aggression_multiplier

    while True:

        # update prices
        for s in symbols:
            price = get_price(s)
            if price > 0:
                price_history[s].append(price)
                if len(price_history[s]) > 50:
                    price_history[s].pop(0)

        scores = calculate_scores()

        # BUY LOGIC
        sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for symbol, score in sorted_coins[:8]:  # top 8 focus
            if score > 0.8 and symbol not in positions:
                if len(positions) < MAX_POSITIONS and balance > 5:

                    position_size = BASE_POSITION_SIZE * aggression_multiplier
                    position_size = min(position_size, balance)

                    entry = price_history[symbol][-1]
                    positions[symbol] = (entry, position_size)

                    balance -= position_size
                    trades += 1

        # SELL LOGIC
        for symbol in list(positions.keys()):
            entry, size = positions[symbol]
            current = price_history[symbol][-1]

            change = (current - entry) / entry

            # aggressive exits
            if change >= 0.018 or change <= -0.012:

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

    rows = ""
    for s in symbols:
        price = price_history[s][-1] if price_history[s] else 0
        rows += f"""
        <tr>
            <td>{s}</td>
            <td>${price:.4f}</td>
            <td>{scores[s]}</td>
        </tr>
        """

    open_rows = ""
    for s, (entry, size) in positions.items():
        current = price_history[s][-1]
        pnl = ((current - entry) / entry) * 100
        open_rows += f"""
        <tr>
            <td>{s}</td>
            <td>${entry:.4f}</td>
            <td>${current:.4f}</td>
            <td>{pnl:.2f}%</td>
        </tr>
        """

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
            table {{
                width:100%;
                border-collapse:collapse;
            }}
            th,td {{
                padding:8px;
                text-align:left;
            }}
            th {{ color:#00c6ff; }}
        </style>
    </head>
    <body>

    <h1>🔥 ELITE AI TRADER v3</h1>

    <div class="card">
        <h2>Account</h2>
        Balance: ${balance:.2f}<br>
        Trades: {trades}<br>
        Wins: {wins}<br>
        Losses: {losses}<br>
        Win Rate: {winrate}%<br>
        Open Positions: {len(positions)}<br>
        Aggression Multiplier: {aggression_multiplier:.2f}
    </div>

    <div class="card">
        <h2>Open Positions</h2>
        <table>
        <tr><th>Symbol</th><th>Entry</th><th>Current</th><th>P/L</th></tr>
        {open_rows if open_rows else "<tr><td colspan='4'>None</td></tr>"}
        </table>
    </div>

    <div class="card">
        <h2>Top 20 Momentum (Live)</h2>
        <table>
        <tr><th>Symbol</th><th>Price</th><th>Score</th></tr>
        {rows}
        </table>
    </div>

    <p>Auto-refreshing every 4 seconds • Adaptive AI Mode</p>

    </body>
    </html>
    """

    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)