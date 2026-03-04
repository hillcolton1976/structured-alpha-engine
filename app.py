from flask import Flask
import requests
import time
import threading
from collections import deque

app = Flask(__name__)

# ===== BOT SETTINGS =====

START_CASH = 50
cash = START_CASH
doge = 0
entry_price = 0

wins = 0
losses = 0
trades = []

prices = deque(maxlen=120)

API = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"


# ===== GET LIVE PRICE =====

def get_price():
    try:
        r = requests.get(API, timeout=5)
        data = r.json()
        return float(data["dogecoin"]["usd"])
    except:
        return None


# ===== MARKET ANALYSIS =====

def market_state():

    if len(prices) < 60:
        return None

    short_avg = sum(list(prices)[-15:]) / 15
    long_avg = sum(prices) / len(prices)

    recent_low = min(list(prices)[-30:])
    recent_high = max(list(prices)[-30:])

    return short_avg, long_avg, recent_low, recent_high


# ===== TRADING AI =====

def trader():

    global cash, doge, entry_price, wins, losses

    while True:

        price = get_price()

        if not price:
            time.sleep(5)
            continue

        prices.append(price)

        state = market_state()

        if not state:
            time.sleep(5)
            continue

        short_avg, long_avg, low, high = state

        # BUY DIP
        if doge == 0 and price < short_avg * 0.985:

            buy_amount = cash * 0.95
            qty = buy_amount / price

            doge += qty
            cash -= buy_amount
            entry_price = price

            trades.append(f"BUY {qty:.2f} DOGE @ ${price}")

        # SELL TOP
        elif doge > 0:

            profit = (price - entry_price) / entry_price * 100

            if price > short_avg * 1.02 or profit > 2:

                value = doge * price

                if price > entry_price:
                    wins += 1
                else:
                    losses += 1

                cash += value
                trades.append(f"SELL {doge:.2f} DOGE @ ${price}")

                doge = 0

        time.sleep(6)


# ===== DASHBOARD =====

@app.route("/")
def dashboard():

    price = prices[-1] if prices else 0
    doge_value = doge * price
    equity = cash + doge_value

    history = "<br>".join(trades[-15:][::-1])

    return f"""
    <html>

    <head>
    <meta http-equiv="refresh" content="5">

    <style>

    body {{
    background:#0f172a;
    color:white;
    font-family:Arial;
    padding:30px;
    }}

    .card {{
    background:#1e293b;
    padding:20px;
    border-radius:10px;
    margin-bottom:20px;
    }}

    h1 {{
    color:#38bdf8;
    }}

    </style>

    </head>

    <body>

    <h1>DOGE AI DIP TRADER</h1>

    <div class="card">

    <h3>Market</h3>

    Price: ${price:.5f}

    </div>

    <div class="card">

    <h3>Portfolio</h3>

    Cash: ${cash:.2f} <br>
    DOGE: {doge:.2f} <br>
    DOGE Value: ${doge_value:.2f} <br>
    Total Equity: ${equity:.2f}

    </div>

    <div class="card">

    <h3>Performance</h3>

    Wins: {wins} <br>
    Losses: {losses}

    </div>

    <div class="card">

    <h3>Trade Log</h3>

    {history}

    </div>

    </body>

    </html>
    """


# ===== START BOT =====

threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)