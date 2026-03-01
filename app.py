from flask import Flask, render_template_string
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)

# ==============================
# CONFIG
# ==============================

STARTING_CASH = 50
TOP_COINS = 35
MAX_HOLDINGS = 7
LEVEL_UP_EVERY = 25  # $ profit milestone

# ==============================
# ACCOUNT STATE
# ==============================

account = {
    "cash": STARTING_CASH,
    "level": 1,
    "wins": 0,
    "losses": 0,
    "trades": 0
}

portfolio = {}  # symbol: {entry, amount}
trade_history = []
last_market = []

# ==============================
# MARKET FETCH
# ==============================

def get_market():
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            timeout=15
        )

        if response.status_code != 200:
            return []

        data = response.json()

        usdt_pairs = [
            x for x in data
            if x["symbol"].endswith("USDT")
            and not any(bad in x["symbol"] for bad in ["UP", "DOWN", "BULL", "BEAR"])
        ]

        sorted_pairs = sorted(
            usdt_pairs,
            key=lambda x: float(x["quoteVolume"]),
            reverse=True
        )

        coins = []

        for coin in sorted_pairs[:TOP_COINS]:
            try:
                price = float(coin["lastPrice"])
                change = float(coin["priceChangePercent"])
                volume = float(coin["quoteVolume"])

                score = 0
                if change > 0: score += 1
                if change > 2: score += 1
                if change > 4: score += 1
                if volume > 100_000_000: score += 1

                coins.append({
                    "symbol": coin["symbol"],
                    "price": price,
                    "change": change,
                    "volume": volume,
                    "score": score
                })
            except:
                continue

        return coins

    except:
        return []

# ==============================
# TRADING LOGIC
# ==============================

def total_equity():
    total = account["cash"]
    for symbol, data in portfolio.items():
        market_price = next((c["price"] for c in last_market if c["symbol"] == symbol), data["entry"])
        total += data["amount"] * market_price
    return round(total, 2)

def level_up_check():
    profit = total_equity() - STARTING_CASH
    new_level = int(profit // LEVEL_UP_EVERY) + 1
    account["level"] = max(1, new_level)

def trade():
    global last_market

    market = get_market()
    if not market:
        return

    last_market = market
    level_up_check()

    aggression = min(0.25 + (account["level"] * 0.02), 0.6)

    # SELL LOGIC
    for symbol in list(portfolio.keys()):
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if not coin:
            continue

        entry = portfolio[symbol]["entry"]
        current = coin["price"]
        change = ((current - entry) / entry) * 100

        # Adaptive exit
        if change > 4 + account["level"] or change < -5:
            amount = portfolio[symbol]["amount"]
            account["cash"] += amount * current

            if change > 0:
                account["wins"] += 1
            else:
                account["losses"] += 1

            trade_history.insert(0, f"{datetime.now().strftime('%H:%M:%S')} SELL {symbol} {round(change,2)}%")
            del portfolio[symbol]
            account["trades"] += 1

    # BUY LOGIC
    sorted_market = sorted(market, key=lambda x: x["score"], reverse=True)

    for coin in sorted_market:
        if len(portfolio) >= MAX_HOLDINGS:
            break

        if coin["symbol"] in portfolio:
            continue

        if coin["score"] >= 3:
            allocation = account["cash"] * aggression / (MAX_HOLDINGS - len(portfolio))
            if allocation <= 1:
                continue

            amount = allocation / coin["price"]
            account["cash"] -= allocation

            portfolio[coin["symbol"]] = {
                "entry": coin["price"],
                "amount": amount
            }

            trade_history.insert(0, f"{datetime.now().strftime('%H:%M:%S')} BUY {coin['symbol']}")
            account["trades"] += 1

# ==============================
# BACKGROUND LOOP
# ==============================

def trader_loop():
    while True:
        trade()
        time.sleep(20)

threading.Thread(target=trader_loop, daemon=True).start()

# ==============================
# DASHBOARD UI
# ==============================

@app.route("/")
def dashboard():
    equity = total_equity()

    portfolio_rows = ""
    for symbol, data in portfolio.items():
        current_price = next((c["price"] for c in last_market if c["symbol"] == symbol), data["entry"])
        value = round(current_price * data["amount"], 2)
        portfolio_rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${round(data['entry'],4)}</td>
            <td>${round(current_price,4)}</td>
            <td>${value}</td>
        </tr>
        """

    market_rows = ""
    for coin in last_market:
        market_rows += f"""
        <tr>
            <td>{coin['symbol']}</td>
            <td>${round(coin['price'],4)}</td>
            <td>{round(coin['change'],2)}%</td>
            <td>{coin['score']}</td>
        </tr>
        """

    trade_rows = ""
    for t in trade_history[:15]:
        trade_rows += f"<p>{t}</p>"

    return render_template_string(f"""
    <html>
    <head>
    <title>ELITE AI TRADER</title>
    <style>
        body {{
            background: #0f172a;
            color: white;
            font-family: Arial;
            padding: 30px;
        }}
        .card {{
            background: #1e293b;
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
            color: #38bdf8;
        }}
    </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="card">
        <h2>Account</h2>
        <p>Level: {account['level']}</p>
        <p>Cash: ${round(account['cash'],2)}</p>
        <p>Total Equity: ${equity}</p>
        <p>Wins: {account['wins']} | Losses: {account['losses']} | Trades: {account['trades']}</p>
    </div>

    <div class="card">
        <h2>Portfolio (0-7 Coins)</h2>
        <table>
            <tr>
                <th>Coin</th>
                <th>Entry</th>
                <th>Current</th>
                <th>$ Value</th>
            </tr>
            {portfolio_rows}
        </table>
    </div>

    <div class="card">
        <h2>Top 35 Market</h2>
        <table>
            <tr>
                <th>Coin</th>
                <th>Price</th>
                <th>24h %</th>
                <th>Score</th>
            </tr>
            {market_rows}
        </table>
    </div>

    <div class="card">
        <h2>Trade History</h2>
        {trade_rows}
    </div>

    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)