from flask import Flask
import requests
import random
import time

app = Flask(__name__)

STARTING_CASH = 50
MAX_POSITIONS = 7

portfolio = {}
cash = STARTING_CASH
trade_log = []
bot_level = 1
xp = 0


# -----------------------------
# SCORING ENGINE
# -----------------------------
def score_coin(symbol, price, change):
    base = change

    # slight randomness to simulate adaptive AI
    noise = random.uniform(-1.5, 1.5)

    level_boost = bot_level * 0.2

    return base + noise + level_boost


# -----------------------------
# LIVE MARKET (CoinGecko)
# -----------------------------
def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"

        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 35,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            return []

        data = r.json()

        market = []

        for coin in data:
            symbol = coin["symbol"].upper()
            price = float(coin["current_price"])
            change = float(coin["price_change_percentage_24h"] or 0)

            score = score_coin(symbol, price, change)

            market.append({
                "symbol": symbol,
                "price": price,
                "change": change,
                "score": score
            })

        market.sort(key=lambda x: x["score"], reverse=True)
        return market

    except:
        return []


# -----------------------------
# LEVEL SYSTEM
# -----------------------------
def level_up():
    global xp, bot_level
    if xp >= bot_level * 5:
        xp = 0
        bot_level += 1


# -----------------------------
# TRADING ENGINE
# -----------------------------
def trade_logic(market):
    global cash, xp

    if not market:
        return

    top_coins = market[:10]

    # SELL LOGIC
    for symbol in list(portfolio.keys()):
        coin = next((c for c in market if c["symbol"] == symbol), None)

        if coin and coin["score"] < -3:
            amount = portfolio[symbol]
            sell_value = amount * coin["price"]

            cash += sell_value
            del portfolio[symbol]

            trade_log.append(
                f"SOLD {symbol} for ${round(sell_value,2)}"
            )
            xp += 1

    # BUY LOGIC
    for coin in top_coins:
        if len(portfolio) >= MAX_POSITIONS:
            break

        if coin["score"] > 3 and coin["symbol"] not in portfolio:
            invest_amount = cash * 0.2

            if invest_amount > 1:
                quantity = invest_amount / coin["price"]
                portfolio[coin["symbol"]] = quantity
                cash -= invest_amount

                trade_log.append(
                    f"BOUGHT {coin['symbol']} for ${round(invest_amount,2)}"
                )
                xp += 1

    level_up()


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/")
def dashboard():
    market = get_market()
    trade_logic(market)

    total_positions_value = 0

    for symbol, amount in portfolio.items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            total_positions_value += amount * coin["price"]

    total_equity = cash + total_positions_value

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <title>ELITE AI TRADER</title>
        <style>
            body {{
                background:#0f111a;
                color:#00ffcc;
                font-family:Arial;
                padding:20px;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
                margin-top:10px;
            }}
            th, td {{
                padding:8px;
                border-bottom:1px solid #222;
                text-align:left;
            }}
            .box {{
                background:#1a1d2b;
                padding:15px;
                margin-bottom:20px;
                border-radius:8px;
            }}
        </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="box">
        <h3>Bot Level: {bot_level}</h3>
        <h3>Cash: ${round(cash,2)}</h3>
        <h3>Portfolio Value: ${round(total_positions_value,2)}</h3>
        <h2>Total Equity: ${round(total_equity,2)}</h2>
    </div>

    <div class="box">
        <h2>Held Coins (0-7)</h2>
        <table>
        <tr>
            <th>Coin</th>
            <th>Amount</th>
            <th>Price</th>
            <th>Value</th>
        </tr>
    """

    for symbol, amount in portfolio.items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            value = amount * coin["price"]
            html += f"""
            <tr>
                <td>{symbol}</td>
                <td>{round(amount,4)}</td>
                <td>${round(coin['price'],4)}</td>
                <td>${round(value,2)}</td>
            </tr>
            """

    html += "</table></div>"

    html += """
    <div class="box">
        <h2>Top 35 Market Coins</h2>
        <table>
        <tr>
            <th>Coin</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Score</th>
        </tr>
    """

    for coin in market:
        html += f"""
        <tr>
            <td>{coin['symbol']}</td>
            <td>${round(coin['price'],4)}</td>
            <td>{round(coin['change'],2)}%</td>
            <td>{round(coin['score'],2)}</td>
        </tr>
        """

    html += "</table></div>"

    html += """
    <div class="box">
        <h2>Trade History</h2>
    """

    for trade in reversed(trade_log[-15:]):
        html += f"<p>{trade}</p>"

    html += "</div></body></html>"

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)