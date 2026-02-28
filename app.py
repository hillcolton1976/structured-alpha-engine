from flask import Flask, render_template_string
import requests
import threading
import time
import statistics

app = Flask(__name__)

# ========================
# CONFIG
# ========================

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

price_history = {symbol: [] for symbol in TOP_20}

account = {
    "balance": 50.0,
    "equity": 50.0,
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "position": None
}

AGGRESSION = 0.2

# ========================
# GET LIVE PRICES
# ========================

def get_prices():
    try:
        url = "https://api.binance.us/api/v3/ticker/price"
        data = requests.get(url, timeout=10).json()
        prices = {}
        for item in data:
            if item["symbol"] in TOP_20:
                prices[item["symbol"]] = float(item["price"])
        return prices
    except:
        return {}

# ========================
# MOMENTUM SCORE
# ========================

def calculate_score(prices):
    scores = {}
    for symbol in TOP_20:
        history = price_history[symbol]
        if len(history) > 10:
            change = (history[-1] - history[-10]) / history[-10]
            volatility = statistics.stdev(history[-10:])
            score = change * 100 - volatility
            scores[symbol] = round(score, 2)
        else:
            scores[symbol] = 0
    return scores

# ========================
# TRADING LOGIC
# ========================

def trade_logic():
    while True:
        prices = get_prices()

        if prices:
            for symbol, price in prices.items():
                price_history[symbol].append(price)
                if len(price_history[symbol]) > 50:
                    price_history[symbol].pop(0)

            scores = calculate_score(prices)
            sorted_coins = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            best_coin = sorted_coins[0]

            # Open position
            if account["position"] is None and best_coin[1] > 0:
                invest = account["balance"] * AGGRESSION
                account["position"] = {
                    "symbol": best_coin[0],
                    "entry": prices[best_coin[0]],
                    "amount": invest
                }
                account["balance"] -= invest

            # Close position
            if account["position"]:
                symbol = account["position"]["symbol"]
                entry = account["position"]["entry"]
                current = prices[symbol]
                change = (current - entry) / entry

                if change > 0.01 or change < -0.01:
                    profit = account["position"]["amount"] * change
                    account["balance"] += account["position"]["amount"] + profit
                    account["equity"] = account["balance"]
                    account["trades"] += 1

                    if profit > 0:
                        account["wins"] += 1
                    else:
                        account["losses"] += 1

                    account["position"] = None

        time.sleep(5)

# Start trading thread
threading.Thread(target=trade_logic, daemon=True).start()

# ========================
# DASHBOARD UI
# ========================

@app.route("/")
def dashboard():
    scores = calculate_score({})

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial; background: #0f2027; color: white; padding: 20px;}
        h1 { color: orange; }
        .card { background: #203a43; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
        table { width: 100%; }
        th, td { padding: 5px; text-align: left; }
        th { color: #00c6ff; }
    </style>
    </head>
    <body>
        <h1>🔥 ELITE AI TRADER</h1>

        <div class="card">
            <h2>Account</h2>
            Balance: ${balance}<br>
            Trades: {trades}<br>
            Wins: {wins}<br>
            Losses: {losses}<br>
            Win Rate: {winrate}%
        </div>

        <div class="card">
            <h2>Top 20 Momentum</h2>
            <table>
                <tr><th>Symbol</th><th>Score</th></tr>
                {rows}
            </table>
        </div>
    </body>
    </html>
    """

    rows = ""
    for symbol, score in sorted_scores:
        rows += f"<tr><td>{symbol}</td><td>{score}</td></tr>"

    winrate = 0
    if account["trades"] > 0:
        winrate = round((account["wins"] / account["trades"]) * 100, 2)

    return render_template_string(
        html,
        balance=round(account["balance"], 2),
        trades=account["trades"],
        wins=account["wins"],
        losses=account["losses"],
        winrate=winrate,
        rows=rows
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)