from flask import Flask
import requests
import threading
import time
import statistics

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50.0

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

# =============================
# ACCOUNT STATE
# =============================

balance = START_BALANCE
trades = 0
wins = 0
losses = 0

price_history = {symbol: [] for symbol in TOP_20}

# =============================
# PRICE FETCHING
# =============================

def get_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data["price"])
    except:
        return 0.0

# =============================
# MOMENTUM SCORING (SAFE)
# =============================

def calculate_scores():
    scores = {}

    for symbol in TOP_20:
        history = price_history[symbol]

        if len(history) < 10:
            scores[symbol] = 0
            continue

        old_price = history[-10]
        new_price = history[-1]

        if old_price == 0:
            scores[symbol] = 0
            continue

        try:
            change = (new_price - old_price) / old_price
            volatility = statistics.stdev(history[-10:])
            score = change * 100 - volatility
            scores[symbol] = round(score, 2)
        except:
            scores[symbol] = 0

    return scores

# =============================
# BACKGROUND TRADER LOOP
# =============================

def trader():
    while True:
        for symbol in TOP_20:
            price = get_price(symbol)

            if price > 0:
                history = price_history[symbol]
                history.append(price)

                # Keep last 50 prices
                if len(history) > 50:
                    history.pop(0)

        time.sleep(5)

threading.Thread(target=trader, daemon=True).start()

# =============================
# DASHBOARD
# =============================

@app.route("/")
def dashboard():
    scores = calculate_scores()

    sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    rows = ""
    for symbol, score in sorted_coins:
        latest_price = price_history[symbol][-1] if price_history[symbol] else 0
        rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${latest_price:.4f}</td>
            <td>{score}</td>
        </tr>
        """

    return f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <style>
            body {{
                background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
                color: white;
                font-family: Arial;
                padding: 30px;
            }}
            h1 {{
                color: orange;
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 8px;
                text-align: left;
            }}
            th {{
                color: #00d4ff;
            }}
            tr:hover {{
                background: rgba(255,255,255,0.05);
            }}
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
        </div>

        <div class="card">
            <h2>Top 20 Momentum (Live Prices)</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Score</th>
                </tr>
                {rows}
            </table>
        </div>

        <p>Auto-refreshing every 5 seconds • Live Simulation Mode</p>
    </body>
    </html>
    """

# =============================
# RUN (for local testing)
# =============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)