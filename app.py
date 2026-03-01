import requests
import time
from flask import Flask

app = Flask(__name__)

# =========================
# CONFIG
# =========================

STARTING_CASH = 50.0
MAX_POSITIONS = 7
TOP_COINS = 35

# =========================
# STATE
# =========================

cash = STARTING_CASH
portfolio = {}  # {symbol: {"amount": float, "entry": float}}
trade_log = []

level = 1
xp = 0
wins = 0
losses = 0
total_trades = 0
profit_milestone = 10  # level up every $10 profit

last_prices = {}
last_update = 0

# =========================
# MARKET DATA
# =========================

def get_market():
    url = "https://api.binance.com/api/v3/ticker/24hr"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()

        if not isinstance(data, list):
            return []

        usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]

        # sort by volume
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

                # simple score model
                score = 0
                if change > 0:
                    score += 1
                if change > 2:
                    score += 1
                if volume > 50_000_000:
                    score += 1
                if change > 5:
                    score += 1

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

# =========================
# TRADING LOGIC
# =========================

def trade_logic(market):
    global cash, portfolio, wins, losses, total_trades, xp, level

    desired_positions = min(MAX_POSITIONS, level + 1)

    # SELL LOGIC
    for symbol in list(portfolio.keys()):
        if symbol not in [c["symbol"] for c in market]:
            continue

        coin = next(c for c in market if c["symbol"] == symbol)
        current_price = coin["price"]
        entry_price = portfolio[symbol]["entry"]

        change = (current_price - entry_price) / entry_price * 100

        # take profit or stop loss
        if change >= 5 or change <= -4:
            amount = portfolio[symbol]["amount"]
            value = amount * current_price

            cash += value
            total_trades += 1

            if change > 0:
                wins += 1
                xp += 1
            else:
                losses += 1

            trade_log.append(
                f"SOLD {symbol} | P/L: {round(change,2)}%"
            )

            del portfolio[symbol]

    # BUY LOGIC
    if len(portfolio) < desired_positions:
        for coin in market:
            if len(portfolio) >= desired_positions:
                break

            if coin["score"] < 2:
                continue

            if coin["symbol"] in portfolio:
                continue

            if cash < 5:
                break

            allocation = cash / (desired_positions - len(portfolio))
            amount = allocation / coin["price"]

            portfolio[coin["symbol"]] = {
                "amount": amount,
                "entry": coin["price"]
            }

            cash -= allocation
            total_trades += 1

            trade_log.append(
                f"BOUGHT {coin['symbol']} @ {round(coin['price'],4)}"
            )

# =========================
# LEVEL SYSTEM
# =========================

def check_level_up(total_equity):
    global level, xp, profit_milestone

    if total_equity >= STARTING_CASH + profit_milestone:
        level += 1
        profit_milestone += 10
        trade_log.append(f"🎉 LEVEL UP → {level}")

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    global last_update

    now = time.time()

    if now - last_update > 20:
        market = get_market()
        if market:
            trade_logic(market)
            last_update = now
    else:
        market = get_market()

    # calculate total equity
    total_positions_value = 0

    for symbol in portfolio:
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            total_positions_value += portfolio[symbol]["amount"] * coin["price"]

    total_equity = cash + total_positions_value

    check_level_up(total_equity)

    # =========================
    # BUILD HTML
    # =========================

    html = f"""
    <html>
    <head>
        <title>ELITE AI TRADER</title>
        <style>
            body {{
                background:#0f172a;
                color:white;
                font-family:Arial;
                padding:20px;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
            }}
            th, td {{
                padding:8px;
                text-align:left;
            }}
            tr:nth-child(even) {{
                background:#1e293b;
            }}
            .green {{ color:#22c55e; }}
            .red {{ color:#ef4444; }}
            .card {{
                background:#1e293b;
                padding:15px;
                margin-bottom:20px;
                border-radius:10px;
            }}
        </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="card">
        <h2>Account</h2>
        <p>Level: {level}</p>
        <p>Cash: ${round(cash,2)}</p>
        <p>Total Equity: ${round(total_equity,2)}</p>
        <p>Wins: {wins} | Losses: {losses} | Trades: {total_trades}</p>
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
    """

    for symbol in portfolio:
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            value = portfolio[symbol]["amount"] * coin["price"]
            html += f"""
            <tr>
                <td>{symbol}</td>
                <td>{round(portfolio[symbol]['entry'],4)}</td>
                <td>{round(coin['price'],4)}</td>
                <td>${round(value,2)}</td>
            </tr>
            """

    html += "</table></div>"

    # MARKET TABLE
    html += """
    <div class="card">
        <h2>Top 35 Market</h2>
        <table>
        <tr>
            <th>Coin</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Score</th>
        </tr>
    """

    for coin in market:
        color = "green" if coin["change"] > 0 else "red"
        html += f"""
        <tr>
            <td>{coin['symbol']}</td>
            <td>{round(coin['price'],4)}</td>
            <td class="{color}">{round(coin['change'],2)}%</td>
            <td>{coin['score']}</td>
        </tr>
        """

    html += "</table></div>"

    # TRADE LOG
    html += """
    <div class="card">
        <h2>Trade History</h2>
    """

    for trade in reversed(trade_log[-15:]):
        html += f"<p>{trade}</p>"

    html += "</div></body></html>"

    return html

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)