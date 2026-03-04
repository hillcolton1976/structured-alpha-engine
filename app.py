from flask import Flask
import requests
import threading
import time
from collections import deque

app = Flask(__name__)

# ----- SETTINGS -----

START_CASH = 100
cash = START_CASH
doge = 0
entry_price = 0

wins = 0
losses = 0
trade_log = []

prices = deque(maxlen=100)

API = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"


# ----- PRICE FETCHER -----

def get_price():

    try:
        r = requests.get(API, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()

        return float(data["dogecoin"]["usd"])

    except:
        return None


# ----- RSI -----

def rsi(period=14):

    if len(prices) < period+1:
        return 50

    gains = []
    losses = []

    for i in range(-period, -1):

        change = prices[i+1] - prices[i]

        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))

    avg_gain = sum(gains)/period if gains else 0.0001
    avg_loss = sum(losses)/period if losses else 0.0001

    rs = avg_gain / avg_loss

    return 100 - (100/(1+rs))


# ----- ANALYSIS -----

def analyze():

    if len(prices) < 30:
        return None

    price = prices[-1]

    short_ma = sum(list(prices)[-10:]) / 10
    long_ma = sum(list(prices)[-30:]) / 30

    current_rsi = rsi()

    signal = "hold"

    # DIP BUY
    if price < short_ma * 0.99 and current_rsi < 40:
        signal = "buy"

    # TOP SELL
    if price > short_ma * 1.01 and current_rsi > 60:
        signal = "sell"

    return price, short_ma, long_ma, current_rsi, signal


# ----- TRADER LOOP -----

def trader():

    global cash, doge, entry_price, wins, losses

    while True:

        price = get_price()

        if not price:
            time.sleep(15)
            continue

        prices.append(price)

        data = analyze()

        if not data:
            time.sleep(15)
            continue

        price, short_ma, long_ma, current_rsi, signal = data

        # BUY
        if signal == "buy" and cash > 10:

            amount = cash * 0.5
            qty = amount / price

            doge += qty
            cash -= amount
            entry_price = price

            trade_log.append(f"BUY {qty:.2f} DOGE @ ${price}")

        # SELL
        elif doge > 0:

            profit = (price - entry_price) / entry_price * 100

            if signal == "sell" or profit > 2 or profit < -2:

                value = doge * price

                if price > entry_price:
                    wins += 1
                else:
                    losses += 1

                cash += value

                trade_log.append(
                    f"SELL {doge:.2f} DOGE @ ${price}  P/L {profit:.2f}%"
                )

                doge = 0

        time.sleep(20)


# ----- DASHBOARD -----

@app.route("/")
def dashboard():

    price = prices[-1] if prices else 0

    doge_value = doge * price
    equity = cash + doge_value

    log = "<br>".join(trade_log[-15:][::-1])

    return f"""

    <html>

    <head>

    <meta http-equiv="refresh" content="10">

    <style>

    body {{
        background:#0f172a;
        color:white;
        font-family:Arial;
        padding:40px;
    }}

    .card {{
        background:#1e293b;
        padding:20px;
        margin:10px;
        border-radius:10px;
    }}

    </style>

    </head>

    <body>

    <h1>DOGE AI TRADER</h1>

    <div class="card">
    <h2>Price: ${price:.5f}</h2>
    </div>

    <div class="card">
    Cash: ${cash:.2f}<br>
    DOGE Held: {doge:.2f}<br>
    DOGE Value: ${doge_value:.2f}<br>
    Equity: ${equity:.2f}
    </div>

    <div class="card">
    Wins: {wins}<br>
    Losses: {losses}
    </div>

    <div class="card">
    <h3>Trade Log</h3>
    {log}
    </div>

    </body>
    </html>

    """


# ----- START THREAD -----

threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)