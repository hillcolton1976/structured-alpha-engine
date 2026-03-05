import requests
import time
import threading
from collections import deque
from flask import Flask, render_template_string

app = Flask(__name__)

# Starting balance
cash = 50.0
doge = 0.0
entry_price = None

price_history = deque(maxlen=120)
equity_history = deque(maxlen=120)
trade_log = []

DOGE_PRICE = 0

# -----------------------
# GET LIVE DOGE PRICE
# -----------------------

def get_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT"
        r = requests.get(url, timeout=5)
        data = r.json()
        return float(data["price"])
    except:
        return None


# -----------------------
# BOT STRATEGY
# -----------------------

def bot():
    global cash, doge, entry_price, DOGE_PRICE

    while True:

        price = get_price()

        if price is None:
            time.sleep(2)
            continue

        DOGE_PRICE = price
        price_history.append(price)

        equity = cash + doge * price
        equity_history.append(equity)

        if len(price_history) < 20:
            time.sleep(2)
            continue

        avg = sum(price_history)/len(price_history)
        dip = avg * 0.992
        scalp = avg * 1.006

        # BUY DIP
        if price < dip and cash > 5:
            amount = cash / price
            doge += amount
            entry_price = price
            cash = 0

            trade_log.append(
                f"BUY {amount:.2f} DOGE @ {price:.4f}"
            )

        # SELL SCALP
        elif doge > 0 and price > scalp:
            cash += doge * price

            trade_log.append(
                f"SELL {doge:.2f} DOGE @ {price:.4f}"
            )

            doge = 0
            entry_price = None

        time.sleep(2)


threading.Thread(target=bot, daemon=True).start()

# -----------------------
# UI
# -----------------------

HTML = """
<html>
<head>

<title>DOGE Auto Trader</title>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<meta http-equiv="refresh" content="2">

<style>

body{
background:#0f172a;
color:white;
font-family:Arial;
padding:20px;
}

.card{
background:#1e293b;
padding:20px;
border-radius:10px;
margin-bottom:20px;
}

h1{
color:#38bdf8;
}

</style>

</head>

<body>

<h1>DOGE Auto Trader</h1>

<div class="card">

<h2>Market</h2>

DOGE Price: ${{price}}

</div>

<div class="card">

<h2>Portfolio</h2>

Cash: ${{cash}}

<br><br>

DOGE Held: {{doge}}

<br><br>

Equity: ${{equity}}

</div>

<div class="card">

<h2>Trade Log</h2>

{% for t in trades %}
{{t}}<br>
{% endfor %}

</div>

<div class="card">

<h2>Equity Chart</h2>

<canvas id="chart"></canvas>

</div>


<script>

var ctx = document.getElementById('chart').getContext('2d');

new Chart(ctx,{
type:'line',
data:{
labels: {{labels}},
datasets:[{
label:'Equity',
data: {{equity}},
}]
}
});

</script>

</body>

</html>
"""

# -----------------------
# PAGE
# -----------------------

@app.route("/")
def home():

    price = DOGE_PRICE
    equity = cash + doge * price

    return render_template_string(
        HTML,
        price=round(price,5),
        cash=round(cash,2),
        doge=round(doge,2),
        equity=round(equity,2),
        trades=list(trade_log)[-10:],
        labels=list(range(len(equity_history))),
        equity=list(equity_history)
    )


if __name__ == "__main__":
    app.run(debug=True)