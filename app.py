from flask import Flask, render_template_string
import requests
import threading
import time

app = Flask(__name__)

START_BALANCE = 50.0
MAX_POSITIONS = 5
REFRESH_SECONDS = 5

# CoinGecko IDs mapped to symbols
COINS = {
    "bitcoin":"BTCUSDT",
    "ethereum":"ETHUSDT",
    "binancecoin":"BNBUSDT",
    "solana":"SOLUSDT",
    "ripple":"XRPUSDT",
    "cardano":"ADAUSDT",
    "dogecoin":"DOGEUSDT",
    "avalanche-2":"AVAXUSDT",
    "chainlink":"LINKUSDT",
    "matic-network":"MATICUSDT",
    "tron":"TRXUSDT",
    "polkadot":"DOTUSDT",
    "litecoin":"LTCUSDT",
    "bitcoin-cash":"BCHUSDT",
    "cosmos":"ATOMUSDT",
    "near":"NEARUSDT",
    "uniswap":"UNIUSDT",
    "aptos":"APTUSDT",
    "arbitrum":"ARBUSDT",
    "optimism":"OPUSDT",
    "injective-protocol":"INJUSDT",
    "immutable-x":"IMXUSDT",
    "render-token":"RNDRUSDT",
    "fetch-ai":"FETUSDT",
    "gala":"GALAUSDT",
    "sui":"SUIUSDT",
    "sei-network":"SEIUSDT",
    "tia":"TIAUSDT",
    "pyth-network":"PYTHUSDT",
    "ordi":"ORDIUSDT",
    "aave":"AAVEUSDT",
    "internet-computer":"ICPUSDT",
    "filecoin":"FILUSDT",
    "ethereum-classic":"ETCUSDT",
    "stellar":"XLMUSDT"
}

cash = START_BALANCE
positions = {}
history = {v: [] for v in COINS.values()}

trades = 0
wins = 0
losses = 0

entry_threshold = 0.004
tp_percent = 0.012
sl_percent = 0.008

# ======================
# PRICE FETCH (CoinGecko Batch)
# ======================

def get_prices():
    try:
        ids = ",".join(COINS.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        data = r.json()

        prices = {}
        for cg_id, symbol in COINS.items():
            if cg_id in data:
                prices[symbol] = data[cg_id]["usd"]
        return prices

    except Exception as e:
        print("Price fetch error:", e)
        return {}

# ======================
# SCORING
# ======================

def calculate_scores(prices):
    scores = {}
    for symbol, price in prices.items():

        history[symbol].append(price)
        if len(history[symbol]) > 50:
            history[symbol].pop(0)

        if len(history[symbol]) >= 10:
            base = history[symbol][-10]
            if base != 0:
                change = (price - base) / base
                scores[symbol] = round(change, 5)
            else:
                scores[symbol] = 0
        else:
            scores[symbol] = 0

    return scores

# ======================
# TRADER
# ======================

def trader():
    global cash, trades, wins, losses
    global entry_threshold, tp_percent, sl_percent

    while True:
        prices = get_prices()
        scores = calculate_scores(prices)

        # SELL
        for symbol in list(positions.keys()):
            if symbol not in prices:
                continue

            price = prices[symbol]
            entry = positions[symbol]["entry"]
            qty = positions[symbol]["qty"]

            change = (price - entry) / entry

            if change >= tp_percent or change <= -sl_percent:
                value = qty * price
                pnl = value - (qty * entry)

                cash += value
                trades += 1

                if pnl > 0:
                    wins += 1
                else:
                    losses += 1

                del positions[symbol]

                # Adaptive Learning
                if trades > 5:
                    winrate = wins / trades
                    if winrate < 0.4:
                        entry_threshold *= 1.05
                    elif winrate > 0.6:
                        entry_threshold *= 0.97

        # BUY
        if len(positions) < MAX_POSITIONS:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

            for symbol, score in sorted_scores:
                if symbol in positions:
                    continue

                if score > entry_threshold and cash > 5:
                    price = prices[symbol]
                    invest = cash / (MAX_POSITIONS - len(positions))
                    qty = invest / price

                    positions[symbol] = {"qty": qty, "entry": price}
                    cash -= invest
                    break

        time.sleep(REFRESH_SECONDS)

threading.Thread(target=trader, daemon=True).start()

# ======================
# DASHBOARD
# ======================

@app.route("/")
def dashboard():
    prices = get_prices()
    scores = calculate_scores(prices)

    total_positions_value = 0
    pos_rows = ""

    for s, data in positions.items():
        if s in prices:
            price = prices[s]
            value = data["qty"] * price
            pnl = value - (data["qty"] * data["entry"])
            total_positions_value += value

            pos_rows += f"<tr><td>{s}</td><td>{data['qty']:.4f}</td><td>${data['entry']:.4f}</td><td>${price:.4f}</td><td>${pnl:.2f}</td></tr>"

    total_equity = cash + total_positions_value
    winrate = round((wins/trades)*100,2) if trades>0 else 0

    rows = ""
    for s, price in prices.items():
        score = scores.get(s,0)
        rows += f"<tr><td>{s}</td><td>${price:.6f}</td><td>{score:.5f}</td></tr>"

    return render_template_string(f"""
    <html>
    <head>
        <meta http-equiv="refresh" content="{REFRESH_SECONDS}">
        <style>
            body {{
                background: linear-gradient(to bottom right,#0f2027,#203a43,#2c5364);
                color:white;
                font-family:Arial;
                padding:20px;
            }}
            table{{width:100%;border-collapse:collapse;margin-bottom:20px;}}
            th,td{{padding:8px;text-align:left;}}
            th{{color:#6dd5fa;}}
            tr:nth-child(even){{background:rgba(255,255,255,0.05);}}
            .card{{background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;margin-bottom:20px;}}
        </style>
    </head>
    <body>
        <h1>🔥 ELITE TOP-35 ADAPTIVE AI</h1>

        <div class="card">
            Cash: ${cash:.2f}<br>
            Positions Value: ${total_positions_value:.2f}<br>
            Total Equity: ${total_equity:.2f}<br><br>
            Trades: {trades} | Wins: {wins} | Losses: {losses} | Win Rate: {winrate}%
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            <table>
                <tr><th>Coin</th><th>Qty</th><th>Entry</th><th>Current</th><th>P/L</th></tr>
                {pos_rows if pos_rows else "<tr><td colspan=5>None</td></tr>"}
            </table>
        </div>

        <div class="card">
            <h2>Live Market Scores</h2>
            <table>
                <tr><th>Coin</th><th>Price</th><th>Score</th></tr>
                {rows}
            </table>
        </div>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run()