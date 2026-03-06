import time
import threading
import requests
import numpy as np

from flask import Flask, jsonify, request, render_template_string
from collections import deque
import config

app = Flask(__name__)

# --- Paper Trading State ---
usd_balance = 1000.0
coins = {c:0.0 for c in config.COINS}
entry_prices = {c:None for c in config.COINS}

wins = {c:0 for c in config.COINS}
losses = {c:0 for c in config.COINS}
trades = {c:0 for c in config.COINS}

price_history = {c:deque(maxlen=500) for c in config.COINS}
equity_history = deque(maxlen=500)

bot_running = True

# Kraken public price fetch
def get_kraken_price(symbol):
    pair = config.PAIR_MAP[symbol]
    try:
        r = requests.get(f"https://api.kraken.com/0/public/Ticker?pair={pair}",timeout=5)
        data = r.json()
        price = list(data["result"].values())[0]["c"][0]
        return float(price)
    except:
        return None

# RSI
def compute_rsi(prices, period=config.RSI_PERIOD):
    if len(prices) < period+1:
        return None
    deltas = np.diff(prices)
    ups = deltas[deltas>0]
    downs = -deltas[deltas<0]

    avg_up = np.mean(ups) if len(ups)>0 else 0
    avg_down = np.mean(downs) if len(downs)>0 else 0
    if avg_down == 0:
        return 100
    rs = avg_up/avg_down
    return 100 - (100/(1+rs))

# EMA
def ema(prices, period):
    if len(prices) < period:
        return None
    return float(np.mean(prices[-period:]))

def trading_bot():
    global usd_balance, coins, entry_prices
    while bot_running:
        total_equity = usd_balance
        for sym in config.COINS:
            price = get_kraken_price(sym)
            if price:
                price_history[sym].append(price)
                total_equity += coins[sym]*price

                # Indicators
                rsi_val = compute_rsi(list(price_history[sym]))
                ema50 = ema(list(price_history[sym]),config.EMA_SHORT)
                ema200 = ema(list(price_history[sym]),config.EMA_LONG)

                # Buy rules
                if coins[sym] == 0 and rsi_val and ema50 and ema200:
                    if rsi_val < 30 and ema50 > ema200:
                        amount = usd_balance * config.BUY_PERCENT
                        coins[sym] += amount/price
                        usd_balance -= amount
                        entry_prices[sym] = price
                        trades[sym]+=1

                # Sell rules
                elif coins[sym] > 0:
                    entry = entry_prices[sym]
                    if price >= entry*config.PROFIT_TARGET:
                        usd_balance += coins[sym]*price
                        wins[sym]+=1
                        coins[sym]=0
                        entry_prices[sym]=None
                    elif price <= entry*config.STOP_LOSS:
                        usd_balance += coins[sym]*price
                        losses[sym]+=1
                        coins[sym]=0
                        entry_prices[sym]=None

        equity_history.append(total_equity)
        time.sleep(1)

threading.Thread(target=trading_bot,daemon=True).start()

# Flask routes
@app.route("/data")
def data():
    return jsonify(
        usd=usd_balance,
        coins=coins,
        wins=wins,
        losses=losses,
        trades=trades,
        prices={s:list(price_history[s]) for s in config.COINS},
        equity=list(equity_history),
    )

@app.route("/deposit",methods=["POST"])
def deposit():
    global usd_balance
    amount = float(request.json.get("amount",0))
    usd_balance += amount
    return jsonify(success=True,usd=usd_balance)

@app.route("/sell_all",methods=["POST"])
def sell_all():
    global usd_balance, coins
    for s in coins:
        p = get_kraken_price(s)
        if p and coins[s]>0:
            usd_balance += coins[s]*p
            coins[s]=0
    return jsonify(success=True,usd=usd_balance)

@app.route("/")
def index():
    return render_template_string("""
<html>
<head><title>Multi-Crypto Paper Bot</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{background:#0f172a;color:white;font-family:Arial;text-align:center;}
button{padding:10px;margin:5px;border-radius:5px;}
</style>
</head>
<body>
<h1>Multi-Crypto Paper Trading Bot</h1>
<button onclick="deposit()">Deposit $500</button>
<button onclick="sell()">Sell All</button>
<div>USD: <span id="usd"></span></div>
<div>Equity: <span id="eq"></span></div>
<canvas id="equityChart"></canvas>

<script>
async function update(){
  let r=await fetch('/data'); let d=await r.json();
  document.getElementById("usd").innerText=d.usd.toFixed(2);
  document.getElementById("eq").innerText=d.equity.slice(-1)[0]?.toFixed(2);

  eqChart.data.datasets[0].data=d.equity;
  eqChart.update();
}
setInterval(update,1000);

async function deposit(){
  await fetch('/deposit',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({amount:500})
  });
}
async function sell(){
  await fetch('/sell_all',{method:'POST'});
}

let eqChart=new Chart(document.getElementById("equityChart"),{
  type:'line',
  data:{labels:[],datasets:[{label:"Equity",data:[]}]},
  options:{animation:false,responsive:true}
});
</script>

</body>
</html>
""")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080)