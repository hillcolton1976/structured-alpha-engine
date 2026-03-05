from flask import Flask, jsonify, render_template
import requests
import threading
import time
from collections import deque

app = Flask(__name__)

START_BALANCE = 50

cash = START_BALANCE
doge = 0
entry_price = 0

wins = 0
losses = 0

prices = deque(maxlen=120)
equity_history = deque(maxlen=120)
trade_log = []


def get_price():

    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT",
            timeout=5
        )

        return float(r.json()["price"])

    except:
        return None


def trader():

    global cash, doge, entry_price, wins, losses

    while True:

        price = get_price()

        if price is None:
            time.sleep(5)
            continue

        prices.append(price)

        doge_value = doge * price
        equity = cash + doge_value

        equity_history.append(equity)

        # BUY DIP
        if doge == 0 and len(prices) > 20:

            recent_high = max(list(prices)[-20:])
            dip = (recent_high - price) / recent_high * 100

            if dip > 0.4:

                buy_amount = cash * 0.95
                qty = buy_amount / price

                doge += qty
                cash -= buy_amount
                entry_price = price

                trade_log.insert(0, f"BUY {qty:.2f} DOGE @ {price:.5f}")

        # SELL
        if doge > 0:

            profit = (price - entry_price) / entry_price * 100

            if profit > 0.6:

                value = doge * price
                cash += value
                doge = 0
                wins += 1

                trade_log.insert(0, f"SELL +{profit:.2f}%")

            elif profit < -1.5:

                value = doge * price
                cash += value
                doge = 0
                losses += 1

                trade_log.insert(0, f"STOP LOSS")

        time.sleep(5)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def data():

    price = prices[-1] if prices else 0

    doge_value = doge * price
    equity = cash + doge_value

    return jsonify({
        "price": price,
        "cash": cash,
        "doge": doge,
        "equity": equity,
        "wins": wins,
        "losses": losses,
        "prices": list(prices),
        "equity_history": list(equity_history),
        "trades": trade_log[:10]
    })


threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)