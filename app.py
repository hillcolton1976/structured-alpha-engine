from flask import Flask, jsonify, render_template
import requests
import threading
import time

app = Flask(__name__)

# STARTING PORTFOLIO
cash = 50.0
doge = 0.0
equity = 50.0

wins = 0
losses = 0

last_buy_price = 0

price_history = []
equity_history = []
trade_history = []

running = True


# GET DOGE PRICE
def get_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd",
            timeout=5
        )
        data = r.json()
        return float(data["dogecoin"]["usd"])
    except:
        return None


# TRADING BRAIN
def trader():

    global cash, doge, equity, last_buy_price, wins, losses

    while running:

        price = get_price()

        if price:

            price_history.append(price)

            if len(price_history) > 60:
                price_history.pop(0)

            equity = cash + doge * price
            equity_history.append(equity)

            if len(equity_history) > 60:
                equity_history.pop(0)

            if len(price_history) > 10:

                avg = sum(price_history[-10:]) / 10

                dip = price < avg * 0.995
                peak = price > avg * 1.005

                # BUY DIP
                if dip and cash > 5:

                    buy_amount = cash * 0.5
                    doge_bought = buy_amount / price

                    doge += doge_bought
                    cash -= buy_amount

                    last_buy_price = price

                    trade_history.append({
                        "type": "BUY",
                        "price": price,
                        "amount": doge_bought
                    })

                # SELL PEAK
                if peak and doge > 0:

                    sell_amount = doge * 0.5
                    cash += sell_amount * price
                    doge -= sell_amount

                    if price > last_buy_price:
                        wins += 1
                    else:
                        losses += 1

                    trade_history.append({
                        "type": "SELL",
                        "price": price,
                        "amount": sell_amount
                    })

        time.sleep(10)


# START TRADER THREAD
threading.Thread(target=trader, daemon=True).start()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/data")
def data():

    price = get_price()

    return jsonify({

        "price": price,
        "cash": round(cash, 2),
        "doge": round(doge, 2),
        "equity": round(cash + doge * price if price else cash, 2),
        "wins": wins,
        "losses": losses,
        "prices": price_history,
        "equity_history": equity_history,
        "trades": trade_history[-10:]

    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)