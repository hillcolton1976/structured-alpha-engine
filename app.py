from flask import Flask
import requests
import threading
import time

app = Flask(__name__)

# ==========================
# CONFIG
# ==========================
STARTING_CASH = 50
MAX_POSITIONS = 5
TOP_COINS = 35

cash = STARTING_CASH
positions = {}
price_history = {}
trades = 0
wins = 0
losses = 0
entry_threshold = 0.003

# ==========================
# GET TOP 35 COINS
# ==========================
def get_top_pairs():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url, timeout=10).json()

    usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [x["symbol"] for x in sorted_pairs[:TOP_COINS]]

coins = get_top_pairs()

# ==========================
# GET PRICES
# ==========================
def get_prices():
    url = "https://api.binance.com/api/v3/ticker/price"
    data = requests.get(url, timeout=10).json()
    prices = {x["symbol"]: float(x["price"]) for x in data if x["symbol"] in coins}
    return prices

# ==========================
# SCORE CALCULATION
# ==========================
def calculate_scores(prices):
    scores = {}

    for coin in coins:
        price = prices.get(coin, 0)
        if price == 0:
            continue

        history = price_history.setdefault(coin, [])
        history.append(price)

        if len(history) > 50:
            history.pop(0)

        if len(history) < 10:
            scores[coin] = 0
            continue

        base = history[-10]
        if base == 0:
            scores[coin] = 0
            continue

        change = (history[-1] - base) / base
        scores[coin] = change

    return scores

# ==========================
# ADAPTIVE LEARNING
# ==========================
def adapt():
    global entry_threshold

    if trades < 5:
        return

    winrate = wins / trades

    if winrate > 0.6:
        entry_threshold *= 1.02
    elif winrate < 0.45:
        entry_threshold *= 0.98

    entry_threshold = max(0.001, min(entry_threshold, 0.02))

# ==========================
# TRADING ENGINE
# ==========================
def trader():
    global cash, trades, wins, losses

    while True:
        try:
            prices = get_prices()
            scores = calculate_scores(prices)

            # BUY LOGIC
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            for coin, score in sorted_scores:
                if score > entry_threshold and coin not in positions and len(positions) < MAX_POSITIONS:
                    amount = cash / (MAX_POSITIONS - len(positions))
                    if amount <= 1:
                        continue

                    qty = amount / prices[coin]
                    positions[coin] = {
                        "entry": prices[coin],
                        "qty": qty
                    }
                    cash -= amount
                    trades += 1

            # SELL LOGIC
            for coin in list(positions.keys()):
                entry = positions[coin]["entry"]
                qty = positions[coin]["qty"]
                current = prices.get(coin, entry)

                change = (current - entry) / entry

                if change > 0.01 or change < -0.01:
                    value = qty * current
                    cash += value
                    trades += 1

                    if change > 0:
                        wins += 1
                    else:
                        losses += 1

                    del positions[coin]

            adapt()

        except Exception as e:
            print("Engine error:", e)

        time.sleep(5)

# ==========================
# DASHBOARD
# ==========================
@app.route("/")
def dashboard():
    prices = get_prices()
    scores = calculate_scores(prices)

    total_positions_value = sum(
        positions[s]['qty'] * prices.get(s, positions[s]['entry'])
        for s in positions
    )

    total_equity = cash + total_positions_value

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
    body {{ background:#0f2027; color:white; font-family:Arial; padding:20px; }}
    h1 {{ color:gold; }}
    .card {{ background:#1c3b45; padding:20px; margin-bottom:20px; border-radius:10px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ padding:8px; border-bottom:1px solid #333; }}
    .green {{ color:#00ff99; }}
    .red {{ color:#ff4d4d; }}
    </style>
    </head>
    <body>

    <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

    <div class="card">
    <b>Cash:</b> ${cash:.2f}<br>
    <b>Positions Value:</b> ${total_positions_value:.2f}<br>
    <b>Total Equity:</b> ${total_equity:.2f}<br><br>
    Trades: {trades} | Wins: {wins} | Losses: {losses}<br>
    Entry Threshold: {entry_threshold:.4f}
    </div>

    <div class="card">
    <h3>Open Positions</h3>
    <table>
    <tr><th>Coin</th><th>Qty</th><th>Entry</th><th>Current</th></tr>
    {''.join(
        f"<tr><td>{c}</td><td>{positions[c]['qty']:.4f}</td><td>${positions[c]['entry']:.4f}</td><td>${prices.get(c,0):.4f}</td></tr>"
        for c in positions
    )}
    </table>
    </div>

    <div class="card">
    <h3>Live Market Scores</h3>
    <table>
    <tr><th>Coin</th><th>Price</th><th>Score</th></tr>
    {''.join(
        f"<tr><td>{s}</td><td>${prices.get(s,0):.4f}</td><td>{score:.4f}</td></tr>"
        for s,score in sorted_scores
    )}
    </table>
    </div>

    </body>
    </html>
    """

# ==========================
# START ENGINE
# ==========================
threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)