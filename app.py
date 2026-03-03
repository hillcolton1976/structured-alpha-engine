from flask import Flask, render_template_string
import threading
import requests
import time
from collections import deque

app = Flask(__name__)

START_BALANCE = 50.0
TRADE_SIZE_PERCENT = 0.25   # 25% of balance per trade
PRICE_REFRESH = 5
HISTORY = 20
MOMENTUM_THRESHOLD = 0.003  # 0.3%

COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "ripple",
    "dogecoin"
]

balance = START_BALANCE
positions = {}  # coin -> dict(type, entry, size)
price_history = {coin: deque(maxlen=HISTORY) for coin in COINS}
last_prices = {}

def fetch_prices():
    global last_prices
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={','.join(COINS)}&vs_currencies=usd"
        r = requests.get(url, timeout=10)
        data = r.json()
        for coin in COINS:
            if coin in data:
                price = data[coin]["usd"]
                last_prices[coin] = price
                price_history[coin].append(price)
    except:
        pass

def get_momentum(coin):
    hist = price_history[coin]
    if len(hist) < HISTORY:
        return 0
    return (hist[-1] - hist[0]) / hist[0]

def trade_engine():
    global balance

    while True:
        fetch_prices()

        for coin in COINS:
            if coin not in last_prices:
                continue

            price = last_prices[coin]
            momentum = get_momentum(coin)

            # ENTER LONG
            if momentum > MOMENTUM_THRESHOLD and coin not in positions:
                trade_size = balance * TRADE_SIZE_PERCENT
                if trade_size > 1:
                    positions[coin] = {
                        "type": "long",
                        "entry": price,
                        "size": trade_size
                    }
                    balance -= trade_size

            # ENTER SHORT
            elif momentum < -MOMENTUM_THRESHOLD and coin not in positions:
                trade_size = balance * TRADE_SIZE_PERCENT
                if trade_size > 1:
                    positions[coin] = {
                        "type": "short",
                        "entry": price,
                        "size": trade_size
                    }
                    balance -= trade_size

            # EXIT LONG
            if coin in positions and positions[coin]["type"] == "long":
                if momentum < 0:
                    entry = positions[coin]["entry"]
                    size = positions[coin]["size"]
                    pnl = size * ((price - entry) / entry)
                    balance += size + pnl
                    del positions[coin]

            # EXIT SHORT
            if coin in positions and positions[coin]["type"] == "short":
                if momentum > 0:
                    entry = positions[coin]["entry"]
                    size = positions[coin]["size"]
                    pnl = size * ((entry - price) / entry)
                    balance += size + pnl
                    del positions[coin]

        time.sleep(PRICE_REFRESH)

@app.route("/")
def home():
    return render_template_string("""
    <h1>Dual Momentum Bot</h1>
    <h2>Balance: ${{balance}}</h2>

    <h3>Open Positions</h3>
    <ul>
    {% for coin, pos in positions.items() %}
        <li>{{coin}} - {{pos.type}} @ ${{pos.entry}}</li>
    {% endfor %}
    </ul>

    <h3>Live Prices</h3>
    <ul>
    {% for coin, price in prices.items() %}
        <li>{{coin}} : ${{price}}</li>
    {% endfor %}
    </ul>
    """, balance=round(balance,2), positions=positions, prices=last_prices)

if __name__ == "__main__":
    threading.Thread(target=trade_engine, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)