import requests
import time
import threading
from flask import Flask

app = Flask(__name__)

# =========================
# CONFIG
# =========================

STARTING_CASH = 50
MAX_COINS = 35
CACHE_SECONDS = 60

state = {
    "cash": STARTING_CASH,
    "positions": {},
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "last_market": [],
    "last_fetch": 0,
    "mode": "BOOTING",
    "deployment": 0
}

# =========================
# MARKET FETCH (CACHED)
# =========================

def get_market():
    now = time.time()

    # Use cached data
    if now - state["last_fetch"] < CACHE_SECONDS:
        return state["last_market"]

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": MAX_COINS,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h"
    }

    try:
        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            print("API ERROR:", r.status_code)
            return state["last_market"]

        data = r.json()

        coins = []
        for c in data:
            coins.append({
                "symbol": c["symbol"].upper(),
                "price": c["current_price"],
                "change": c.get("price_change_percentage_24h") or 0
            })

        state["last_market"] = coins
        state["last_fetch"] = now
        return coins

    except Exception as e:
        print("MARKET ERROR:", e)
        return state["last_market"]

# =========================
# AI LOGIC
# =========================

def rebalance():
    coins = get_market()

    if not coins:
        state["mode"] = "API ERROR"
        return

    # Market health
    positives = len([c for c in coins if c["change"] > 0])
    market_strength = positives / len(coins)

    state["deployment"] = round(market_strength * 100, 1)

    if market_strength > 0.65:
        state["mode"] = "BULL MODE"
        deploy_percent = 0.90
    elif market_strength > 0.45:
        state["mode"] = "NEUTRAL"
        deploy_percent = 0.60
    else:
        state["mode"] = "DEFENSIVE"
        deploy_percent = 0.30

    target_in_market = state["cash"] * deploy_percent

    # Sort strongest gainers
    coins = sorted(coins, key=lambda x: x["change"], reverse=True)

    top = coins[:5]

    if target_in_market <= 0:
        return

    allocation = target_in_market / len(top)

    for coin in top:
        price = coin["price"]
        if price <= 0:
            continue

        qty = allocation / price

        state["positions"][coin["symbol"]] = {
            "qty": qty,
            "price": price
        }

        state["cash"] -= allocation
        state["trades"] += 1

# =========================
# BACKGROUND TRADER
# =========================

def trader():
    while True:
        rebalance()
        time.sleep(60)

threading.Thread(target=trader, daemon=True).start()

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():

    coins = get_market()

    total_positions_value = 0
    rows = ""

    for symbol, data in state["positions"].items():
        current_price = next((c["price"] for c in coins if c["symbol"] == symbol), data["price"])
        value = data["qty"] * current_price
        total_positions_value += value

        rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>{round(data['qty'],4)}</td>
            <td>${round(value,2)}</td>
        </tr>
        """

    total_equity = state["cash"] + total_positions_value

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{
                background:#0f172a;
                color:white;
                font-family:Arial;
                padding:30px;
            }}
            h1 {{
                color:#00ffcc;
            }}
            .card {{
                background:#1e293b;
                padding:20px;
                border-radius:12px;
                margin-bottom:20px;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
            }}
            th, td {{
                padding:10px;
                text-align:left;
            }}
            th {{
                background:#334155;
            }}
            tr:nth-child(even) {{
                background:#1e293b;
            }}
        </style>
    </head>
    <body>

        <h1>ELITE AI TRADER</h1>

        <div class="card">
            <b>Mode:</b> {state["mode"]}<br>
            <b>Market Deployment:</b> {state["deployment"]}%<br>
            <b>Cash:</b> ${round(state["cash"],2)}<br>
            <b>Invested:</b> ${round(total_positions_value,2)}<br>
            <b>Total Equity:</b> ${round(total_equity,2)}<br>
            <b>Total Trades:</b> {state["trades"]}
        </div>

        <div class="card">
            <h2>Positions</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Quantity</th>
                    <th>Value</th>
                </tr>
                {rows}
            </table>
        </div>

    </body>
    </html>
    """

    return html