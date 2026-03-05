from flask import Flask
import requests
import threading
import time
from collections import deque
import statistics
import random
import json

app = Flask(__name__)

# -------- SETTINGS --------

START_CASH = 50

cash = START_CASH
doge = 0
entry_price = 0

wins = 0
losses = 0

bot_level = 1
xp = 0
strategy = "dip"

trade_log = []

prices = deque(maxlen=300)
equity_history = deque(maxlen=300)

API = "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd"


# -------- GET PRICE --------

def get_price():

    try:
        r = requests.get(API, timeout=10)
        return r.json()["dogecoin"]["usd"]
    except:
        return None


# -------- RSI --------

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


# -------- DIP SIGNAL --------

def dip(price):

    if len(prices) < 30:
        return False

    short = statistics.mean(list(prices)[-10:])
    long = statistics.mean(list(prices)[-30:])

    return price < short*0.995 and price < long*0.997


# -------- PUMP SIGNAL --------

def pump(price):

    if len(prices) < 20:
        return False

    short = statistics.mean(list(prices)[-5:])
    mid = statistics.mean(list(prices)[-20:])

    return short > mid*1.002


# -------- ANALYZE --------

def analyze():

    if len(prices) < 40:
        return "hold"

    price = prices[-1]

    r = rsi()

    if strategy == "dip":

        if dip(price) and r < 45:
            return "buy"

    if strategy == "momentum":

        if pump(price):
            return "buy"

    if strategy == "scalp":

        if r < 40 and random.random() > 0.5:
            return "buy"

    return "hold"


# -------- LEARNING --------

def learn(win):

    global xp
    global bot_level
    global strategy

    if win:
        xp += 10
    else:
        xp += 4

    if xp > bot_level * 100:

        bot_level += 1
        xp = 0

        strategy = random.choice(["dip","momentum","scalp"])


# -------- TRADER --------

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

        doge_value = doge * price
        equity_history.append(cash + doge_value)

        signal = analyze()

        # BUY

        if signal == "buy" and cash > 5:

            amount = cash * 0.9
            qty = amount / price

            doge += qty
            cash -= amount
            entry_price = price

            trade_log.append(f"BUY {qty:.2f} DOGE @ ${price:.5f}")

        # SELL

        if doge > 0:

            profit = (price-entry_price)/entry_price*100

            target = 0.6 + bot_level*0.05
            stop = -1.8

            if profit > target or profit < stop or pump(price):

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

        time.sleep(10)


# -------- DASHBOARD --------

@app.route("/")

def dashboard():

    price = prices[-1] if prices else 0

    doge_value = doge * price

    equity = cash + doge_value

    pnl = ((equity-START_CASH)/START_CASH*100) if START_CASH else 0

    log = "<br>".join(trade_log[-15:][::-1])

    price_data = json.dumps(list(prices))
    equity_data = json.dumps(list(equity_history))

    return f"""

<html>

<head>

<meta http-equiv="refresh" content="8">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body {{
background:#0f172a;
color:white;
font-family:Arial;
padding:30px;
}}

h1 {{
color:#facc15;
}}

.card {{
background:#1e293b;
padding:20px;
margin:10px;
border-radius:10px;
}}

.grid {{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:10px;
}}

canvas {{
background:#111827;
padding:10px;
border-radius:10px;
}}

</style>

</head>

<body>

<h1>DOGE AI TRADER</h1>

<div class="grid">

<div class="card">
Price<br>
${price:.5f}
</div>

<div class="card">
Cash<br>
${cash:.2f}
</div>

<div class="card">
DOGE Held<br>
{doge:.2f}
</div>

<div class="card">
DOGE Value<br>
${doge_value:.2f}
</div>

<div class="card">
Equity<br>
${equity:.2f}
</div>

<div class="card">
P/L<br>
{pnl:.2f}%
</div>

<div class="card">
Wins<br>
{wins}
</div>

<div class="card">
Losses<br>
{losses}
</div>

<div class="card">
Level<br>
{bot_level}
</div>

</div>

<br>

<div class="card">

<h3>DOGE Price Chart</h3>

<canvas id="priceChart"></canvas>

</div>

<br>

<div class="card">

<h3>Portfolio Value</h3>

<canvas id="equityChart"></canvas>

</div>

<br>

<div class="card">

<h3>Trades</h3>

{log}

</div>

<script>

let priceData = {price_data}
let equityData = {equity_data}

new Chart(document.getElementById("priceChart"), {{
type: 'line',
data: {{
labels: priceData.map((_,i)=>i),
datasets:[{{
label:'DOGE Price',
data: priceData,
borderColor:'#22c55e',
fill:false
}}]
}}
}})

new Chart(document.getElementById("equityChart"), {{
type: 'line',
data: {{
labels: equityData.map((_,i)=>i),
datasets:[{{
label:'Portfolio Value',
data: equityData,
borderColor:'#facc15',
fill:false
}}]
}}
}})

</script>

</body>
</html>

"""


threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)