from flask import Flask
import requests
import random
import time

app = Flask(__name__)

# ---------------- CONFIG ----------------
STARTING_CASH = 50
STRATEGY_COUNT = 30
MAX_POSITIONS = 7
REFRESH_SECONDS = 15

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
        self.aggression = random.uniform(1.5, 3.0)
        self.equity = STARTING_CASH

    def trade(self, market):

        now = time.time()

        # ----- SELL FAST (SCALP) -----
        for symbol in list(self.portfolio.keys()):
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if not coin:
                continue

            qty = self.portfolio[symbol]
            entry_price = self.entry[symbol]
            current_price = coin["price"]

            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            hold_time = now - self.entry_time[symbol]

            # ultra tight scalp exits
            take_profit = 1.5
            stop_loss = -1.5

            # also force exit after 3 minutes
            if pnl_percent >= take_profit or pnl_percent <= stop_loss or hold_time > 180:

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

        # ----- BUY AGGRESSIVELY -----
        for coin in market[:15]:

            if len(self.portfolio) >= MAX_POSITIONS:
                break

            if coin["symbol"] not in self.portfolio:

                # lower threshold massively
                if coin["change"] > -1:

                    invest_percent = 0.35 * self.aggression
                    invest_amount = self.cash * invest_percent

                    if invest_amount > 5:
                        qty = invest_amount / coin["price"]
                        self.portfolio[coin["symbol"]] = qty
                        self.entry[coin["symbol"]] = coin["price"]
                        self.entry_time[coin["symbol"]] = now
                        self.cash -= invest_amount

    def update_equity(self, market):
        total_positions = 0
        for symbol, qty in self.portfolio.items():
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if coin:
                total_positions += qty * coin["price"]

        self.equity = self.cash + total_positions

# ---------------- MARKET ----------------
def get_market():
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
        data = r.json()

        market = []
        for coin in data:
            market.append({
                "symbol": coin["symbol"].upper(),
                "price": float(coin["current_price"]),
                "change": float(coin["price_change_percentage_24h"] or 0),
            })

        return market

    except:
        return []

# ---------------- INIT ----------------
strategies = [Strategy(i+1) for i in range(STRATEGY_COUNT)]

# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():

    market = get_market()
    if not market:
        return "Market loading..."

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

    <h1>⚡ ULTRA SCALP ARENA ⚡</h1>

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

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)