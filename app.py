import requests
from flask import Flask

app = Flask(__name__)

# -------------------------
# SIM START (RESET)
# -------------------------

cash = 50.00
positions = {}   # symbol: {"qty": float, "entry": float}
trades = 0
wins = 0
losses = 0
entry_threshold = 0.002


# -------------------------
# SAFE BINANCE FETCH
# -------------------------

def get_top_pairs():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            raise Exception("Bad status")

        data = r.json()

        if not isinstance(data, list):
            raise Exception("Unexpected format")

        usdt = [x for x in data if x["symbol"].endswith("USDT")]

        usdt.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)

        return usdt[:35]

    except Exception as e:
        print("Binance fetch failed:", e)
        return []


# -------------------------
# DASHBOARD
# -------------------------

@app.route("/")
def dashboard():

    global cash, positions

    pairs = get_top_pairs()

    total_positions_value = 0

    rows = ""
    for p in pairs:
        symbol = p["symbol"]
        price = float(p.get("lastPrice", 0))
        score = price * 0.00001

        rows += f"""
        <tr>
            <td>{symbol}</td>
            <td>${price:,.4f}</td>
            <td>{score:.6f}</td>
        </tr>
        """

    total_equity = cash + total_positions_value

    return f"""
    <html>
    <head>
        <title>Trading Engine</title>
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

        <h1>🚀 Trading Engine Dashboard</h1>

        <div class="card">
            <h2>Account</h2>
            <p>Cash: ${cash:.2f}</p>
            <p>Positions Value: ${total_positions_value:.2f}</p>
            <p><b>Total Equity: ${total_equity:.2f}</b></p>
        </div>

        <div class="card">
            <h2>Stats</h2>
            <p>Trades: {trades}</p>
            <p>Wins: {wins}</p>
            <p>Losses: {losses}</p>
            <p>Entry Threshold: {entry_threshold}</p>
        </div>

        <div class="card">
            <h2>Top 35 USDT Coins</h2>
            <table>
                <tr>
                    <th>Coin</th>
                    <th>Price</th>
                    <th>Score</th>
                </tr>
                {rows}
            </table>
        </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)