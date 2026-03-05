from flask import Flask, jsonify, render_template
import requests
import threading
import time
from collections import deque

app = Flask(__name__)

# ===== PORTFOLIO =====

cash = 50.0
doge = 0.0
entry_price = 0

wins = 0
losses = 0

# ===== DATA STORAGE =====

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

# ===== TRADER =====

def trader():

    global cash
    global doge
    global entry_price
    global wins
    global losses

    while True:

        price = get_price()

        if not price:
            time.sleep(5)
            continue

        prices.append(price)

        doge_value = doge * price
        equity_history.append(cash + doge_value)

        # ===== BUY DIP =====

        if doge == 0 and len(prices) > 20:

            recent_high = max(list(prices)[-20:])
            dip = (recent_high - price) / recent_high * 100

            if dip > 0.35:

                amount = cash * 0.9
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

            # scalp profit
            if profit > 0.35:

                value = doge * price
                cash += value
                wins += 1

                trade_log.insert(0,
                    f"SELL {doge:.2f} DOGE @ ${price:.5f} | +{profit:.2f}%"
                )

                doge = 0

            # stop loss
            elif profit < -1.2:

                value = doge * price
                cash += value
                losses += 1

                trade_log.insert(0,
                    f"STOP LOSS {doge:.2f} DOGE @ ${price:.5f} | {profit:.2f}%"
                )

                doge = 0

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
        "prices": list(prices),
        "equity_history": list(equity_history),
        "trades": trade_log[:10]

    })

# ===== DASHBOARD =====

@app.route("/")
def home():
    return render_template("index.html")

# ===== START BOT =====

threading.Thread(target=trader, daemon=True).start()

# ===== RUN =====

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)