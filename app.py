from flask import Flask, jsonify, render_template
import requests
import threading
import time
from collections import deque
import statistics

app = Flask(__name__)

# ===== PORTFOLIO =====

START_BALANCE = 50

cash = START_BALANCE
doge = 0
entry_price = 0

wins = 0
losses = 0
level = 1

# ===== DATA =====

prices = deque(maxlen=200)
equity_history = deque(maxlen=200)
trade_log = []

# ===== PRICE API =====

def get_price():

    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT",
            timeout=5
        )

        data = r.json()
        return float(data["price"])

    except:
        return None


# ===== RSI =====

def calculate_rsi():

    if len(prices) < 15:
        return 50

    gains = []
    losses_list = []

    for i in range(1, 15):

        diff = prices[-i] - prices[-i-1]

        if diff > 0:
            gains.append(diff)
        else:
            losses_list.append(abs(diff))

    avg_gain = sum(gains) / 14 if gains else 0.00001
    avg_loss = sum(losses_list) / 14 if losses_list else 0.00001

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


# ===== TRADER =====

def trader():

    global cash
    global doge
    global entry_price
    global wins
    global losses
    global level

    while True:

        price = get_price()

        if not price:
            time.sleep(5)
            continue

        prices.append(price)

        rsi = calculate_rsi()

        doge_value = doge * price
        equity = cash + doge_value

        equity_history.append(equity)

        # ===== BUY =====

        if doge == 0 and len(prices) > 30:

            recent_high = max(list(prices)[-30:])
            dip = (recent_high - price) / recent_high * 100

            momentum = prices[-1] > prices[-3]

            if rsi < 35 and dip > 0.4 and momentum:

                amount = cash * 0.95
                qty = amount / price

                doge += qty
                cash -= amount
                entry_price = price

                trade_log.insert(0,
                    f"BUY {qty:.2f} DOGE @ ${price:.5f}"
                )

        # ===== SELL =====

        if doge > 0:

            profit = (price - entry_price) / entry_price * 100

            if profit > 0.6 or rsi > 65:

                value = doge * price
                cash += value
                doge = 0

                wins += 1

                trade_log.insert(0,
                    f"SELL @ ${price:.5f} | +{profit:.2f}%"
                )

            elif profit < -1.5:

                value = doge * price
                cash += value
                doge = 0

                losses += 1

                trade_log.insert(0,
                    f"STOP LOSS @ ${price:.5f} | {profit:.2f}%"
                )

        # ===== LEVEL SYSTEM =====

        if equity > START_BALANCE * (1 + level * 0.05):
            level += 1

        time.sleep(5)


# ===== API =====

@app.route("/data")
def data():

    price = prices[-1] if prices else 0
    doge_value = doge * price
    equity = cash + doge_value

    return jsonify({

        "price": price,
        "cash": round(cash,2),
        "doge": round(doge,2),
        "doge_value": round(doge_value,2),
        "equity": round(equity,2),
        "wins": wins,
        "losses": losses,
        "level": level,
        "prices": list(prices),
        "equity_history": list(equity_history),
        "trades": trade_log[:15]

    })


# ===== DASHBOARD =====

@app.route("/")
def home():
    return render_template("index.html")


# ===== BACKGROUND BOT =====

threading.Thread(target=trader, daemon=True).start()


# ===== START SERVER =====

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)