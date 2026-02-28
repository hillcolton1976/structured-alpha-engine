from flask import Flask, render_template_string
import requests
import threading
import time
import statistics

app = Flask(__name__)

TOP_20 = [
    "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","LINKUSDT","MATICUSDT",
    "TRXUSDT","DOTUSDT","LTCUSDT","BCHUSDT","ATOMUSDT",
    "NEARUSDT","UNIUSDT","APTUSDT","ARBUSDT","OPUSDT"
]

price_history = {symbol: [] for symbol in TOP_20}

account = {
    "balance": 50.0,
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "position": None
}

AGGRESSION = 0.2
TAKE_PROFIT = 0.02
STOP_LOSS = 0.01


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


def calculate_scores():
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


def trader():
    while True:
        prices = get_prices()
        if not prices:
            time.sleep(5)
            continue

        for symbol, price in prices.items():
            price_history[symbol].append(price)
            if len(price_history[symbol]) > 50:
                price_history[symbol].pop(0)

        scores = calculate_scores()
        best = max(scores, key=scores.get)

        # ENTER TRADE
        if account["position"] is None and scores[best] > 0:
            entry_price = prices[best]
            size = account["balance"] * AGGRESSION
            account["position"] = {
                "symbol": best,
                "entry": entry_price,
                "size": size
            }

        # EXIT TRADE
        if account["position"]:
            symbol = account["position"]["symbol"]
            entry = account["position"]["entry"]
            size = account["position"]["size"]
            current = prices.get(symbol, entry)

            change = (current - entry) / entry

            if change >= TAKE_PROFIT or change <= -STOP_LOSS:
                pnl = size * change
                account["balance"] += pnl
                account["trades"] += 1

                if pnl > 0:
                    account["wins"] += 1
                else:
                    account["losses"] += 1

                account["position"] = None

        time.sleep(5)


threading.Thread(target=trader, daemon=True).start()


@app.route("/")
def dashboard():
    scores = calculate_scores()
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    winrate = 0
    if account["trades"] > 0:
        winrate = round((account["wins"] / account["trades"]) * 100, 2)

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="5">
    <style>
        body { font-family: Arial; background: #0f2027; color: white; padding: 20px;}
        h1 { color: orange; }
        .card { background: #203a43; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 6px; text-align: left; }
        th { color: #00c6ff; border-bottom: 1px solid #555; }
    </style>
    </head>
    <body>
        <h1>🔥 ELITE AI TRADER</h1>

        <div class="card">
            <h2>Account</h2>
            Balance: ${{ balance }}<br>
            Trades: {{ trades }}<br>
            Wins: {{ wins }}<br>
            Losses: {{ losses }}<br>
            Win Rate: {{ winrate }}%
        </div>

        <div class="card">
            <h2>Open Position</h2>
            {% if position %}
                Symbol: {{ position.symbol }}<br>
                Entry: {{ position.entry }}<br>
                Size: ${{ position.size }}
            {% else %}
                None
            {% endif %}
        </div>

        <div class="card">
            <h2>Top 20 Momentum</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Score</th>
                </tr>
                {% for symbol, score in scores %}
                <tr>
                    <td>{{ symbol }}</td>
                    <td>{{ score }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """

    return render_template_string(
        html,
        balance=round(account["balance"], 2),
        trades=account["trades"],
        wins=account["wins"],
        losses=account["losses"],
        winrate=winrate,
        scores=sorted_scores,
        position=account["position"]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)