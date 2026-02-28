import requests
import threading
import time
from flask import Flask, render_template_string

app = Flask(__name__)

# =============================
# CONFIG
# =============================
START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH_SECONDS = 5
ENTRY_THRESHOLD = 0.004
TAKE_PROFIT = 0.01
STOP_LOSS = 0.008

SYMBOLS = [
    "PEPEUSDT","WIFUSDT","BONKUSDT","FLOKIUSDT","JASMYUSDT",
    "SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
    "RNDRUSDT","FETUSDT","GALAUSDT","BLURUSDT","DYDXUSDT",
    "IMXUSDT","OPUSDT","ARBUSDT","APTUSDT","INJUSDT"
]

# =============================
# STATE
# =============================
cash = START_BALANCE
positions = {}
price_history = {s: [] for s in SYMBOLS}
trades = 0
wins = 0
losses = 0

# =============================
# PRICE FETCH
# =============================
def get_price(symbol):
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
            timeout=5
        )
        return float(r.json()["price"])
    except:
        return 0.0

# =============================
# SCORE ENGINE
# =============================
def calculate_scores():
    scores = {}

    for symbol in SYMBOLS:
        history = price_history[symbol]

        if len(history) < 12:
            scores[symbol] = 0
            continue

        old = history[-10]
        new = history[-1]

        if old == 0:
            scores[symbol] = 0
            continue

        momentum = (new - old) / old
        scores[symbol] = momentum

    return scores

# =============================
# TRADING ENGINE
# =============================
def trader():
    global cash, trades, wins, losses

    while True:
        for symbol in SYMBOLS:
            price = get_price(symbol)
            if price > 0:
                price_history[symbol].append(price)
                if len(price_history[symbol]) > 100:
                    price_history[symbol].pop(0)

        scores = calculate_scores()

        # ---- EXIT LOGIC ----
        for symbol in list(positions.keys()):
            entry = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]
            current = price_history[symbol][-1]

            change = (current - entry) / entry

            if change >= TAKE_PROFIT or change <= -STOP_LOSS:
                pnl = qty * current
                cash += pnl
                trades += 1

                if change > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]

        # ---- ENTRY LOGIC ----
        sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for symbol, score in sorted_coins:
            if score > ENTRY_THRESHOLD and len(positions) < MAX_POSITIONS:
                if symbol not in positions and cash > 5:
                    allocation = cash / (MAX_POSITIONS - len(positions))
                    price = price_history[symbol][-1]

                    qty = allocation / price
                    cash -= allocation

                    positions[symbol] = {
                        "entry": price,
                        "qty": qty
                    }

        time.sleep(REFRESH_SECONDS)

# =============================
# DASHBOARD
# =============================
@app.route("/")
def dashboard():
    scores = calculate_scores()

    total_positions_value = 0
    position_rows = ""

    for symbol, data in positions.items():
        current = price_history[symbol][-1]
        qty = data["qty"]
        entry = data["entry"]
        value = qty * current
        pnl = value - (qty * entry)

        total_positions_value += value

        position_rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>{qty:.4f}</td>
            <td>${entry:.6f}</td>
            <td>${current:.6f}</td>
            <td>${pnl:.2f}</td>
        </tr>
        """

    if not position_rows:
        position_rows = "<tr><td colspan='5'>None</td></tr>"

    total_equity = cash + total_positions_value

    score_rows = ""
    for symbol, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        price = price_history[symbol][-1] if price_history[symbol] else 0
        score_rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${price:.6f}</td>
            <td>{score:.4f}</td>
        </tr>
        """

    return render_template_string(f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
        <style>
            body {{
                background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
                font-family: Arial;
                color: white;
                padding: 20px;
            }}
            .card {{
                background: rgba(255,255,255,0.08);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
            }}
            th, td {{
                padding: 6px;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <h1>🔥 ELITE SMALL-CAP AI TRADER</h1>

        <div class="card">
            <h2>Account</h2>
            Cash Balance: ${cash:.2f}<br>
            Positions Value: ${total_positions_value:.2f}<br>
            <b>Total Equity: ${total_equity:.2f}</b><br><br>
            Trades: {trades} |
            Wins: {wins} |
            Losses: {losses}
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Quantity</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>P/L</th>
                </tr>
                {position_rows}
            </table>
        </div>

        <div class="card">
            <h2>Live Market Scores</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Price</th>
                    <th>Score</th>
                </tr>
                {score_rows}
            </table>
        </div>

        <p>Auto-refreshing every {REFRESH_SECONDS} seconds • Live Simulation Mode</p>
    </body>
    </html>
    """)

# =============================
# START THREAD
# =============================
threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)