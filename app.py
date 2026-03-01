from flask import Flask
import requests
import random
import time

app = Flask(__name__)

STARTING_CASH = 50
MAX_POSITIONS = 7

portfolio = {}
entry_prices = {}
cash = STARTING_CASH
trade_log = []
bot_level = 1
xp = 0
wins = 0
losses = 0


# -----------------------
# SCORING ENGINE
# -----------------------
def score_coin(change):
    noise = random.uniform(-1, 1)
    level_boost = bot_level * 0.3
    return change + noise + level_boost


# -----------------------
# LIVE MARKET
# -----------------------
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

            market.append({
                "symbol": symbol,
                "price": price,
                "change": change,
                "score": score_coin(change)
            })

        market.sort(key=lambda x: x["score"], reverse=True)
        return market

    except:
        return []


# -----------------------
# LEVEL SYSTEM
# -----------------------
def level_up():
    global xp, bot_level
    if xp >= bot_level * 5:
        xp = 0
        bot_level += 1


# -----------------------
# TRADE LOGIC
# -----------------------
def trade_logic(market):
    global cash, xp, wins, losses

    if not market:
        return

    top = market[:10]

    # SELL LOGIC
    for symbol in list(portfolio.keys()):
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if not coin:
            continue

        if coin["score"] < -3:
            amount = portfolio[symbol]
            sell_value = amount * coin["price"]
            entry_value = amount * entry_prices[symbol]
            pnl = sell_value - entry_value

            cash += sell_value

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            trade_log.append(
                f"SOLD {symbol} | PnL: ${round(pnl,2)}"
            )

            del portfolio[symbol]
            del entry_prices[symbol]
            xp += 1

    # BUY LOGIC
    for coin in top:
        if len(portfolio) >= MAX_POSITIONS:
            break

        if coin["score"] > 3 and coin["symbol"] not in portfolio:
            invest = cash * 0.2
            if invest > 1:
                qty = invest / coin["price"]
                portfolio[coin["symbol"]] = qty
                entry_prices[coin["symbol"]] = coin["price"]
                cash -= invest

                trade_log.append(
                    f"BOUGHT {coin['symbol']} @ ${round(coin['price'],4)}"
                )
                xp += 1

    level_up()


# -----------------------
# DASHBOARD
# -----------------------
@app.route("/")
def dashboard():
    market = get_market()
    trade_logic(market)

    total_positions = 0

    for symbol, amount in portfolio.items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            total_positions += amount * coin["price"]

    total_equity = cash + total_positions

    winrate = round((wins / (wins + losses) * 100), 2) if (wins + losses) > 0 else 0

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <title>ELITE AI TRADER</title>
        <style>
            body {{
                background:#0f172a;
                font-family:Arial;
                color:white;
                padding:20px;
            }}
            h1 {{
                color:#38bdf8;
            }}
            .card {{
                background:#1e293b;
                padding:15px;
                border-radius:10px;
                margin-bottom:20px;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
            }}
            th, td {{
                padding:8px;
                border-bottom:1px solid #334155;
            }}
            .green {{ color:#22c55e; }}
            .red {{ color:#ef4444; }}
        </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="card">
        <h3>Level: {bot_level}</h3>
        <h3>Cash: ${round(cash,2)}</h3>
        <h3>Portfolio Value: ${round(total_positions,2)}</h3>
        <h2>Total Equity: ${round(total_equity,2)}</h2>
        <h3 class="green">Wins: {wins}</h3>
        <h3 class="red">Losses: {losses}</h3>
        <h3>Win Rate: {winrate}%</h3>
    </div>

    <div class="card">
        <h2>Held Coins (0-7)</h2>
        <table>
        <tr>
            <th>Coin</th>
            <th>Amount</th>
            <th>Entry</th>
            <th>Current</th>
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
                <td>${round(entry_prices[symbol],4)}</td>
                <td>${round(coin['price'],4)}</td>
                <td>${round(value,2)}</td>
            </tr>
            """

    html += "</table></div>"

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
            <td>${round(coin['price'],4)}</td>
            <td class="{color}">{round(coin['change'],2)}%</td>
            <td>{round(coin['score'],2)}</td>
        </tr>
        """

    html += "</table></div>"

    html += """
    <div class="card">
        <h2>Trade History</h2>
    """

    for trade in reversed(trade_log[-15:]):
        html += f"<p>{trade}</p>"

    html += "</div></body></html>"

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)