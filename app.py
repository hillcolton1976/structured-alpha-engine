from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

START_BALANCE = 50.0
balance = START_BALANCE
trades = 0
wins = 0
losses = 0

MAX_POSITIONS = 5
POSITION_SIZE = 10  # $ per trade

symbols = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

price_history = {s: [] for s in symbols}
positions = {}


# -----------------------
# GET LIVE PRICE
# -----------------------
def get_price(symbol):
    try:
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data["price"])
    except:
        return 0.0


# -----------------------
# EMA CALCULATION
# -----------------------
def ema(prices, period=9):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return ema_val


# -----------------------
# SCORE CALCULATION
# -----------------------
def calculate_scores():
    scores = {}
    for symbol in symbols:
        history = price_history[symbol]
        if len(history) >= 15 and history[-10] > 0:
            momentum = (history[-1] - history[-10]) / history[-10]
            fast_ema = ema(history[-15:], 5)
            slow_ema = ema(history[-15:], 12)

            if fast_ema and slow_ema:
                trend = 1 if fast_ema > slow_ema else -1
            else:
                trend = 0

            score = momentum * 100 * trend
            scores[symbol] = round(score, 2)
        else:
            scores[symbol] = 0

    return scores


# -----------------------
# TRADING LOGIC
# -----------------------
def trader():
    global balance, trades, wins, losses

    while True:
        # Update prices
        for symbol in symbols:
            price = get_price(symbol)
            if price > 0:
                price_history[symbol].append(price)
                if len(price_history[symbol]) > 50:
                    price_history[symbol].pop(0)

        scores = calculate_scores()

        # BUY LOGIC
        sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for symbol, score in sorted_coins:
            if score > 1 and symbol not in positions:
                if len(positions) < MAX_POSITIONS and balance >= POSITION_SIZE:
                    entry = price_history[symbol][-1]
                    positions[symbol] = entry
                    balance -= POSITION_SIZE
                    trades += 1

        # SELL LOGIC
        for symbol in list(positions.keys()):
            current = price_history[symbol][-1]
            entry = positions[symbol]
            change = (current - entry) / entry

            if change >= 0.02 or change <= -0.015:
                profit = POSITION_SIZE * change
                balance += POSITION_SIZE + profit

                if profit > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]

        time.sleep(5)


threading.Thread(target=trader, daemon=True).start()


# -----------------------
# DASHBOARD
# -----------------------
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
    for s, entry in positions.items():
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
        <meta http-equiv="refresh" content="5">
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

    <h1>🔥 ELITE AI TRADER</h1>

    <div class="card">
        <h2>Account</h2>
        Balance: ${balance:.2f}<br>
        Trades: {trades}<br>
        Wins: {wins}<br>
        Losses: {losses}<br>
        Win Rate: {winrate}%<br>
        Open Positions: {len(positions)}
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

    <p>Auto-refreshing every 5 seconds • Live Simulation Mode</p>

    </body>
    </html>
    """

    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)