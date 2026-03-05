from flask import Flask, jsonify, render_template_string
import requests
import threading
import time
from collections import deque

app = Flask(__name__)

# ---- STARTING SETTINGS ----

START_BALANCE = 50.0
balance = START_BALANCE
doge = 0.0
entry_price = None

price = 0

prices = deque(maxlen=120)
equity_history = deque(maxlen=300)
trade_history = []

# ---- FETCH DOGE PRICE ----

def get_price():
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT",
            timeout=5
        )
        return float(r.json()["price"])
    except:
        return None

# ---- TRADING BOT ----

def trader():
    global balance, doge, entry_price, price

    while True:

        p = get_price()
        if p is None:
            time.sleep(2)
            continue

        price = p
        prices.append(p)

        if len(prices) > 20:

            short = sum(list(prices)[-5:]) / 5
            long = sum(list(prices)[-20:]) / 20

            # BUY DIP
            if doge == 0 and short < long * 0.995:

                doge = balance / price
                entry_price = price
                balance = 0

                trade_history.append({
                    "type": "BUY",
                    "price": price
                })

            # SELL TOP
            elif doge > 0 and price > entry_price * 1.01:

                balance = doge * price
                doge = 0
                entry_price = None

                trade_history.append({
                    "type": "SELL",
                    "price": price
                })

        equity = balance + doge * price
        equity_history.append(equity)

        time.sleep(2)

# ---- START BACKGROUND BOT ----

threading.Thread(target=trader, daemon=True).start()

# ---- DASHBOARD PAGE ----

@app.route("/")
def home():

    return render_template_string("""

<!DOCTYPE html>
<html>
<head>

<title>DOGE Auto Trader</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>

body{
background:#0f172a;
color:white;
font-family:Arial;
text-align:center;
}

.card{
background:#1e293b;
padding:20px;
margin:10px;
border-radius:12px;
display:inline-block;
width:200px;
}

canvas{
background:white;
border-radius:10px;
margin-top:20px;
}

</style>

</head>

<body>

<h1>DOGE Auto Trader</h1>

<div class="card">
<h3>Price</h3>
<div id="price">0</div>
</div>

<div class="card">
<h3>Balance</h3>
<div id="balance">0</div>
</div>

<div class="card">
<h3>DOGE</h3>
<div id="doge">0</div>
</div>

<div class="card">
<h3>Equity</h3>
<div id="equity">0</div>
</div>

<br><br>

<canvas id="priceChart" width="600" height="200"></canvas>
<br>
<canvas id="equityChart" width="600" height="200"></canvas>

<script>

let priceData=[]
let equityData=[]
let labels=[]

const priceChart = new Chart(
document.getElementById('priceChart'),
{
type:'line',
data:{
labels:labels,
datasets:[{
label:'DOGE Price',
data:priceData,
borderWidth:2
}]
}
})

const equityChart = new Chart(
document.getElementById('equityChart'),
{
type:'line',
data:{
labels:labels,
datasets:[{
label:'Equity',
data:equityData,
borderWidth:2
}]
}
})

async function update(){

let r = await fetch("/data")
let d = await r.json()

document.getElementById("price").innerText=d.price
document.getElementById("balance").innerText=d.balance.toFixed(2)
document.getElementById("doge").innerText=d.doge.toFixed(2)
document.getElementById("equity").innerText=d.equity.toFixed(2)

labels.push("")
priceData.push(d.price)
equityData.push(d.equity)

if(labels.length>50){
labels.shift()
priceData.shift()
equityData.shift()
}

priceChart.update()
equityChart.update()

}

setInterval(update,2000)

</script>

</body>
</html>

""")

# ---- DATA API ----

@app.route("/data")
def data():

    equity = balance + doge * price

    return jsonify(
        price=price,
        balance=balance,
        doge=doge,
        equity=equity
    )

# ---- RUN SERVER ----

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)