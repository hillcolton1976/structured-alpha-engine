from flask import Flask
import requests
import threading
import time
from collections import deque
import statistics

app = Flask(__name__)

# ---------- SETTINGS ----------

START_CASH = 50
cash = START_CASH
doge = 0
entry_price = 0

wins = 0
losses = 0

trade_log = []

prices = deque(maxlen=200)
volume_score = 1.0
momentum_score = 1.0

API = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"

# ---------- PRICE FETCH ----------

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


# ---------- ANALYSIS ----------

def analyze():

    if len(prices) < 50:
        return "hold"

    price = prices[-1]

    short = statistics.mean(list(prices)[-10:])
    mid = statistics.mean(list(prices)[-30:])
    long = statistics.mean(list(prices)[-50:])

    r = rsi()

    m = momentum()

    signal = "hold"

    # BUY DIP
    if price < short * 0.995 and r < 42:
        signal = "buy"

    # MOMENTUM BREAKOUT
    if m > 0.0005 and price > short and short > mid:
        signal = "buy"

    # SELL TOP
    if r > 62 and price > short * 1.003:
        signal = "sell"

    return signal


# ---------- LEARNING ----------

def learn(win):

    global momentum_score

    if win:
        momentum_score *= 1.02
    else:
        momentum_score *= 0.98


# ---------- TRADER ----------

def trader():

    global cash, doge, entry_price, wins, losses

    while True:

        price = get_price()

        if not price:
            time.sleep(10)
            continue

        prices.append(price)

        signal = analyze()

        # BUY
        if signal == "buy" and cash > 5:

            amount = cash * 0.8
            qty = amount / price

            doge += qty
            cash -= amount
            entry_price = price

            trade_log.append(f"BUY {qty:.2f} DOGE @ ${price}")

        # SELL
        if doge > 0:

            profit = (price - entry_price) / entry_price * 100

            if signal == "sell" or profit > 1.2 or profit < -2:

                value = doge * price

                if price > entry_price:
                    wins += 1
                    learn(True)
                else:
                    losses += 1
                    learn(False)

                cash += value

                trade_log.append(
                    f"SELL {doge:.2f} DOGE @ ${price} | {profit:.2f}%"
                )

                doge = 0

        time.sleep(15)


# ---------- DASHBOARD ----------

@app.route("/")
def dashboard():

    price = prices[-1] if prices else 0
    doge_value = doge * price
    equity = cash + doge_value

    log = "<br>".join(trade_log[-15:][::-1])

    return f"""

    <html>

    <head>

    <meta http-equiv="refresh" content="8">

    <style>

    body {{
        background:#0b0f1a;
        color:white;
        font-family:Arial;
        padding:40px;
    }}

    h1 {{
        color:#facc15;
    }}

    .card {{
        background:#1a1f2e;
        padding:20px;
        margin:10px;
        border-radius:10px;
        box-shadow:0 0 10px #000;
    }}

    </style>

    </head>

    <body>

    <h1>DOGE AI SCALPER</h1>

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
    Losses: {losses}
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