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

last_market = []
last_fetch_time = 0


# -------------------------
# SCORE ENGINE
# -------------------------
def score_coin(change):
    noise = random.uniform(-1, 1)
    intelligence = bot_level * 0.3
    return change + noise + intelligence


# -------------------------
# FETCH MARKET (with fallback)
# -------------------------
def get_market():
    global last_market, last_fetch_time

    # Avoid spamming CoinGecko
    if time.time() - last_fetch_time < 25 and last_market:
        return last_market

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
            return last_market

        data = r.json()

        market = []
        for coin in data:
            market.append({
                "symbol": coin["symbol"].upper(),
                "price": float(coin["current_price"]),
                "change": float(coin["price_change_percentage_24h"] or 0),
            })

        for coin in market:
            coin["score"] = score_coin(coin["change"])

        market.sort(key=lambda x: x["score"], reverse=True)

        last_market = market
        last_fetch_time = time.time()

        return market

    except:
        return last_market


# -------------------------
# LEVEL SYSTEM
# -------------------------
def level_up():
    global xp, bot_level
    if xp >= bot_level * 5:
        xp = 0
        bot_level += 1


# -------------------------
# TRADE LOGIC
# -------------------------
def trade_logic(market):
    global cash, wins, losses, xp

    if not market:
        return

    # SELL
    for symbol in list(portfolio.keys()):
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if not coin:
            continue

        if coin["score"] < -3:
            qty = portfolio[symbol]
            sell_value = qty * coin["price"]
            entry_value = qty * entry_prices[symbol]
            pnl = sell_value - entry_value

            cash += sell_value

            if pnl > 0:
                wins += 1
            else:
                losses += 1

            trade_log.append(
                f"SOLD {symbol} | PnL ${round(pnl,2)}"
            )

            del portfolio[symbol]
            del entry_prices[symbol]
            xp += 1

    # BUY
    for coin in market[:12]:
        if len(portfolio) >= MAX_POSITIONS:
            break

        if coin["score"] > 4 and coin["symbol"] not in portfolio:
            invest_amount = cash * 0.20

            if invest_amount > 2:
                qty = invest_amount / coin["price"]

                portfolio[coin["symbol"]] = qty
                entry_prices[coin["symbol"]] = coin["price"]
                cash -= invest_amount

                trade_log.append(
                    f"BOUGHT {coin['symbol']} @ ${round(coin['price'],4)}"
                )

                xp += 1

    level_up()


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/")
def dashboard():
    market = get_market()
    trade_logic(market)

    total_positions_value = 0

    for symbol, qty in portfolio.items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            total_positions_value += qty * coin["price"]

    total_equity = cash + total_positions_value
    total_trades = wins + losses
    winrate = round((wins / total_trades * 100), 2) if total_trades > 0 else 0

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="30">
        <title>ELITE AI TRADER</title>
        <style>
            body {{
                background:linear-gradient(135deg,#0f172a,#020617);
                color:white;
                font-family:Arial;
                padding:25px;
            }}
            h1 {{
                color:#38bdf8;
            }}
            .card {{
                background:#1e293b;
                padding:18px;
                border-radius:15px;
                margin-bottom:25px;
                box-shadow:0 0 20px rgba(0,0,0,0.5);
            }}
            table {{
                width:100%;
                border-collapse:collapse;
            }}
            th, td {{
                padding:10px;
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
        <h3>Portfolio Value: ${round(total_positions_value,2)}</h3>
        <h2>Total Equity: ${round(total_equity,2)}</h2>
        <h3 class="green">Wins: {wins}</h3>
        <h3 class="red">Losses: {losses}</h3>
        <h3>Win Rate: {winrate}%</h3>
    </div>
    """

    # Held coins
    html += """
    <div class="card">
        <h2>Held Coins (0–7)</h2>
        <table>
        <tr>
            <th>Coin</th>
            <th>Amount</th>
            <th>Entry</th>
            <th>Current</th>
            <th>Value</th>
        </tr>
    """

    for symbol, qty in portfolio.items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            value = qty * coin["price"]
            html += f"""
            <tr>
                <td>{symbol}</td>
                <td>{round(qty,4)}</td>
                <td>${round(entry_prices[symbol],4)}</td>
                <td>${round(coin['price'],4)}</td>
                <td>${round(value,2)}</td>
            </tr>
            """

    html += "</table></div>"

    # Market
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

    # Trade history
    html += """
    <div class="card">
        <h2>Trade History</h2>
    """

    for trade in reversed(trade_log[-20:]):
        html += f"<p>{trade}</p>"

    html += "</div></body></html>"

    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)