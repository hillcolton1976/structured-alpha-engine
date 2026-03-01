from flask import Flask, render_template_string
import requests
import random
import time

app = Flask(__name__)

# =============================
# CONFIG
# =============================

STARTING_CASH = 50
TOP_COINS = 35
MAX_POSITIONS = 7
TRADE_SIZE_PERCENT = 0.15
LEVEL_UP_EQUITY = 60  # level up at $60, then scales

# =============================
# STATE
# =============================

state = {
    "cash": STARTING_CASH,
    "portfolio": {},  # symbol -> {entry, qty}
    "history": [],
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "level": 1,
    "xp": 0,
    "last_update": 0
}

# =============================
# MARKET DATA (CoinGecko)
# =============================

def get_market():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "volume_desc",
                "per_page": TOP_COINS,
                "page": 1,
                "price_change_percentage": "24h"
            },
            timeout=15
        )

        data = r.json()

        coins = []
        for c in data:
            price = float(c["current_price"])
            change = float(c["price_change_percentage_24h"] or 0)
            volume = float(c["total_volume"])

            score = 0

            # Momentum
            if change > 0:
                score += 2
            if change > 3:
                score += 2
            if change < -3:
                score -= 2

            # Volume strength
            if volume > 50_000_000:
                score += 1

            # Small randomness for "AI personality"
            score += random.uniform(-0.5, 0.5)

            coins.append({
                "symbol": c["symbol"].upper(),
                "name": c["name"],
                "price": price,
                "change": change,
                "score": round(score, 2)
            })

        coins.sort(key=lambda x: x["score"], reverse=True)
        return coins

    except Exception as e:
        print("MARKET ERROR:", e)
        return []

# =============================
# TRADING LOGIC
# =============================

def simulate_trading(market):

    if not market:
        return

    # ===== SELL LOGIC =====
    for symbol in list(state["portfolio"].keys()):
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if not coin:
            continue

        entry = state["portfolio"][symbol]["entry"]
        qty = state["portfolio"][symbol]["qty"]
        current_price = coin["price"]

        pnl_percent = (current_price - entry) / entry * 100

        # take profit
        if pnl_percent > 5:
            sell(symbol, current_price, qty)

        # stop loss
        elif pnl_percent < -5:
            sell(symbol, current_price, qty)

    # ===== BUY LOGIC =====
    if len(state["portfolio"]) >= MAX_POSITIONS:
        return

    for coin in market[:10]:  # only top 10 scored
        if coin["symbol"] in state["portfolio"]:
            continue

        if coin["score"] > 2 and state["cash"] > 5:
            buy(coin["symbol"], coin["price"])
            break


def buy(symbol, price):
    allocation = state["cash"] * TRADE_SIZE_PERCENT
    qty = allocation / price

    state["cash"] -= allocation
    state["portfolio"][symbol] = {
        "entry": price,
        "qty": qty
    }

    state["history"].insert(0, f"BUY {symbol} @ ${round(price,4)}")
    state["trades"] += 1


def sell(symbol, price, qty):
    entry = state["portfolio"][symbol]["entry"]
    value = qty * price
    cost = qty * entry

    profit = value - cost

    state["cash"] += value
    del state["portfolio"][symbol]

    if profit > 0:
        state["wins"] += 1
        state["xp"] += 10
    else:
        state["losses"] += 1
        state["xp"] += 3

    state["history"].insert(0, f"SELL {symbol} @ ${round(price,4)} | P/L ${round(profit,2)}")
    state["trades"] += 1


# =============================
# LEVEL SYSTEM
# =============================

def check_level_up(total_equity):
    required = LEVEL_UP_EQUITY + (state["level"] - 1) * 20

    if total_equity >= required:
        state["level"] += 1
        state["history"].insert(0, f"LEVEL UP! Now Level {state['level']}")


# =============================
# DASHBOARD
# =============================

@app.route("/")
def dashboard():

    now = time.time()
    if now - state["last_update"] > 20:  # trade every 20 seconds
        market = get_market()
        simulate_trading(market)
        state["last_update"] = now
    else:
        market = get_market()

    # calculate total equity
    invested_value = 0
    for symbol, pos in state["portfolio"].items():
        coin = next((c for c in market if c["symbol"] == symbol), None)
        if coin:
            invested_value += pos["qty"] * coin["price"]

    total_equity = state["cash"] + invested_value

    check_level_up(total_equity)

    # HTML
    html = """
    <html>
    <head>
    <title>ELITE AI TRADER</title>
    <meta http-equiv="refresh" content="10">
    <style>
        body {background:#0b1220;color:white;font-family:Arial;padding:20px}
        h1 {color:#7df9ff}
        .card {background:#1a2238;padding:20px;margin-bottom:20px;border-radius:10px}
        table {width:100%}
        th {text-align:left;color:#7df9ff}
        td {padding:4px}
    </style>
    </head>
    <body>

    <h1>🤖 ELITE AI TRADER</h1>

    <div class="card">
    <b>Level:</b> {{level}}<br>
    <b>Cash:</b> ${{cash}}<br>
    <b>Total Equity:</b> ${{equity}}<br>
    <b>Wins:</b> {{wins}} | <b>Losses:</b> {{losses}} | <b>Trades:</b> {{trades}}
    </div>

    <div class="card">
    <h3>Portfolio (0-7 Coins)</h3>
    <table>
    <tr><th>Coin</th><th>Entry</th><th>Current</th><th>$ Value</th></tr>
    {% for symbol, pos in portfolio.items() %}
        {% set coin = market|selectattr("symbol","equalto",symbol)|first %}
        {% if coin %}
        <tr>
        <td>{{symbol}}</td>
        <td>${{pos.entry}}</td>
        <td>${{coin.price}}</td>
        <td>${{(pos.qty * coin.price)|round(2)}}</td>
        </tr>
        {% endif %}
    {% endfor %}
    </table>
    </div>

    <div class="card">
    <h3>Top 35 Market</h3>
    <table>
    <tr><th>Coin</th><th>Price</th><th>24h %</th><th>Score</th></tr>
    {% for c in market %}
    <tr>
    <td>{{c.symbol}}</td>
    <td>${{c.price}}</td>
    <td>{{c.change}}%</td>
    <td>{{c.score}}</td>
    </tr>
    {% endfor %}
    </table>
    </div>

    <div class="card">
    <h3>Trade History</h3>
    {% for h in history[:15] %}
        {{h}}<br>
    {% endfor %}
    </div>

    </body>
    </html>
    """

    return render_template_string(
        html,
        level=state["level"],
        cash=round(state["cash"],2),
        equity=round(total_equity,2),
        wins=state["wins"],
        losses=state["losses"],
        trades=state["trades"],
        portfolio=state["portfolio"],
        market=market,
        history=state["history"]
    )

if __name__ == "__main__":
    app.run()