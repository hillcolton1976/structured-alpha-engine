from flask import Flask
import requests
import time
import random

app = Flask(__name__)

STARTING_CASH = 50
REFRESH_SECONDS = 15
API_COOLDOWN = 60
BOT_COUNT = 20

last_market = []
last_fetch = 0
api_status = "OK"
last_evolution = time.time()

# ================= MARKET =================

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
                "change": float(coin.get("price_change_percentage_24h") or 0),
            })

        last_market = market
        last_fetch = time.time()
        api_status = "OK"
        return market

    except:
        api_status = "ERROR"
        return last_market

# ================= STRATEGY =================

class Strategy:
    def __init__(self, id, mode):
        self.id = id
        self.mode = mode
        self.cash = STARTING_CASH
        self.portfolio = {}
        self.entry_price = {}
        self.entry_time = {}
        self.wins = 0
        self.losses = 0
        self.equity = STARTING_CASH

        if mode == "Aggressive":
            self.tp = 0.3
            self.sl = -0.4
            self.size = 0.6
            self.hold = 60
        else:  # Momentum
            self.tp = 0.8
            self.sl = -0.6
            self.size = 0.5
            self.hold = 120

        # Mutation
        self.tp += random.uniform(-0.1, 0.1)
        self.sl += random.uniform(-0.1, 0.1)
        self.size += random.uniform(-0.1, 0.1)
        self.hold += random.randint(-20, 20)

        self.tp = max(0.1, min(self.tp, 1.5))
        self.sl = max(-1.5, min(self.sl, -0.1))
        self.size = max(0.2, min(self.size, 0.8))
        self.hold = max(30, min(self.hold, 300))

    def trade(self, market):
        if not market:
            return

        now = time.time()

        # SELL LOGIC
        for symbol in list(self.portfolio.keys()):
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if not coin:
                continue

            entry = self.entry_price[symbol]
            price = coin["price"]
            qty = self.portfolio[symbol]

            pnl = ((price - entry) / entry) * 100

            if pnl >= self.tp or pnl <= self.sl or now - self.entry_time[symbol] > self.hold:
                self.cash += qty * price
                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

                del self.portfolio[symbol]
                del self.entry_price[symbol]
                del self.entry_time[symbol]

        # BUY LOGIC
        if len(self.portfolio) < 2:
            coin = random.choice(market)
            invest = self.cash * self.size

            if invest > 5:
                qty = invest / coin["price"]
                self.cash -= invest
                self.portfolio[coin["symbol"]] = qty
                self.entry_price[coin["symbol"]] = coin["price"]
                self.entry_time[coin["symbol"]] = now

        # UPDATE EQUITY
        total = self.cash
        for symbol, qty in self.portfolio.items():
            coin = next((c for c in market if c["symbol"] == symbol), None)
            if coin:
                total += qty * coin["price"]

        self.equity = round(total, 2)

# ================= CREATE BOTS =================

strategies = []

for i in range(BOT_COUNT):
    mode = "Aggressive" if i < BOT_COUNT//2 else "Momentum"
    strategies.append(Strategy(i+1, mode))

# ================= EVOLUTION =================

def evolve():
    global strategies, last_evolution

    if time.time() - last_evolution < 300:
        return

    ranked = sorted(strategies, key=lambda x: x.equity, reverse=True)

    survivors = ranked[:int(len(ranked)*0.7)]
    elites = ranked[:int(len(ranked)*0.3)]

    new_gen = survivors.copy()

    for _ in range(len(strategies) - len(survivors)):
        parent = random.choice(elites)
        child = Strategy(parent.id, parent.mode)

        child.tp = parent.tp + random.uniform(-0.1, 0.1)
        child.sl = parent.sl + random.uniform(-0.1, 0.1)
        child.size = parent.size + random.uniform(-0.1, 0.1)
        child.hold = parent.hold + random.randint(-20, 20)

        new_gen.append(child)

    strategies = new_gen
    last_evolution = time.time()

# ================= DASHBOARD =================

@app.route("/")
def dashboard():
    market = get_market()

    for s in strategies:
        s.trade(market)

    evolve()

    total_equity = round(sum(s.equity for s in strategies), 2)
    total_wins = sum(s.wins for s in strategies)
    total_losses = sum(s.losses for s in strategies)

    html = f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
        <style>
            body {{
                background-color: #0e0e0e;
                color: white;
                font-family: Arial;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            th, td {{
                padding: 8px;
                text-align: center;
            }}
            tr:nth-child(even) {{ background-color: #1c1c1c; }}
            .green {{ color: #00ff88; }}
            .red {{ color: #ff4d4d; }}
        </style>
    </head>
    <body>
        <h1>Crypto Strategy Arena</h1>
        <h3>API Status: {api_status}</h3>
        <h3>Total Equity: <span class="green">${total_equity}</span> |
            Wins: {total_wins} |
            Losses: {total_losses}
        </h3>

        <table>
            <tr>
                <th>ID</th>
                <th>Mode</th>
                <th>Equity</th>
                <th>Wins</th>
                <th>Losses</th>
                <th>TP%</th>
                <th>SL%</th>
                <th>Size</th>
            </tr>
    """

    for s in strategies:
        color = "green" if s.equity >= STARTING_CASH else "red"
        html += f"""
        <tr>
            <td>{s.id}</td>
            <td>{s.mode}</td>
            <td class="{color}">${s.equity}</td>
            <td>{s.wins}</td>
            <td>{s.losses}</td>
            <td>{round(s.tp,2)}</td>
            <td>{round(s.sl,2)}</td>
            <td>{round(s.size,2)}</td>
        </tr>
        """

    html += "</table></body></html>"
    return html

# ================= RUN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)