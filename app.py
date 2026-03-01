import requests
import time
import random
from flask import Flask

app = Flask(__name__)

STARTING_BALANCE = 50.0
cash = STARTING_BALANCE
positions = {}
trades = 0
wins = 0
losses = 0
level = 1

MIN_HOLD_TIME = 600
TRADE_COOLDOWN = 180
CONFIDENCE_THRESHOLD = 0.65
last_trade_time = 0


# ---------------- MARKET ----------------

def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 35,
            "page": 1,
            "sparkline": False
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        return r.json()
    except:
        return []


# ---------------- ANALYSIS ----------------

def analyze_coin(coin):
    change = coin.get("price_change_percentage_24h") or 0
    volume = coin.get("total_volume") or 0

    score = 0

    if change > 2:
        score += 0.4
    if change > 5:
        score += 0.3
    if volume > 500000000:
        score += 0.2

    score += random.uniform(0, 0.2)
    return score


# ---------------- LEVEL SYSTEM ----------------

def update_level(total_equity):
    global level
    win_rate = wins / trades if trades > 0 else 0

    if total_equity > 60 and win_rate > 0.55:
        level = 2
    if total_equity > 75 and win_rate > 0.6:
        level = 3
    if total_equity > 100 and win_rate > 0.65:
        level = 4


# ---------------- TRADING ----------------

def trade_logic():
    global cash, trades, wins, losses, last_trade_time

    market = get_market()
    if not market:
        return

    now = time.time()

    for coin in market:
        symbol = coin["symbol"].upper()
        price = coin["current_price"]

        if not price or price <= 0:
            continue

        # EXIT
        if symbol in positions:
            pos = positions[symbol]
            hold_time = now - pos["entry_time"]

            if hold_time < MIN_HOLD_TIME:
                continue

            pnl = (price - pos["entry_price"]) / pos["entry_price"]

            if pnl > 0.04 or pnl < -0.03:
                cash += pos["amount"] * price
                trades += 1
                wins += 1 if pnl > 0 else 0
                losses += 1 if pnl <= 0 else 0
                del positions[symbol]
                last_trade_time = now

        # ENTRY
        else:
            if now - last_trade_time < TRADE_COOLDOWN:
                continue

            confidence = analyze_coin(coin)

            if confidence > CONFIDENCE_THRESHOLD and cash > 5:
                allocation = 0.1 * level
                size = cash * allocation
                amount = size / price

                positions[symbol] = {
                    "entry_price": price,
                    "amount": amount,
                    "entry_time": now,
                    "invested": size
                }

                cash -= size
                last_trade_time = now


# ---------------- DASHBOARD ----------------

@app.route("/")
def dashboard():
    global cash

    trade_logic()

    market = get_market()
    price_lookup = {c["symbol"].upper(): c["current_price"] for c in market}

    total_positions_value = 0
    rows = ""

    for symbol, pos in positions.items():
        current_price = price_lookup.get(symbol, 0)
        invested = pos["invested"]
        value = pos["amount"] * current_price
        pnl_percent = ((current_price - pos["entry_price"]) / pos["entry_price"]) * 100
        total_positions_value += value

        color = "#00ff88" if pnl_percent >= 0 else "#ff4d4d"

        rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${invested:.2f}</td>
            <td>${pos['entry_price']:.4f}</td>
            <td>${current_price:.4f}</td>
            <td>${value:.2f}</td>
            <td style="color:{color}">{pnl_percent:.2f}%</td>
        </tr>
        """

    total_equity = cash + total_positions_value
    update_level(total_equity)

    win_rate = round((wins / trades) * 100, 2) if trades > 0 else 0

    return f"""
    <html>
    <head>
        <title>Elite AI Trader</title>
        <style>
            body {{
                background: #0f1117;
                color: white;
                font-family: Arial;
                padding: 20px;
            }}
            h1 {{
                color: #00ffcc;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 10px;
                text-align: center;
                border-bottom: 1px solid #333;
            }}
            th {{
                background: #1a1d26;
                color: #00ffcc;
            }}
            tr:hover {{
                background: #1f2330;
            }}
            .card {{
                background: #1a1d26;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <h1>🚀 Elite AI Trader</h1>

        <div class="card">
            <b>Cash:</b> ${cash:.2f} |
            <b>Positions Value:</b> ${total_positions_value:.2f} |
            <b>Total Equity:</b> ${total_equity:.2f}
        </div>

        <div class="card">
            <b>Level:</b> {level} |
            <b>Trades:</b> {trades} |
            <b>Wins:</b> {wins} |
            <b>Losses:</b> {losses} |
            <b>Win Rate:</b> {win_rate}%
        </div>

        <table>
            <tr>
                <th>Coin</th>
                <th>$ Invested</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Current Value</th>
                <th>PnL %</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """
    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)