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

symbols = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

price_history = {s: [] for s in symbols}


# -------------------------
# SAFE PRICE FETCH (Binance US)
# -------------------------
def get_price(symbol):
    try:
        url = f"https://api.binance.us/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data["price"])
    except:
        return 0.0


# -------------------------
# SCORE CALCULATION
# -------------------------
def calculate_scores():
    scores = {}

    for symbol in symbols:
        history = price_history[symbol]

        if len(history) >= 10 and history[-10] > 0:
            change = (history[-1] - history[-10]) / history[-10]
            scores[symbol] = round(change * 100, 2)
        else:
            scores[symbol] = 0

    return scores


# -------------------------
# BACKGROUND TRADER LOOP
# -------------------------
def trader():
    while True:
        for symbol in symbols:
            price = get_price(symbol)

            if price > 0:
                price_history[symbol].append(price)

                if len(price_history[symbol]) > 50:
                    price_history[symbol].pop(0)

        time.sleep(5)


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
            h1 {{
                color: #f5a623;
            }}
            .card {{
                background: rgba(255,255,255,0.05);
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 10px;
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
                color: #00c6ff;
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
            Losses: {losses}
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

    return render_template_string(html)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)