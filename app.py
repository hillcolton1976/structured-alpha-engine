import requests
import threading
import time
import statistics
from flask import Flask, render_template_string

app = Flask(__name__)

# =============================
# CONFIG
# =============================
START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH_SECONDS = 5

# Adaptive base values
BASE_ENTRY = 0.0035
BASE_TP = 0.012
BASE_SL = 0.008

SYMBOLS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT",
    "INJUSDT","IMXUSDT","RNDRUSDT","FETUSDT","GALAUSDT",
    "SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
    "AAVEUSDT","ICPUSDT","FILUSDT","ETCUSDT","XLMUSDT"
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

entry_threshold = BASE_ENTRY
take_profit = BASE_TP
stop_loss = BASE_SL

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

        if len(history) < 15:
            scores[symbol] = 0
            continue

        old = history[-12]
        new = history[-1]

        if old == 0:
            scores[symbol] = 0
            continue

        momentum = (new - old) / old

        # Volatility penalty
        returns = []
        for i in range(1, len(history)):
            if history[i-1] != 0:
                returns.append((history[i] - history[i-1]) / history[i-1])

        volatility = statistics.stdev(returns) if len(returns) > 5 else 0
        adjusted_score = momentum - (volatility * 0.5)

        scores[symbol] = adjusted_score

    return scores

# =============================
# ADAPTIVE LEARNING
# =============================
def adapt():
    global entry_threshold, take_profit, stop_loss

    if trades < 10:
        return

    win_rate = wins / trades if trades > 0 else 0

    # Adjust entry aggressiveness
    if win_rate > 0.60:
        entry_threshold = max(0.0025, entry_threshold * 0.9)
        take_profit *= 1.05
    elif win_rate < 0.45:
        entry_threshold *= 1.1
        stop_loss *= 0.9

# =============================
# TRADER ENGINE
# =============================
def trader():
    global cash, trades, wins, losses

    while True:
        for symbol in SYMBOLS:
            price = get_price(symbol)
            if price > 0:
                price_history[symbol].append(price)
                if len(price_history[symbol]) > 120:
                    price_history[symbol].pop(0)

        scores = calculate_scores()

        # ----- EXIT LOGIC -----
        for symbol in list(positions.keys()):
            entry = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]
            current = price_history[symbol][-1]

            change = (current - entry) / entry

            if change >= take_profit or change <= -stop_loss:
                value = qty * current
                cash += value
                trades += 1

                if change > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]

        adapt()

        # ----- ENTRY LOGIC -----
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for symbol, score in ranked:
            if score > entry_threshold and len(positions) < MAX_POSITIONS:
                if symbol not in positions and cash > 5:
                    price = price_history[symbol][-1]

                    # volatility position sizing
                    history = price_history[symbol]
                    returns = [
                        (history[i] - history[i-1]) / history[i-1]
                        for i in range(1, len(history))
                        if history[i-1] != 0
                    ]
                    vol = statistics.stdev(returns) if len(returns) > 5 else 0.01
                    size_factor = max(0.5, min(1.5, 1 / (vol * 50)))

                    allocation = (cash / (MAX_POSITIONS - len(positions))) * size_factor
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
            <td>{qty:.6f}</td>
            <td>${entry:.6f}</td>
            <td>${current:.6f}</td>
            <td>${pnl:.2f}</td>
        </tr>
        """

    if not position_rows:
        position_rows = "<tr><td colspan='5'>None</td></tr>"

    total_equity = cash + total_positions_value
    win_rate = (wins / trades * 100) if trades > 0 else 0

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
                border-radius: 12px;
                margin-bottom: 20px;
            }}
            table {{ width:100%; }}
            th {{ color:#6dd5fa; text-align:left; }}
            td {{ padding:4px; }}
        </style>
    </head>
    <body>
        <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

        <div class="card">
            Cash: ${cash:.2f} <br>
            Positions Value: ${total_positions_value:.2f} <br>
            <b>Total Equity: ${total_equity:.2f}</b><br><br>
            Trades: {trades} |
            Wins: {wins} |
            Losses: {losses} |
            Win Rate: {win_rate:.1f}%<br><br>
            Entry Threshold: {entry_threshold:.4f} |
            TP: {take_profit:.4f} |
            SL: {stop_loss:.4f}
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Qty</th>
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
    </body>
    </html>
    """)

threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)