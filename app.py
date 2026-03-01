from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

# ================= CONFIG =================

START_BALANCE = 50.0
MAX_POSITIONS = 5

SYMBOLS = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","DOGEUSDT",
"AVAXUSDT","LINKUSDT","MATICUSDT","TRXUSDT","DOTUSDT","LTCUSDT",
"BCHUSDT","ATOMUSDT","NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT",
"OPUSDT","INJUSDT","IMXUSDT","RNDRUSDT","FETUSDT","GALAUSDT",
"SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
"AAVEUSDT","ICPUSDT","FILUSDT","ETCUSDT","XLMUSDT"
]

balance = START_BALANCE
positions = {}
price_history = {s: [] for s in SYMBOLS}

wins = 0
losses = 0
trades = 0

entry_threshold = 0.004
take_profit = 0.015
stop_loss = 0.01


# ================= PRICE FETCH =================

def get_prices():
    try:
        coins = ",".join([s.replace("USDT","") for s in SYMBOLS])
        url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={coins}&tsyms=USDT"
        r = requests.get(url, timeout=10)
        data = r.json()

        prices = {}
        for s in SYMBOLS:
            coin = s.replace("USDT","")
            if coin in data and "USDT" in data[coin]:
                prices[s] = float(data[coin]["USDT"])
        return prices
    except:
        return {}


# ================= SCORING =================

def calculate_scores(prices):
    scores = {}
    for s in SYMBOLS:
        history = price_history[s]
        if len(history) < 10:
            scores[s] = 0
            continue

        past = history[-10]
        if past == 0:
            scores[s] = 0
            continue

        change = (history[-1] - past) / past
        scores[s] = round(change, 5)

    return scores


# ================= ADAPT =================

def adapt():
    global entry_threshold
    if trades < 5:
        return

    winrate = wins / trades
    if winrate < 0.4:
        entry_threshold *= 0.9
    elif winrate > 0.6:
        entry_threshold *= 1.05


# ================= TRADER =================

def trader():
    global balance, wins, losses, trades

    while True:
        prices = get_prices()
        if not prices:
            time.sleep(5)
            continue

        for s in prices:
            price_history[s].append(prices[s])
            if len(price_history[s]) > 50:
                price_history[s] = price_history[s][-50:]

        scores = calculate_scores(prices)

        # SELL
        for s in list(positions.keys()):
            entry = positions[s]["entry"]
            qty = positions[s]["qty"]
            current = prices.get(s, entry)

            change = (current - entry) / entry

            if change >= take_profit or change <= -stop_loss:
                balance += qty * current
                trades += 1
                if change > 0:
                    wins += 1
                else:
                    losses += 1
                del positions[s]

        # BUY
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        for s, score in sorted_scores:
            if len(positions) >= MAX_POSITIONS:
                break
            if s in positions:
                continue
            if score > entry_threshold and balance > 5:
                price = prices[s]
                amount = balance / (MAX_POSITIONS - len(positions))
                qty = amount / price

                positions[s] = {"entry": price, "qty": qty}
                balance -= amount

        adapt()
        time.sleep(5)


# ================= DASHBOARD =================

@app.route("/")
def dashboard():
    prices = get_prices()
    scores = calculate_scores(prices) if prices else {}

    # SORT MARKET BY SCORE
    sorted_market = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    positions_value = 0
    position_rows = ""

    for s, data in positions.items():
        current = prices.get(s, data["entry"])
        value = data["qty"] * current
        pnl = value - (data["qty"] * data["entry"])
        positions_value += value

        color = "#00ff88" if pnl >= 0 else "#ff4d4d"

        position_rows += f"""
        <tr>
            <td>{s}</td>
            <td>{round(data['qty'],6)}</td>
            <td>${data['entry']:.6f}</td>
            <td>${current:.6f}</td>
            <td style='color:{color};'>${round(pnl,2)}</td>
        </tr>
        """

    total_equity = balance + positions_value

    score_rows = ""
    for s, score in sorted_market:
        price = prices.get(s, 0)
        color = "#00ff88" if score > 0 else "#ff4d4d" if score < 0 else "white"

        score_rows += f"""
        <tr>
            <td>{s}</td>
            <td>${price:.6f}</td>
            <td style='color:{color};'>{score}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body {{
        font-family: Arial;
        background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
        color:white;
        padding:20px;
    }}

    .card {{
        background: rgba(255,255,255,0.05);
        padding:20px;
        border-radius:12px;
        margin-bottom:20px;
    }}

    table {{
        width:100%;
        border-collapse: collapse;
    }}

    th {{
        text-align:left;
        border-bottom:1px solid #555;
        padding:8px 4px;
    }}

    td {{
        padding:6px 4px;
        border-bottom:1px solid #333;
    }}

    h1 {{
        color:#ffb347;
    }}

    .green {{ color:#00ff88; }}
    .red {{ color:#ff4d4d; }}

    </style>
    </head>
    <body>

    <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

    <div class="card">
        <h2>Account</h2>
        <p>Cash: <b>${balance:.2f}</b></p>
        <p>Positions Value: <b>${positions_value:.2f}</b></p>
        <p>Total Equity: <b>${total_equity:.2f}</b></p>
        <p>Trades: {trades} | Wins: {wins} | Losses: {losses}</p>
        <p>Entry Threshold: {entry_threshold:.5f}</p>
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
        {position_rows if position_rows else "<tr><td colspan=5>None</td></tr>"}
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
    """

    return render_template_string(html)


threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)