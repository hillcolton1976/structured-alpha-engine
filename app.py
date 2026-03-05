from flask import Flask, jsonify, render_template
import requests
import threading
import time

app = Flask(__name__)

# STARTING PORTFOLIO
cash = 50.0
doge = 0.0
entry_price = 0

wins = 0
losses = 0

price_history = []
equity_history = []
trade_history = []

def get_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT"
        r = requests.get(url).json()
        return float(r["price"])
    except:
        return 0


def trader():
    global cash, doge, entry_price, wins, losses

    while True:

        price = get_price()

        if price == 0:
            time.sleep(1)
            continue

        price_history.append(price)

        if len(price_history) > 50:
            price_history.pop(0)

        # DIP DETECTION
        if doge == 0 and len(price_history) > 10:

            avg = sum(price_history[-10:]) / 10

            if price < avg * 0.995:  # dip

                doge = cash / price
                entry_price = price
                cash = 0

                trade_history.append({
                    "type": "BUY",
                    "price": price
                })

        # SELL LOGIC
        if doge > 0:

            if price > entry_price * 1.01:

                cash = doge * price
                doge = 0

                wins += 1

                trade_history.append({
                    "type": "SELL",
                    "price": price
                })

            elif price < entry_price * 0.98:

                cash = doge * price
                doge = 0

                losses += 1

                trade_history.append({
                    "type": "STOP",
                    "price": price
                })

        equity = cash + doge * price
        equity_history.append(equity)

        if len(equity_history) > 100:
            equity_history.pop(0)

        time.sleep(1)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def data():

    price = get_price()

    equity = cash + doge * price

    return jsonify({
        "price": price,
        "cash": cash,
        "doge": doge,
        "equity": equity,
        "wins": wins,
        "losses": losses,
        "price_history": price_history,
        "equity_history": equity_history,
        "trades": trade_history[-10:]
    })


threading.Thread(target=trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)