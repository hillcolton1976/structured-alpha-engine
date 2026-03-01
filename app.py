import requests
from flask import Flask

app = Flask(__name__)

# =========================
# ELITE AI TRADER v3.1
# =========================

STARTING_CASH = 50.0
cash = STARTING_CASH
positions = {}  # symbol: {"qty": float, "entry": float}
trades = 0
wins = 0
losses = 0

entry_threshold = 0.002
position_size_pct = 0.20


# =========================
# SAFE BINANCE FETCH
# =========================

def get_top_pairs():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return []

        data = r.json()

        if not isinstance(data, list):
            return []

        usdt = [x for x in data if x["symbol"].endswith("USDT")]
        usdt.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)

        return usdt[:35]  # 35 coins

    except:
        return []


# =========================
# ADAPTIVE STRATEGY
# =========================

def adapt_strategy():
    global entry_threshold, wins, losses

    total = wins + losses
    if total < 5:
        return

    winrate = wins / total

    if winrate > 0.6:
        entry_threshold *= 0.95
    elif winrate < 0.4:
        entry_threshold *= 1.05

    entry_threshold = max(0.0005, min(entry_threshold, 0.01))


# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    global cash, positions, trades, wins, losses

    pairs = get_top_pairs()

    rows = ""
    total_positions_value = 0

    # Live trading logic
    for p in pairs:
        symbol = p["symbol"]
        price = float(p["lastPrice"])
        change = float(p["priceChangePercent"]) / 100

        score = change

        # ENTRY
        if score > entry_threshold and symbol not in positions and cash > 5:
            allocation = cash * position_size_pct
            qty = allocation / price
            positions[symbol] = {"qty": qty, "entry": price}
            cash -= allocation
            trades += 1

        # EXIT
        if symbol in positions:
            entry_price = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]

            if price >= entry_price * 1.02:
                cash += qty * price
                del positions[symbol]
                wins += 1

            elif price <= entry_price * 0.98:
                cash += qty * price
                del positions[symbol]
                losses += 1

        rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${price:,.4f}</td>
            <td>{change*100:.2f}%</td>
        </tr>
        """

    # Build positions table with $ value
    position_rows = ""
    total_unrealized = 0

    for symbol, data in positions.items():
        price = next((float(x["lastPrice"]) for x in pairs if x["symbol"] == symbol), data["entry"])
        qty = data["qty"]
        entry = data["entry"]

        value = qty * price
        pnl = value - (qty * entry)

        total_positions_value += value
        total_unrealized += pnl

        color = "#22c55e" if pnl >= 0 else "#ef4444"

        position_rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>{qty:.6f}</td>
            <td>${entry:.4f}</td>
            <td>${value:.2f}</td>
            <td style='color:{color}'>${pnl:.2f}</td>
        </tr>
        """

    if not positions:
        position_rows = "<tr><td colspan='5'>No open positions</td></tr>"

    total_equity = cash + total_positions_value

    adapt_strategy()

    return f"""
    <html>
    <head>
        <title>ELITE AI TRADER v3.1</title>
        <style>
            body {{
                background-color: #0f172a;
                color: white;
                font-family: Arial;
                padding: 30px;
            }}
            .card {{
                background: #1e293b;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            td, th {{
                padding: 8px;
                border-bottom: 1px solid #334155;
            }}
            th {{
                text-align: left;
            }}
        </style>
    </head>
    <body>

        <h1>🔥 ELITE AI TRADER v3.1</h1>

        <div class="card">
            <h2>Account</h2>
            <p>Cash: ${cash:.2f}</p>
            <p>Positions Value: ${total_positions_value:.2f}</p>
            <p><b>Total Equity: ${total_equity:.2f}</b></p>
            <p>Unrealized P/L: ${total_unrealized:.2f}</p>
        </div>

        <div class="card">
            <h2>Stats</h2>
            <p>Trades: {trades}</p>
            <p>Wins: {wins}</p>
            <p>Losses: {losses}</p>
            <p>Adaptive Threshold: {entry_threshold:.4f}</p>
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Qty</th>
                    <th>Entry</th>
                    <th>Value ($)</th>
                    <th>P/L</th>
                </tr>
                {position_rows}
            </table>
        </div>

        <div class="card">
            <h2>Top 35 USDT Pairs</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Price</th>
                    <th>24h %</th>
                </tr>
                {rows}
            </table>
        </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)