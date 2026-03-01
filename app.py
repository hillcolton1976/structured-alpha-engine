from flask import Flask, render_template_string
import requests
import random
import time

app = Flask(__name__)

# =========================
# CONFIG
# =========================

STARTING_CASH = 50
MAX_POSITIONS = 7
TRADE_RISK = 0.20  # 20% of cash per trade
STOP_LOSS = -0.06
TAKE_PROFIT = 0.12

# =========================
# STATE
# =========================

state = {
    "cash": STARTING_CASH,
    "portfolio": {},  # symbol -> {entry, qty}
    "history": [],
    "wins": 0,
    "losses": 0,
    "level": 1,
    "last_scores": {},
    "score_memory": {}
}

# =========================
# MARKET DATA
# =========================

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

        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        market = []
        for coin in data:
            score = calculate_score(coin)
            market.append({
                "symbol": coin["symbol"].upper(),
                "name": coin["name"],
                "price": coin["current_price"],
                "change": coin["price_change_percentage_24h"] or 0,
                "score": score
            })

        market.sort(key=lambda x: x["score"], reverse=True)
        return market

    except:
        return []

# =========================
# SCORING ENGINE
# =========================

def calculate_score(coin):
    change = coin["price_change_percentage_24h"] or 0

    momentum = change / 5
    volatility_boost = random.uniform(0, 1)

    score = momentum + volatility_boost
    return round(score, 2)

# =========================
# TREND MEMORY
# =========================

def update_memory(symbol, score):
    if symbol not in state["score_memory"]:
        state["score_memory"][symbol] = []
    state["score_memory"][symbol].append(score)
    if len(state["score_memory"][symbol]) > 5:
        state["score_memory"][symbol].pop(0)

def accelerating(symbol):
    hist = state["score_memory"].get(symbol, [])
    if len(hist) < 3:
        return False
    return hist[-1] > hist[-2] > hist[-3]

# =========================
# TRADING LOGIC
# =========================

def simulate_trading(market):
    if not market:
        return

    # Update score memory
    for coin in market:
        update_memory(coin["symbol"], coin["score"])

    # ===== SELL LOGIC =====
    for symbol in list(state["portfolio"].keys()):
        position = state["portfolio"][symbol]
        current_coin = next((c for c in market if c["symbol"] == symbol), None)

        if not current_coin:
            continue

        current_price = current_coin["price"]
        entry = position["entry"]
        pnl = (current_price - entry) / entry

        if pnl <= STOP_LOSS or pnl >= TAKE_PROFIT or current_coin["score"] < 1:
            value = position["qty"] * current_price
            state["cash"] += value

            if pnl > 0:
                state["wins"] += 1
            else:
                state["losses"] += 1

            state["history"].insert(0, f"SELL {symbol} @ ${round(current_price,2)} | PnL: {round(pnl*100,2)}%")
            del state["portfolio"][symbol]

    # ===== BUY LOGIC =====
    for coin in market:
        symbol = coin["symbol"]

        if len(state["portfolio"]) >= MAX_POSITIONS:
            break

        if symbol in state["portfolio"]:
            continue

        if coin["score"] > 3 and accelerating(symbol):
            amount = state["cash"] * TRADE_RISK
            if amount < 5:
                continue

            qty = amount / coin["price"]

            state["portfolio"][symbol] = {
                "entry": coin["price"],
                "qty": qty
            }

            state["cash"] -= amount
            state["history"].insert(0, f"BUY {symbol} @ ${round(coin['price'],2)}")

    # ===== LEVEL SYSTEM =====
    equity = total_equity(market)
    if equity > STARTING_CASH * (1 + 0.25 * state["level"]):
        state["level"] += 1
        state["history"].insert(0, f"LEVEL UP → {state['level']}")

# =========================
# EQUITY CALC
# =========================

def total_equity(market):
    total = state["cash"]
    for symbol, pos in state["portfolio"].items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            total += pos["qty"] * coin["price"]
    return round(total, 2)

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    market = get_market()
    simulate_trading(market)

    equity = total_equity(market)

    portfolio_rows = ""
    for symbol, pos in state["portfolio"].items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            value = round(pos["qty"] * coin["price"], 2)
            portfolio_rows += f"""
            <tr>
                <td>{symbol}</td>
                <td>${round(pos['entry'],2)}</td>
                <td>${round(coin['price'],2)}</td>
                <td>${value}</td>
            </tr>
            """

    market_rows = ""
    for coin in market:
        market_rows += f"""
        <tr>
            <td>{coin['symbol']}</td>
            <td>${coin['price']}</td>
            <td>{round(coin['change'],2)}%</td>
            <td>{coin['score']}</td>
        </tr>
        """

    history_rows = ""
    for trade in state["history"][:20]:
        history_rows += f"<li>{trade}</li>"

    return render_template_string(f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="15">
    <style>
    body {{
        background: #0f172a;
        color: white;
        font-family: Arial;
        padding: 20px;
    }}
    .card {{
        background: #1e293b;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
    }}
    table {{
        width: 100%;
    }}
    th, td {{
        padding: 8px;
        text-align: left;
    }}
    </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="card">
        <h2>Account</h2>
        Level: {state["level"]}<br>
        Cash: ${round(state["cash"],2)}<br>
        Total Equity: ${equity}<br>
        Wins: {state["wins"]} | Losses: {state["losses"]} | Trades: {len(state["history"])}
    </div>

    <div class="card">
        <h2>Portfolio (0-7 Coins)</h2>
        <table>
        <tr><th>Coin</th><th>Entry</th><th>Current</th><th>$ Value</th></tr>
        {portfolio_rows}
        </table>
    </div>

    <div class="card">
        <h2>Top 35 Market</h2>
        <table>
        <tr><th>Coin</th><th>Price</th><th>24h %</th><th>Score</th></tr>
        {market_rows}
        </table>
    </div>

    <div class="card">
        <h2>Trade History</h2>
        <ul>{history_rows}</ul>
    </div>

    </body>
    </html>
    """)

# =========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)