import requests
import threading
import time
from flask import Flask, render_template_string

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

START_BALANCE = 50.0
cash = START_BALANCE
positions = {}
price_history = {}

trades = 0
wins = 0
losses = 0

# ===== Adaptive Parameters =====
entry_threshold = 0.004
take_profit = 0.012
stop_loss = 0.008

MIN_THRESHOLD = 0.001
MAX_THRESHOLD = 0.02
MIN_TP = 0.006
MAX_TP = 0.03
MIN_SL = 0.004
MAX_SL = 0.02

MAX_DRAWDOWN = 0.15
risk_per_trade = 0.10

peak_equity = START_BALANCE
paused = False

TOP_35 = [
"BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
"ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
"TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
"NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT",
"INJUSDT","IMXUSDT","RNDRUSDT","FETUSDT","GALAUSDT",
"SUIUSDT","SEIUSDT","TIAUSDT","PYTHUSDT","ORDIUSDT",
"AAVEUSDT","ICPUSDT","FILUSDT","ETCUSDT","XLMUSDT"
]

# ==============================
# PRICE FETCH
# ==============================

def get_prices():
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        data = requests.get(url, timeout=5).json()
        prices = {item['symbol']: float(item['price']) for item in data if item['symbol'] in TOP_35}
        return prices
    except:
        return {}

# ==============================
# SCORING
# ==============================

def calculate_scores(prices):
    scores = {}
    for symbol, price in prices.items():
        history = price_history.setdefault(symbol, [])
        history.append(price)
        if len(history) > 20:
            history.pop(0)

        if len(history) < 10:
            scores[symbol] = 0
            continue

        if history[-10] == 0:
            scores[symbol] = 0
            continue

        change = (history[-1] - history[-10]) / history[-10]
        scores[symbol] = change

    return scores

# ==============================
# POSITION SIZE
# ==============================

def calculate_position_size(score, cash):
    confidence = min(score / 0.01, 1)
    return cash * risk_per_trade * confidence

# ==============================
# VOLATILITY FILTER
# ==============================

def volatility_filter(history):
    if len(history) < 5:
        return False
    change = abs(history[-1] - history[-5]) / history[-5]
    return change > 0.05

# ==============================
# ADAPTIVE LEARNING
# ==============================

def adapt(total_equity):
    global entry_threshold, take_profit, stop_loss
    global peak_equity, paused

    if total_equity > peak_equity:
        peak_equity = total_equity

    drawdown = (peak_equity - total_equity) / peak_equity

    if drawdown > MAX_DRAWDOWN:
        paused = True
        return
    else:
        paused = False

    if trades < 5:
        return

    winrate = wins / trades

    if winrate < 0.45:
        entry_threshold *= 0.98
        take_profit *= 0.98
        stop_loss *= 1.02
    elif winrate > 0.60:
        entry_threshold *= 1.02
        take_profit *= 1.02
        stop_loss *= 0.98

    entry_threshold = max(MIN_THRESHOLD, min(entry_threshold, MAX_THRESHOLD))
    take_profit = max(MIN_TP, min(take_profit, MAX_TP))
    stop_loss = max(MIN_SL, min(stop_loss, MAX_SL))

# ==============================
# TRADER LOOP
# ==============================

def trader():
    global cash, trades, wins, losses

    while True:
        prices = get_prices()
        if not prices:
            time.sleep(5)
            continue

        scores = calculate_scores(prices)

        total_positions_value = sum(
            positions[s]['qty'] * prices.get(s, positions[s]['entry'])
            for s in positions
        )

        total_equity = cash + total_positions_value
        adapt(total_equity)

        for symbol in TOP_35:
            if symbol not in prices:
                continue

            price = prices[symbol]
            history = price_history[symbol]

            if paused:
                continue

            if volatility_filter(history):
                continue

            score = scores.get(symbol, 0)

            # ENTRY
            if score > entry_threshold and symbol not in positions:
                position_size = calculate_position_size(score, cash)
                if position_size > 1:
                    qty = position_size / price
                    positions[symbol] = {"entry": price, "qty": qty}
                    cash -= position_size
                    trades += 1

            # EXIT
            if symbol in positions:
                entry_price = positions[symbol]["entry"]
                qty = positions[symbol]["qty"]

                change = (price - entry_price) / entry_price

                if change >= take_profit or change <= -stop_loss:
                    value = qty * price
                    cash += value

                    if change > 0:
                        wins += 1
                    else:
                        losses += 1

                    del positions[symbol]

        time.sleep(5)

# ==============================
# DASHBOARD
# ==============================

@app.route("/")
def dashboard():
    prices = get_prices()
    scores = calculate_scores(prices)

    total_positions_value = sum(
        positions[s]['qty'] * prices.get(s, positions[s]['entry'])
        for s in positions
    )
    total_equity = cash + total_positions_value

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body { background: #0f2027; color: white; font-family: Arial; padding: 20px;}
    h1 { color: gold; }
    .card { background: #1c3b45; padding: 20px; margin-bottom: 20px; border-radius: 10px;}
    table { width: 100%; border-collapse: collapse;}
    th, td { padding: 8px; border-bottom: 1px solid #333;}
    .green { color: #00ff99;}
    .red { color: #ff4d4d;}
    </style>
    </head>
    <body>
    <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

    <div class="card">
    <b>Cash:</b> ${:.2f}<br>
    <b>Positions Value:</b> ${:.2f}<br>
    <b>Total Equity:</b> ${:.2f}<br><br>
    Trades: {} | Wins: {} | Losses: {}<br>
    Entry Threshold: {:.4f}
    </div>

    <div class="card">
    <h3>Open Positions</h3>
    <table>
    <tr><th>Coin</th><th>Qty</th><th>Entry</th><th>Current</th><th>P/L</th></tr>
    """.format(
        cash, total_positions_value, total_equity,
        trades, wins, losses, entry_threshold
    )

    if not positions:
        html += "<tr><td colspan=5>None</td></tr>"
    else:
        for s, data in positions.items():
            current = prices.get(s, data["entry"])
            pnl = (current - data["entry"]) / data["entry"]
            color = "green" if pnl > 0 else "red"
            html += f"<tr><td>{s}</td><td>{data['qty']:.4f}</td><td>${data['entry']:.4f}</td><td>${current:.4f}</td><td class='{color}'>{pnl*100:.2f}%</td></tr>"

    html += "</table></div>"

    html += "<div class='card'><h3>Live Market Scores</h3><table><tr><th>Coin</th><th>Price</th><th>Score</th></tr>"

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    for s, score in sorted_scores:
        price = prices.get(s, 0)
        html += f"<tr><td>{s}</td><td>${price:.4f}</td><td>{score:.4f}</td></tr>"

    html += "</table></div></body></html>"

    return html

# ==============================
# START
# ==============================

threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)