from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

# ======================
# CONFIG
# ======================

START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH_SECONDS = 5

SYMBOLS = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT",
    "INJUSDT","IMXUSDT","RNDRUSDT","FETUSDT","GALAUSDT",
    "SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
    "AAVEUSDT","ICPUSDT","FILUSDT","ETCUSDT","XLMUSDT"
]

# ======================
# STATE
# ======================

cash = START_BALANCE
positions = {}  # symbol: {qty, entry}
history = {s: [] for s in SYMBOLS}

trades = 0
wins = 0
losses = 0

entry_threshold = 0.004
tp_percent = 0.012
sl_percent = 0.008

# ======================
# PRICE FETCH
# ======================

def get_price(symbol):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol},
            headers=headers,
            timeout=10
        )
        data = r.json()

        if "price" in data:
            return float(data["price"])
        else:
            print("API Error:", data)
            return None
    except Exception as e:
        print("Request failed:", e)
        return None

# ======================
# SCORING
# ======================

def calculate_scores():
    scores = {}
    for s in SYMBOLS:
        price = get_price(s)
        if price is None:
            continue

        history[s].append(price)
        if len(history[s]) > 50:
            history[s].pop(0)

        if len(history[s]) >= 10:
            base = history[s][-10]
            if base != 0:
                change = (history[s][-1] - base) / base
                scores[s] = round(change, 5)
            else:
                scores[s] = 0
        else:
            scores[s] = 0

    return scores

# ======================
# TRADER LOOP
# ======================

def trader():
    global cash, trades, wins, losses
    global entry_threshold, tp_percent, sl_percent

    while True:
        scores = calculate_scores()

        # SELL LOGIC
        for symbol in list(positions.keys()):
            price = get_price(symbol)
            if price is None:
                continue

            entry = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]

            change = (price - entry) / entry

            if change >= tp_percent or change <= -sl_percent:
                value = qty * price
                pnl = value - (qty * entry)

                cash += value
                trades += 1

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]

                # Adaptive Learning
                if trades > 5:
                    winrate = wins / trades
                    if winrate < 0.4:
                        entry_threshold *= 1.05
                        tp_percent *= 0.95
                        sl_percent *= 1.05
                    elif winrate > 0.6:
                        entry_threshold *= 0.97
                        tp_percent *= 1.05
                        sl_percent *= 0.95

        # BUY LOGIC
        if len(positions) < MAX_POSITIONS:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            for symbol, score in sorted_scores:
                if symbol in positions:
                    continue

                if score > entry_threshold and cash > 5:
                    price = get_price(symbol)
                    if price is None:
                        continue

                    invest = cash / (MAX_POSITIONS - len(positions))
                    qty = invest / price

                    positions[symbol] = {
                        "qty": qty,
                        "entry": price
                    }

                    cash -= invest
                    break

        time.sleep(REFRESH_SECONDS)

threading.Thread(target=trader, daemon=True).start()

# ======================
# DASHBOARD
# ======================

@app.route("/")
def dashboard():
    scores = calculate_scores()

    rows = ""
    for s in SYMBOLS:
        price = get_price(s)
        score = scores.get(s, 0)
        if price is None:
            price = 0
        rows += f"<tr><td>{s}</td><td>${price:.6f}</td><td>{score:.5f}</td></tr>"

    pos_rows = ""
    total_positions_value = 0

    for s, data in positions.items():
        price = get_price(s)
        if price is None:
            continue

        value = data["qty"] * price
        total_positions_value += value
        pnl = value - (data["qty"] * data["entry"])

        pos_rows += f"<tr><td>{s}</td><td>{data['qty']:.4f}</td><td>${data['entry']:.6f}</td><td>${price:.6f}</td><td>${pnl:.2f}</td></tr>"

    total_equity = cash + total_positions_value
    winrate = round((wins / trades) * 100, 2) if trades > 0 else 0

    return render_template_string(f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
        <style>
            body {{
                background: linear-gradient(to bottom right, #0f2027, #203a43, #2c5364);
                color: white;
                font-family: Arial;
                padding: 20px;
            }}
            h1 {{ color: #ffae42; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
            }}
            th {{ color: #6dd5fa; }}
            tr:nth-child(even) {{ background-color: rgba(255,255,255,0.05); }}
            .card {{
                background: rgba(255,255,255,0.05);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

        <div class="card">
            <b>Cash:</b> ${cash:.2f}<br>
            <b>Positions Value:</b> ${total_positions_value:.2f}<br>
            <b>Total Equity:</b> ${total_equity:.2f}<br><br>
            Trades: {trades} | Wins: {wins} | Losses: {losses} | Win Rate: {winrate}%<br>
            Entry: {entry_threshold:.4f} | TP: {tp_percent:.4f} | SL: {sl_percent:.4f}
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            <table>
                <tr>
                    <th>Coin</th><th>Qty</th><th>Entry</th><th>Current</th><th>P/L</th>
                </tr>
                {pos_rows if pos_rows else "<tr><td colspan=5>None</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Live Market Scores</h2>
            <table>
                <tr><th>Coin</th><th>Price</th><th>Score</th></tr>
                {rows}
            </table>
        </div>

        <p>Auto-refresh every {REFRESH_SECONDS}s • Live Simulation Mode</p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run()