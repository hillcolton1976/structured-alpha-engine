from flask import Flask, jsonify, render_template_string
import requests
import threading
import time
from collections import deque

app = Flask(__name__)

# Portfolio
usd_balance = 50.0
doge_balance = 0.0
entry_price = None

# Stats
wins = 0
losses = 0
trades = 0

# Data history
price_history = deque(maxlen=200)
equity_history = deque(maxlen=200)

bot_running = True


# Get DOGE price
def get_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd",
            timeout=5,
        )
        return float(r.json()["dogecoin"]["usd"])
    except:
        return None


# Trading Bot
def trading_bot():
    global usd_balance, doge_balance, entry_price
    global wins, losses, trades

    while bot_running:

        price = get_price()

        if price:
            price_history.append(price)

            equity = usd_balance + doge_balance * price
            equity_history.append(equity)

            if len(price_history) > 20:

                avg = sum(price_history) / len(price_history)

                # BUY DIP
                if doge_balance == 0 and price < avg * 0.997:

                    amount = usd_balance * 0.95
                    doge_balance = amount / price
                    usd_balance -= amount
                    entry_price = price
                    trades += 1

                # SELL SCALP
                elif doge_balance > 0:

                    if price > entry_price * 1.003:

                        usd_balance += doge_balance * price

                        if price > entry_price:
                            wins += 1
                        else:
                            losses += 1

                        doge_balance = 0
                        entry_price = None

        time.sleep(1)


# Start bot thread
threading.Thread(target=trading_bot, daemon=True).start()


@app.route("/data")
def data():

    price = price_history[-1] if price_history else 0

    return jsonify(
        price=price,
        usd=usd_balance,
        doge=doge_balance,
        wins=wins,
        losses=losses,
        trades=trades,
        prices=list(price_history),
        equity=list(equity_history),
    )


@app.route("/")
def dashboard():

    return render_template_string(
        """
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
border-radius:10px;
display:inline-block;
min-width:150px;
}

canvas{
background:#111827;
margin-top:20px;
}

</style>

</head>

<body>

<h1>DOGE Auto Trader</h1>

<div class="card">Price<br><span id="price">0</span></div>
<div class="card">USD<br><span id="usd">0</span></div>
<div class="card">DOGE<br><span id="doge">0</span></div>
<div class="card">Trades<br><span id="trades">0</span></div>
<div class="card">Wins<br><span id="wins">0</span></div>
<div class="card">Losses<br><span id="losses">0</span></div>

<h2>Price Chart</h2>
<canvas id="priceChart"></canvas>

<h2>Equity Chart</h2>
<canvas id="equityChart"></canvas>

<script>

let priceChart = new Chart(document.getElementById('priceChart'),{
type:'line',
data:{labels:[],datasets:[{label:'DOGE Price',data:[]}]}
})

let equityChart = new Chart(document.getElementById('equityChart'),{
type:'line',
data:{labels:[],datasets:[{label:'Equity',data:[]}]}
})

async function update(){

let r = await fetch('/data')
let d = await r.json()

document.getElementById("price").innerText = d.price
document.getElementById("usd").innerText = d.usd.toFixed(2)
document.getElementById("doge").innerText = d.doge.toFixed(2)
document.getElementById("wins").innerText = d.wins
document.getElementById("losses").innerText = d.losses
document.getElementById("trades").innerText = d.trades

priceChart.data.labels = d.prices.map((_,i)=>i)
priceChart.data.datasets[0].data = d.prices
priceChart.update()

equityChart.data.labels = d.equity.map((_,i)=>i)
equityChart.data.datasets[0].data = d.equity
equityChart.update()

}

setInterval(update,1000)

</script>

</body>
</html>
"""
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)