from flask import Flask
import requests
import threading
import time
from collections import deque
import statistics
import random

app = Flask(__name__)

# ---------- START SETTINGS ----------

START_CASH = 50
cash = START_CASH
doge = 0
entry_price = 0

wins = 0
losses = 0

trade_log = []

prices = deque(maxlen=300)

bot_level = 1
xp = 0

strategy = "dip"

API = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"

# ---------- GET PRICE ----------

def get_price():

    try:
        r = requests.get(API, timeout=10)
        data = r.json()
        return float(data["dogecoin"]["usd"])
    except:
        return None


# ---------- RSI ----------

def rsi(period=14):

    if len(prices) < period+1:
        return 50

    gains = []
    losses = []

    for i in range(-period, -1):

        diff = prices[i+1] - prices[i]

        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains)/period if gains else 0.001
    avg_loss = sum(losses)/period if losses else 0.001

    rs = avg_gain / avg_loss

    return 100 - (100/(1+rs))


# ---------- MOMENTUM ----------

def momentum():

    if len(prices) < 20:
        return 0

    recent = list(prices)[-5:]
    older = list(prices)[-20:-15]

    return statistics.mean(recent) - statistics.mean(older)


# ---------- DIP DETECTION ----------

def dip_signal(price):

    short = statistics.mean(list(prices)[-10:])
    long = statistics.mean(list(prices)[-50:])

    if price < short * 0.995 and price < long * 0.997:
        return True

    return False


# ---------- PUMP DETECTION ----------

def pump_signal(price):

    short = statistics.mean(list(prices)[-5:])
    mid = statistics.mean(list(prices)[-20:])

    if short > mid * 1.002:
        return True

    return False


# ---------- ANALYSIS ----------

def analyze():

    if len(prices) < 60:
        return "hold"

    price = prices[-1]
    r = rsi()
    m = momentum()

    signal = "hold"

    # STRATEGY 1 — DIP BUY
    if strategy == "dip":

        if dip_signal(price) and r < 45:
            signal = "buy"

    # STRATEGY 2 — MOMENTUM
    if strategy == "momentum":

        if m > 0 and pump_signal(price):
            signal = "buy"

    # STRATEGY 3 — RANDOM SCALP
    if strategy == "scalp":

        if r < 40 and random.random() > 0.5:
            signal = "buy"

    return signal


# ---------- LEARNING ----------

def learn(win):

    global xp
    global bot_level
    global strategy

    if win:
        xp += 10
    else:
        xp += 3

    if xp > bot_level * 100:

        bot_level += 1
        xp = 0

        # switch strategy sometimes
        strategy = random.choice(["dip","momentum","scalp"])


# ---------- TRADER ----------

def trader():

    global cash
    global doge
    global entry_price
    global wins
    global losses

    while True:

        price = get_price()

        if not price:
            time.sleep(10)
            continue

        prices.append(price)

        signal = analyze()

        # ---------- BUY ----------

        if signal == "buy" and cash > 5:

            amount = cash * 0.9
            qty = amount / price

            doge += qty
            cash -= amount
            entry_price = price

            trade_log.append(f"BUY {qty:.2f} DOGE @ ${price:.5f}")

        # ---------- SELL ----------

        if doge > 0:

            profit = (price-entry_price)/entry_price*100

            target = 0.6 + bot_level*0.05

            stop = -1.8

            if profit > target or profit < stop or pump_signal(price):

                value = doge * price

                if price > entry_price:
                    wins += 1
                    learn(True)
                else:
                    losses += 1
                    learn(False)

                cash += value

                trade_log.append(
                    f"SELL {doge:.2f} DOGE @ ${price:.5f} | {profit:.2f}%"
                )

                doge = 0

        time.sleep(12)


# ---------- DASHBOARD ----------

@app.route("/")

def dashboard():

    price = prices[-1] if prices else 0

    doge_value = doge * price

    equity = cash + doge_value

    log = "<br>".join(trade_log[-20:][::-1])

    return f"""

    <html>

    <head>

    <meta http-equiv="refresh" content="8">

    <style>

    body {{
        background:#0f172a;
        color:white;
        font-family:Arial;
        padding:40px;
    }}

    h1 {{
        color:#facc15;
    }}

    .card {{
        background:#1e293b;
        padding:20px;
        margin:10px;
        border-radius:12px;
        box-shadow:0 0 10px #000;
    }}

    .profit {{
        color:#22c55e;
    }}

    .loss {{
        color:#ef4444;
    }}

    </style>

    </head>

    <body>

    <h1>DOGE AI v5</h1>

    <div class="card">
    Price: ${price:.5f}
    </div>

    <div class="card">

    Cash: ${cash:.2f}<br>
    DOGE: {doge:.2f}<br>
    DOGE Value: ${doge_value:.2f}<br>
    Equity: ${equity:.2f}

    </div>

    <div class="card">

    Wins: {wins}<br>
    Losses: {losses}<br>
    Level: {bot_level}<br>
    XP: {xp}<br>
    Strategy: {strategy}

    </div>

    <div class="card">

    <h3>Trades</h3>

    {log}

    </div>

    </body>
    </html>
    """


threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)