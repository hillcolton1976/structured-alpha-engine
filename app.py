from flask import Flask
import requests
import random
import time

app = Flask(__name__)

# ---------------- CONFIG ----------------
STARTING_CASH = 50
STRATEGY_COUNT = 25
MAX_POSITIONS = 5
REFRESH_SECONDS = 20
API_COOLDOWN = 60

# ---------------- MARKET CACHE ----------------
last_market = []
last_fetch = 0
api_status = "OK"

def get_market():
    global last_market, last_fetch, api_status

    # Only call API once per minute
    if time.time() - last_fetch < API_COOLDOWN and last_market:
        return last_market

    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "volume_desc",
            "per_page": 35,
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
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


# ---------------- STRATEGY ----------------
class Strategy:
    def __init__(self, id):
        self.id = id
        self.cash = STARTING_CASH
        self.portfolio = {}
        self.entry = {}
        self.entry_time = {}
        self.wins = 0
        self.losses = 0
        self.equity = STARTING_CASH

    def trade(self, market):
        now = time.time()

        # SELL FAST
        for symbol in list(self.portfolio.keys()):
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if not coin:
                continue

            qty = self.portfolio[symbol]
            entry_price = self.entry[symbol]
            current_price = coin["price"]

            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            hold_time = now - self.entry_time[symbol]

            if pnl_percent >= 1 or pnl_percent <= -1 or hold_time > 120:
                value = qty * current_price
                pnl = value - (qty * entry_price)

                self.cash += value

                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

                del self.portfolio[symbol]
                del self.entry[symbol]
                del self.entry_time[symbol]

        # BUY CONSTANTLY
        for coin in market[:10]:
            if len(self.portfolio) >= MAX_POSITIONS:
                break

            if coin["symbol"] not in self.portfolio:
                if coin["change"] > -2:

                    invest = self.cash * 0.40
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


# ---------------- INIT ----------------
strategies = [Strategy(i+1) for i in range(STRATEGY_COUNT)]


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():

    market = get_market()

    # Always run even if API fails (uses cache)
    for strat in strategies:
        strat.trade(market)
        strat.update_equity(market)

    ranked = sorted(strategies, key=lambda x: x.equity, reverse=True)
    best = ranked[0]

    html = f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
    <style>
    body {{
        background:#000;
        color:#0f0;
        font-family:monospace;
        padding:20px;
    }}
    table {{
        width:100%;
        border-collapse:collapse;
    }}
    th, td {{
        padding:6px;
        border-bottom:1px solid #222;
    }}
    </style>
    </head>
    <body>

    <h1>⚡ STABLE SCALP ARENA ⚡</h1>
    <h3>API Status: {api_status}</h3>

    <h2>🏆 Best Strategy #{best.id}</h2>
    <h3>Equity: ${round(best.equity,2)}</h3>
    <h3>Wins: {best.wins} | Losses: {best.losses}</h3>

    <h2>All Strategies</h2>
    <table>
    <tr>
        <th>ID</th>
        <th>Equity</th>
        <th>Wins</th>
        <th>Losses</th>
        <th>Open Positions</th>
    </tr>
    """

    for strat in ranked:
        html += f"""
        <tr>
            <td>{strat.id}</td>
            <td>${round(strat.equity,2)}</td>
            <td>{strat.wins}</td>
            <td>{strat.losses}</td>
            <td>{len(strat.portfolio)}</td>
        </tr>
        """

    html += "</table></body></html>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)