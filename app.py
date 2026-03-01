import requests
import math
from flask import Flask, render_template_string

app = Flask(__name__)

# ===============================
# CONFIG
# ===============================
STARTING_CAPITAL = 50.0
MAX_POSITIONS = 3
STABLES = ["USDT", "USDC", "BUSD", "DAI", "USDS", "USDE", "USD1", "PYUSD"]

# ===============================
# GLOBAL STATE
# ===============================
state = {
    "cash": STARTING_CAPITAL,
    "positions": {},
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "mode": "WAITING",
    "deployment": 0
}

# ===============================
# FETCH MARKET DATA
# ===============================
def get_market():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 35,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }
    response = requests.get(url)
    data = response.json()

    coins = []
    for coin in data:
        coins.append({
            "symbol": coin["symbol"].upper(),
            "price": coin["current_price"],
            "change": coin["price_change_percentage_24h"] or 0
        })
    return coins

# ===============================
# MARKET REGIME DETECTION
# ===============================
def detect_market_mode(coins):
    green = [c for c in coins if c["change"] > 0]
    pct_green = len(green) / len(coins)
    avg_change = sum(c["change"] for c in coins) / len(coins)

    btc = next((c for c in coins if c["symbol"] == "BTC"), None)

    if pct_green > 0.7 and btc and btc["change"] > 0:
        return "BULL", 0.85
    elif pct_green > 0.5:
        return "TREND", 0.60
    elif pct_green > 0.3:
        return "NEUTRAL", 0.40
    else:
        return "DEFENSIVE", 0.15

# ===============================
# SELECT STRONGEST COINS
# ===============================
def select_coins(coins):
    tradable = [
        c for c in coins
        if c["symbol"] not in STABLES and c["change"] > 2.5
    ]
    tradable.sort(key=lambda x: x["change"], reverse=True)
    return tradable[:MAX_POSITIONS]

# ===============================
# REBALANCE ENGINE
# ===============================
def rebalance():
    coins = get_market()
    mode, deploy_pct = detect_market_mode(coins)

    state["mode"] = mode
    state["deployment"] = deploy_pct

    total_equity = state["cash"] + sum(
        pos["qty"] * pos["price"]
        for pos in state["positions"].values()
    )

    deploy_amount = total_equity * deploy_pct

    selected = select_coins(coins)

    state["positions"].clear()

    if not selected:
        state["cash"] = total_equity
        return coins

    weights = [0.5, 0.3, 0.2]

    state["cash"] = total_equity - deploy_amount

    for i, coin in enumerate(selected):
        allocation = deploy_amount * weights[i]
        qty = allocation / coin["price"]

        state["positions"][coin["symbol"]] = {
            "qty": qty,
            "price": coin["price"],
            "value": allocation,
            "change": coin["change"]
        }

        state["trades"] += 1

    return coins

# ===============================
# DASHBOARD
# ===============================
@app.route("/")
def dashboard():
    coins = rebalance()

    total_positions = sum(p["value"] for p in state["positions"].values())
    total_equity = state["cash"] + total_positions

    return render_template_string("""
    <html>
    <head>
    <title>ELITE AI TRADER v5</title>
    <style>
        body { background:#0f172a; color:white; font-family:Arial; padding:30px; }
        .card { background:#1e293b; padding:20px; margin-bottom:20px; border-radius:10px; }
        table { width:100%; border-collapse:collapse; }
        th, td { padding:8px; border-bottom:1px solid #334155; }
    </style>
    </head>
    <body>
    <h2>🔥 ELITE AI TRADER v5 (AUTO)</h2>

    <div class="card">
        <h3>Market Mode: {{mode}}</h3>
        <p>Capital Deployment: {{deployment*100}}%</p>
    </div>

    <div class="card">
        <h3>Account</h3>
        <p>Cash: ${{cash}}</p>
        <p>Positions Value: ${{positions_value}}</p>
        <p><b>Total Equity: ${{equity}}</b></p>
    </div>

    <div class="card">
        <h3>Open Positions</h3>
        <table>
        <tr><th>Coin</th><th>Qty</th><th>Value</th><th>24h %</th></tr>
        {% for symbol, pos in positions.items() %}
            <tr>
                <td>{{symbol}}</td>
                <td>{{"%.4f"|format(pos.qty)}}</td>
                <td>${{"%.2f"|format(pos.value)}}</td>
                <td>{{pos.change}}%</td>
            </tr>
        {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>Top 35 Market</h3>
        <table>
        <tr><th>Coin</th><th>Price</th><th>24h %</th></tr>
        {% for coin in coins %}
            <tr>
                <td>{{coin.symbol}}</td>
                <td>${{coin.price}}</td>
                <td>{{coin.change}}%</td>
            </tr>
        {% endfor %}
        </table>
    </div>

    </body>
    </html>
    """,
    coins=coins,
    positions=state["positions"],
    cash=round(state["cash"],2),
    positions_value=round(total_positions,2),
    equity=round(total_equity,2),
    mode=state["mode"],
    deployment=state["deployment"]
    )

if __name__ == "__main__":
    app.run(debug=True)