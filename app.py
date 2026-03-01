from flask import Flask, render_template_string
import requests
import random

app = Flask(__name__)

STARTING_CASH = 50.0

account = {
    "cash": STARTING_CASH,
    "positions": {},
    "trades": 0,
    "wins": 0,
    "losses": 0
}

# -----------------------------
# GET REAL MARKET DATA
# -----------------------------
def get_top_35_usdt():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)
        data = response.json()

        # Make sure we actually received a list
        if not isinstance(data, list):
            print("API returned unexpected data:", data)
            return []

        # Filter USDT pairs only
        usdt_pairs = [x for x in data if x["symbol"].endswith("USDT")]

        # Sort by quote volume (biggest markets first)
        usdt_pairs.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)

        top_35 = usdt_pairs[:35]

        result = []
        for coin in top_35:
            result.append({
                "symbol": coin["symbol"],
                "price": float(coin["lastPrice"]),
                "change": float(coin["priceChangePercent"])
            })

        return result

    except Exception as e:
        print("Market fetch error:", e)
        return []


# -----------------------------
# SIMPLE MOMENTUM STRATEGY
# -----------------------------
def run_strategy(coins):
    for coin in coins:
        symbol = coin["symbol"]
        change = coin["change"]

        # Buy strong positive momentum
        if change > 3 and symbol not in account["positions"] and account["cash"] > 5:
            size = account["cash"] * 0.2
            qty = size / coin["price"]

            account["positions"][symbol] = {
                "qty": qty,
                "entry": coin["price"]
            }

            account["cash"] -= size
            account["trades"] += 1

        # Sell if momentum fades
        if symbol in account["positions"]:
            entry = account["positions"][symbol]["entry"]
            qty = account["positions"][symbol]["qty"]
            pnl_percent = (coin["price"] - entry) / entry

            if pnl_percent > 0.05 or pnl_percent < -0.03:
                value = qty * coin["price"]
                account["cash"] += value
                account["trades"] += 1

                if pnl_percent > 0:
                    account["wins"] += 1
                else:
                    account["losses"] += 1

                del account["positions"][symbol]


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/")
def dashboard():
    coins = get_top_35_usdt()
    run_strategy(coins)

    positions_value = 0
    open_positions = []

    for symbol, pos in account["positions"].items():
        current = next((c for c in coins if c["symbol"] == symbol), None)
        if current:
            value = pos["qty"] * current["price"]
            pnl = value - (pos["qty"] * pos["entry"])
            positions_value += value

            open_positions.append({
                "symbol": symbol,
                "qty": round(pos["qty"], 4),
                "entry": round(pos["entry"], 4),
                "value": round(value, 2),
                "pnl": round(pnl, 2)
            })

    total_equity = account["cash"] + positions_value

    html = """
    <html>
    <head>
    <meta http-equiv="refresh" content="15">
    <style>
    body { background:#0b1220; color:white; font-family:Arial; padding:20px;}
    .card { background:#1e293b; padding:20px; border-radius:12px; margin-bottom:20px;}
    table { width:100%; border-collapse:collapse;}
    th, td { padding:8px; border-bottom:1px solid #334155;}
    th { text-align:left;}
    </style>
    </head>
    <body>

    <h2>🔥 ELITE AI TRADER v4 (LIVE MARKET)</h2>

    <div class="card">
    <h3>Account</h3>
    Cash: ${{cash}}<br>
    Positions Value: ${{positions}}<br>
    Total Equity: <b>${{equity}}</b>
    </div>

    <div class="card">
    <h3>Stats</h3>
    Trades: {{trades}}<br>
    Wins: {{wins}}<br>
    Losses: {{losses}}
    </div>

    <div class="card">
    <h3>Open Positions</h3>
    <table>
    <tr><th>Coin</th><th>Qty</th><th>Entry</th><th>Value</th><th>P/L</th></tr>
    {% for p in open_positions %}
    <tr>
    <td>{{p.symbol}}</td>
    <td>{{p.qty}}</td>
    <td>${{p.entry}}</td>
    <td>${{p.value}}</td>
    <td>${{p.pnl}}</td>
    </tr>
    {% endfor %}
    </table>
    </div>

    <div class="card">
    <h3>Top 35 USDT Pairs</h3>
    <table>
    <tr><th>Coin</th><th>Price</th><th>24h %</th></tr>
    {% for c in coins %}
    <tr>
    <td>{{c.symbol}}</td>
    <td>${{c.price}}</td>
    <td>{{c.change}}%</td>
    </tr>
    {% endfor %}
    </table>
    </div>

    </body>
    </html>
    """

    return render_template_string(html,
        cash=round(account["cash"],2),
        positions=round(positions_value,2),
        equity=round(total_equity,2),
        trades=account["trades"],
        wins=account["wins"],
        losses=account["losses"],
        open_positions=open_positions,
        coins=coins
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)