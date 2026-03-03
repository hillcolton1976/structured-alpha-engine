from flask import Flask
import requests
import random
import time

app = Flask(__name__)

# ---------------- CONFIG ----------------
STARTING_CASH = 50
STRATEGY_COUNT = 30
MAX_POSITIONS = 7
REFRESH_SECONDS = 20

# ---------------- STRATEGY CLASS ----------------
class Strategy:
    def __init__(self, id):
        self.id = id
        self.cash = STARTING_CASH
        self.portfolio = {}
        self.entry = {}
        self.wins = 0
        self.losses = 0
        self.aggression = random.uniform(1.2, 2.5)
        self.confidence = random.uniform(1.0, 2.0)
        self.xp = 0
        self.level = 1
        self.equity = STARTING_CASH

    def score(self, change):
        volatility_boost = abs(change) * 0.5
        randomness = random.uniform(-2, 2)
        intelligence = self.level * 0.6
        return (change * self.aggression) + volatility_boost + intelligence + randomness

    def mutate(self):
        # random mutation over time
        if random.random() < 0.15:
            self.aggression += random.uniform(-0.2, 0.3)
            self.aggression = max(0.8, min(3.5, self.aggression))

    def trade(self, market):

        self.mutate()

        # SELL FAST
        for symbol in list(self.portfolio.keys()):
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if not coin:
                continue

            qty = self.portfolio[symbol]
            entry_price = self.entry[symbol]
            current_price = coin["price"]

            pnl_percent = ((current_price - entry_price) / entry_price) * 100

            take_profit = 4 * self.aggression
            stop_loss = -4 * self.aggression

            if pnl_percent >= take_profit or pnl_percent <= stop_loss:
                value = qty * current_price
                pnl = value - (qty * entry_price)

                self.cash += value

                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

                del self.portfolio[symbol]
                del self.entry[symbol]
                self.xp += 1

        # BUY HARD
        for coin in market[:20]:

            if len(self.portfolio) >= MAX_POSITIONS:
                break

            if coin["symbol"] not in self.portfolio:
                score = self.score(coin["change"])

                if score > (2.5 * self.confidence):

                    invest_percent = 0.30 * self.aggression
                    invest_amount = self.cash * invest_percent

                    if invest_amount > 5:
                        qty = invest_amount / coin["price"]
                        self.portfolio[coin["symbol"]] = qty
                        self.entry[coin["symbol"]] = coin["price"]
                        self.cash -= invest_amount
                        self.xp += 1

        if self.xp >= self.level * 4:
            self.xp = 0
            self.level += 1

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
        background:#020617;
        color:white;
        font-family:Arial;
        padding:25px;
    }}
    h1 {{ color:#ef4444; }}
    table {{
        width:100%;
        border-collapse:collapse;
    }}
    th, td {{
        padding:8px;
        border-bottom:1px solid #334155;
    }}
    .gold {{ color:gold; }}
    </style>
    </head>
    <body>

    <h1>🔥 ULTRA AGGRESSIVE AI ARENA</h1>

    <h2 class="gold">🏆 Best Strategy: #{best.id}</h2>
    <h3>Equity: ${round(best.equity,2)}</h3>
    <h3>Wins: {best.wins} | Losses: {best.losses}</h3>
    <h3>Level: {best.level}</h3>
    <h3>Aggression: {round(best.aggression,2)}</h3>

    <h2>All Strategies</h2>
    <table>
    <tr>
        <th>ID</th>
        <th>Equity</th>
        <th>Wins</th>
        <th>Losses</th>
        <th>Level</th>
        <th>Aggression</th>
    </tr>
    """

    for strat in ranked:
        html += f"""
        <tr>
            <td>{strat.id}</td>
            <td>${round(strat.equity,2)}</td>
            <td>{strat.wins}</td>
            <td>{strat.losses}</td>
            <td>{strat.level}</td>
            <td>{round(strat.aggression,2)}</td>
        </tr>
        """

    html += "</table></body></html>"

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)