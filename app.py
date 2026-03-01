from flask import Flask, render_template_string
import requests
import statistics
import time

app = Flask(__name__)

# =========================
# CONFIG
# =========================

STARTING_CASH = 50
MAX_POSITIONS = 7
RISK_PER_TRADE = 0.20
STOP_LOSS = -0.05
TAKE_PROFIT = 0.15

state = {
    "cash": STARTING_CASH,
    "portfolio": {},
    "history": [],
    "wins": 0,
    "losses": 0,
    "level": 1,
    "memory": {}  # reinforcement score memory
}

# =========================
# BINANCE MARKET DATA
# =========================

def get_market():

    try:
        tickers = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=10).json()
        prices = requests.get("https://api.binance.com/api/v3/ticker/price", timeout=10).json()

        usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]
        usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)[:35]

        market = []

        for coin in usdt_pairs:
            symbol = coin["symbol"]
            price = float(coin["lastPrice"])
            change = float(coin["priceChangePercent"])

            score = score_coin(symbol, price, change)

            market.append({
                "symbol": symbol.replace("USDT",""),
                "price": price,
                "change": change,
                "score": score
            })

        market.sort(key=lambda x: x["score"], reverse=True)
        return market

    except:
        return []

# =========================
# EMA + RSI + REINFORCEMENT
# =========================

def score_coin(symbol, price, change):

    if symbol not in state["memory"]:
        state["memory"][symbol] = []

    state["memory"][symbol].append(change)
    if len(state["memory"][symbol]) > 14:
        state["memory"][symbol].pop(0)

    history = state["memory"][symbol]

    if len(history) < 6:
        return 0

    # EMA approximation
    ema_short = statistics.mean(history[-5:])
    ema_long = statistics.mean(history)

    trend_score = ema_short - ema_long

    # RSI approximation
    gains = [x for x in history if x > 0]
    losses = [-x for x in history if x < 0]

    avg_gain = statistics.mean(gains) if gains else 0
    avg_loss = statistics.mean(losses) if losses else 1

    rs = avg_gain / avg_loss if avg_loss != 0 else 0
    rsi = 100 - (100 / (1 + rs))

    rsi_score = 0
    if 40 < rsi < 70:
        rsi_score = 2
    elif rsi <= 30:
        rsi_score = 3
    elif rsi >= 80:
        rsi_score = -2

    reinforcement_bonus = change / 3

    total_score = trend_score + rsi_score + reinforcement_bonus

    return round(total_score, 2)

# =========================
# TRADING ENGINE
# =========================

def simulate(market):

    if not market:
        return

    # SELL LOGIC
    for symbol in list(state["portfolio"].keys()):
        position = state["portfolio"][symbol]
        coin = next((c for c in market if c["symbol"] == symbol), None)

        if not coin:
            continue

        current_price = coin["price"]
        pnl = (current_price - position["entry"]) / position["entry"]

        if pnl <= STOP_LOSS or pnl >= TAKE_PROFIT or coin["score"] < 0:
            value = position["qty"] * current_price
            state["cash"] += value

            if pnl > 0:
                state["wins"] += 1
            else:
                state["losses"] += 1

            state["history"].insert(0, f"SELL {symbol} | {round(pnl*100,2)}%")
            del state["portfolio"][symbol]

    # BUY LOGIC
    for coin in market:
        if len(state["portfolio"]) >= MAX_POSITIONS:
            break

        if coin["symbol"] in state["portfolio"]:
            continue

        if coin["score"] > 3 and state["cash"] > 5:

            amount = state["cash"] * RISK_PER_TRADE
            qty = amount / coin["price"]

            state["portfolio"][coin["symbol"]] = {
                "entry": coin["price"],
                "qty": qty
            }

            state["cash"] -= amount
            state["history"].insert(0, f"BUY {coin['symbol']}")

    # LEVEL SYSTEM
    equity = total_equity(market)
    if equity > STARTING_CASH * (1 + 0.25 * state["level"]):
        state["level"] += 1
        state["history"].insert(0, f"LEVEL UP {state['level']}")

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
    simulate(market)
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

    history_rows = "".join([f"<li>{h}</li>" for h in state["history"][:20]])

    return render_template_string(f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="20">
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

    <h1>🤖 ELITE AI TRADER v5</h1>

    <div class="card">
        Level: {state["level"]}<br>
        Cash: ${round(state["cash"],2)}<br>
        Total Equity: ${equity}<br>
        Wins: {state["wins"]} | Losses: {state["losses"]} | Trades: {len(state["history"])}
    </div>

    <div class="card">
        <h2>Portfolio (0-7)</h2>
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)