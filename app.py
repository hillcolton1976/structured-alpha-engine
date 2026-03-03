import requests
import threading
import time
from flask import Flask, render_template

app = Flask(__name__)

SYMBOL = "BTCUSDT"
BINANCE_URL = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"

UP_THRESHOLD = 1.5     # +1.5%
DOWN_THRESHOLD = -0.5  # -0.5%

STARTING_CASH = 50

last_reference_price = None


# =========================
# BOT CLASS
# =========================
class TradingBot:
    def __init__(self, name):
        self.name = name
        self.cash = STARTING_CASH
        self.coins = 0.0
        self.trades = 0
        self.starting_cash = STARTING_CASH

    def total_value(self, price):
        if price is None:
            return self.cash
        return self.cash + (self.coins * price)

    def profit(self, price):
        return self.total_value(price) - self.starting_cash

    def trade(self, price_change_percent, current_price):
        if current_price is None:
            return

        position_size = self.cash * 0.2

        # BUY on +1.5%
        if price_change_percent >= UP_THRESHOLD and self.cash > 1:
            coins_bought = position_size / current_price
            self.cash -= position_size
            self.coins += coins_bought
            self.trades += 1

        # SELL 50% on -0.5%
        elif price_change_percent <= DOWN_THRESHOLD and self.coins > 0:
            coins_to_sell = self.coins * 0.5
            self.cash += coins_to_sell * current_price
            self.coins -= coins_to_sell
            self.trades += 1


# =========================
# CREATE BOTS
# =========================
bots = [
    TradingBot("Scalper"),
    TradingBot("Momentum"),
    TradingBot("Mean Reversion"),
    TradingBot("Breakout"),
]


# =========================
# SAFE PRICE FETCH
# =========================
def get_price():
    try:
        r = requests.get(BINANCE_URL, timeout=5)
        data = r.json()
        return float(data["price"])
    except:
        return None


# =========================
# TRADING LOOP
# =========================
def run_trading():
    global last_reference_price

    while True:
        try:
            price = get_price()

            if price:
                if last_reference_price is None:
                    last_reference_price = price

                change = ((price - last_reference_price) / last_reference_price) * 100

                if change >= UP_THRESHOLD or change <= DOWN_THRESHOLD:
                    for bot in bots:
                        bot.trade(change, price)

                    last_reference_price = price

        except:
            pass  # prevents crash

        time.sleep(5)


trading_thread = threading.Thread(target=run_trading, daemon=True)
trading_thread.start()


# =========================
# DASHBOARD ROUTE
# =========================
@app.route("/")
def dashboard():
    price = get_price()

    if price is None:
        price = 0

    total_equity = sum(bot.total_value(price) for bot in bots)

    return render_template(
        "dashboard.html",
        bots=bots,
        current_price=price,
        total_equity=round(total_equity, 2),
        symbol=SYMBOL
    )


# =========================
# REQUIRED FOR RAILWAY
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)