from flask import Flask
import requests
import time
import random

app = Flask(__name__)

STARTING_CASH = 50
REFRESH_SECONDS = 15
API_COOLDOWN = 60
STRATEGY_COUNT = 25

last_market = []
last_fetch = 0
api_status = "OK"


def get_market():
    global last_market, last_fetch, api_status

    if time.time() - last_fetch < API_COOLDOWN and last_market:
        return last_market

    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 40,
            "page": 1,
            "sparkline": False,
        }

        r = requests.get(url, params=params, timeout=10)

        if r.status_code != 200:
            api_status = "RATE LIMITED"
            return last_market

        data = r.json()

        market = []
        for coin in data:
            market.append({
                "symbol": coin["symbol"].upper(),
                "price": float(coin["current_price"]),
                "change": float(coin["price_change_percentage_24h"] or 0),
            })

        last_market = market
        last_fetch = time.time()
        api_status = "OK"
        return market

    except:
        api_status = "ERROR"
        return last_market


class Strategy:
    def __init__(self, id, mode):
        self.id = id
        self.mode = mode
        self.cash = STARTING_CASH
        self.portfolio = {}
        self.entry = {}
        self.entry_time = {}
        self.wins = 0
        self.losses = 0
        self.equity = STARTING_CASH

        if mode == "Aggressive":
            self.tp = 0.6
            self.sl = -0.6
            self.size = 0.5
            self.hold = 90

        elif mode == "Balanced":
            self.tp = 1.0
            self.sl = -1.0
            self.size = 0.35
            self.hold = 150

        else:  # Momentum
            self.tp = 1.2
            self.sl = -0.8
            self.size = 0.4
            self.hold = 180

    def trade(self, market):
        now = time.time()

        for symbol in list(self.portfolio.keys()):
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if not coin:
                continue

            entry_price = self.entry[symbol]
            current_price = coin["price"]
            qty = self.portfolio[symbol]

            pnl = ((current_price - entry_price) / entry_price) * 100
            hold_time = now - self.entry_time[symbol]

            if pnl >= self.tp or pnl <= self.sl or hold_time > self.hold:
                value = qty * current_price
                self.cash += value

                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

                del self.portfolio[symbol]
                del self.entry[symbol]
                del self.entry_time[symbol]

        if len(self.portfolio) < 3:
            coin = random.choice(market[:15])

            if self.mode == "Momentum" and coin["change"] < 0:
                return

            invest = self.cash * self.size
            if invest > 5:
                qty = invest / coin["price"]
                self.portfolio[coin["symbol"]] = qty
                self.entry[coin["symbol"]] = coin["price"]
                self.entry_time[coin["symbol"]] = now
                self.cash -= invest

    def update_equity(self, market):
        total = 0
        for symbol, qty in self.portfolio.items():
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if coin:
                total += qty * coin["price"]
        self.equity = self.cash + total


modes = ["Aggressive"] * 8 + ["Balanced"] * 8 + ["Momentum"] * 9
strategies = [Strategy(i + 1, modes[i]) for i in range(STRATEGY_COUNT)]


@app.route("/")
def dashboard():
    market = get_market()

    for strat in strategies:
        strat.trade(market)
        strat.update_equity(market)

    ranked = sorted(strategies, key=lambda x: x.equity, reverse=True)

    html = f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
    <style>
    body {{
        background: linear-gradient(135deg,#0f0f0f,#1a1a1a);
        color: white;
        font-family: Arial;
        padding: 30px;
    }}
    table {{
        width:100%;
        border-collapse:collapse;
    }}
    th, td {{
        padding:10px;
        text-align:center;
    }}
    th {{
        background:#222;
    }}
    tr:nth-child(even) {{
        background:#181818;
    }}
    .profit {{ color:#00ff88; }}
    .loss {{ color:#ff4444; }}
    </style>
    </head>
    <body>

    <h1>⚡ Crypto Strategy Arena ⚡</h1>
    <h3>API Status: {api_status}</h3>

    <table>
    <tr>
        <th>ID</th>
        <th>Mode</th>
        <th>Equity</th>
        <th>Wins</th>
        <th>Losses</th>
        <th>Open</th>
    </tr>
    """

    for strat in ranked:
        pnl_class = "profit" if strat.equity >= STARTING_CASH else "loss"

        html += f"""
        <tr>
            <td>{strat.id}</td>
            <td>{strat.mode}</td>
            <td class="{pnl_class}">${round(strat.equity,2)}</td>
            <td>{strat.wins}</td>
            <td>{strat.losses}</td>
            <td>{len(strat.portfolio)}</td>
        </tr>
        """

    html += "</table></body></html>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)