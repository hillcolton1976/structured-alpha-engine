from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH = 5

SYMBOLS = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
"ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
"TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
"NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT",
"INJUSDT","IMXUSDT","RNDRUSDT","FETUSDT","GALAUSDT",
"SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
"AAVEUSDT","ICPUSDT","FILUSDT","ETCUSDT","XLMUSDT"
]

cash = START_BALANCE
positions = {}
history = {s: [] for s in SYMBOLS}

trades = 0
wins = 0
losses = 0

entry_threshold = 0.004
tp = 0.012
sl = 0.008

# =========================
# GET ALL BINANCE PRICES
# =========================

def get_prices():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10)
        data = r.json()

        prices = {}
        for item in data:
            symbol = item["symbol"]
            if symbol in SYMBOLS:
                prices[symbol] = float(item["price"])

        return prices
    except:
        return {}

# =========================
# SCORE CALCULATION
# =========================

def calculate_scores(prices):
    scores = {}
    for s in SYMBOLS:
        price = prices.get(s, 0)
        if price == 0:
            scores[s] = 0
            continue

        history[s].append(price)
        if len(history[s]) > 50:
            history[s].pop(0)

        if len(history[s]) >= 10:
            base = history[s][-10]
            if base > 0:
                change = (price - base) / base
                scores[s] = round(change, 5)
            else:
                scores[s] = 0
        else:
            scores[s] = 0

    return scores

# =========================
# TRADER LOOP
# =========================

def trader():
    global cash, trades, wins, losses, entry_threshold

    while True:
        prices = get_prices()
        scores = calculate_scores(prices)

        # SELL
        for s in list(positions.keys()):
            if s not in prices:
                continue

            price = prices[s]
            entry = positions[s]["entry"]
            qty = positions[s]["qty"]

            change = (price - entry) / entry

            if change >= tp or change <= -sl:
                value = qty * price
                pnl = value - (qty * entry)

                cash += value
                trades += 1

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[s]

                # Adaptive learning
                if trades > 5:
                    winrate = wins / trades
                    if winrate < 0.4:
                        entry_threshold *= 1.05
                    elif winrate > 0.6:
                        entry_threshold *= 0.97

        # BUY
        if len(positions) < MAX_POSITIONS and prices:
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            for s, score in ranked:
                if s in positions:
                    continue
                if score > entry_threshold and cash > 5:
                    price = prices[s]
                    invest = cash / (MAX_POSITIONS - len(positions))
                    qty = invest / price

                    positions[s] = {"qty": qty, "entry": price}
                    cash -= invest
                    break

        time.sleep(REFRESH)

threading.Thread(target=trader, daemon=True).start()

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    prices = get_prices()
    scores = calculate_scores(prices)

    total_value = 0
    pos_rows = ""

    for s, data in positions.items():
        if s in prices:
            price = prices[s]
            value = data["qty"] * price
            pnl = value - (data["qty"] * data["entry"])
            total_value += value

            pos_rows += f"<tr><td>{s}</td><td>{data['qty']:.4f}</td><td>${data['entry']:.4f}</td><td>${price:.4f}</td><td>${pnl:.2f}</td></tr>"

    equity = cash + total_value
    winrate = round((wins/trades)*100,2) if trades>0 else 0

    rows = ""
    for s in SYMBOLS:
        price = prices.get(s,0)
        score = scores.get(s,0)
        rows += f"<tr><td>{s}</td><td>${price:.6f}</td><td>{score:.5f}</td></tr>"

    return render_template_string(f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="{REFRESH}">
    <style>
    body {{
        background: linear-gradient(to bottom right,#0f2027,#203a43,#2c5364);
        color:white;
        font-family:Arial;
        padding:20px;
    }}
    table{{width:100%;border-collapse:collapse;margin-bottom:20px;}}
    th,td{{padding:8px;text-align:left;}}
    th{{color:#6dd5fa;}}
    tr:nth-child(even){{background:rgba(255,255,255,0.05);}}
    .card{{background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;margin-bottom:20px;}}
    </style>
    </head>
    <body>
    <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

    <div class="card">
    Cash: ${cash:.2f}<br>
    Positions Value: ${total_value:.2f}<br>
    Total Equity: ${equity:.2f}<br><br>
    Trades: {trades} | Wins: {wins} | Losses: {losses} | Win Rate: {winrate}%
    </div>

    <div class="card">
    <h2>Open Positions</h2>
    <table>
    <tr><th>Coin</th><th>Qty</th><th>Entry</th><th>Current</th><th>P/L</th></tr>
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

    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run()