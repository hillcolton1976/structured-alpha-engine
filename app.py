import requests
from flask import Flask

app = Flask(__name__)

# -------------------------------
# SAFE BINANCE FETCH
# -------------------------------

def get_top_pairs():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print("Binance API error:", response.status_code)
            return []

        data = response.json()

        # Make sure we received a list
        if not isinstance(data, list):
            print("Unexpected Binance response:", data)
            return []

        usdt_pairs = [
            x for x in data
            if isinstance(x, dict)
            and "symbol" in x
            and x["symbol"].endswith("USDT")
        ]

        usdt_pairs.sort(
            key=lambda x: float(x.get("quoteVolume", 0)),
            reverse=True
        )

        return [x["symbol"] for x in usdt_pairs[:35]]

    except Exception as e:
        print("Error getting top pairs:", e)
        return []


# -------------------------------
# DASHBOARD ROUTE
# -------------------------------

@app.route("/")
def dashboard():

    # Example account stats (replace with your real ones if needed)
    cash = 1000
    total_positions_value = 2500
    total_equity = cash + total_positions_value
    trades = 12
    wins = 7
    losses = 5
    entry_threshold = 2.5

    coins = get_top_pairs()

    # IMPORTANT:
    # Double braces {{ }} are required in CSS when using .format()
    html = """
    <html>
    <head>
        <title>Trading Engine</title>
        <style>
            body {{
                background: #0f172a;
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
        </style>
    </head>
    <body>

        <h1>🚀 Trading Engine Dashboard</h1>

        <div class="card">
            <h2>Account</h2>
            <p>Cash: ${}</p>
            <p>Positions Value: ${}</p>
            <p>Total Equity: ${}</p>
        </div>

        <div class="card">
            <h2>Stats</h2>
            <p>Trades: {}</p>
            <p>Wins: {}</p>
            <p>Losses: {}</p>
            <p>Entry Threshold: {}%</p>
        </div>

        <div class="card">
            <h2>Top USDT Pairs</h2>
            <ul>
                {}
            </ul>
        </div>

    </body>
    </html>
    """.format(
        cash,
        total_positions_value,
        total_equity,
        trades,
        wins,
        losses,
        entry_threshold,
        "".join(f"<li>{coin}</li>" for coin in coins)
    )

    return html


# -------------------------------
# RUN (for local testing)
# -------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)