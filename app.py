import requests
import threading
import time
from flask import Flask, render_template

app = Flask(__name__)

SYMBOL = "BTCUSDT"
BINANCE_URL = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"

UP_THRESHOLD = 1.5
DOWN_THRESHOLD = -0.5

last_reference_price = None


# =========================
# BOT CLASS
# =========================
class TradingBot:
    def __init__(self, strategy, starting_cash=50):
        self.strategy = strategy
        self.cash = starting_cash
        self.coins = 0.0

        self.pnl = 0
        self.trades = 0
        self.wins = 0
        self.losses = 0

        self.memory = []
        self.aggression = 1.0

    def portfolio_value(self, current_price):
        return self.cash + (self.coins * current_price)

    def trade(self, price_change_percent, current_price):

        position_size = self.cash * 0.2

        # BUY on upward move
        if price_change_percent >= UP_THRESHOLD:
            if self.cash > 1:
                coins_bought = position_size / current_price
                self.cash -= position_size
                self.coins += coins_bought
                self.trades += 1

        # SELL on downward move
        elif price_change_percent <= DOWN_THRESHOLD:
            if self.coins > 0:
                coins_to_sell = self.coins * 0.5
                sale_value = coins_to_sell * current_price
                self.cash += sale_value
                self.coins -= coins_to_sell
                self.trades += 1

        # Calculate PnL
        total_value = self.portfolio_value(current_price)
        self.pnl = total_value - 50  # based on starting 50

        if self.pnl > 0:
            self.wins += 1
        else:
            self.losses += 1


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
# GET LIVE PRICE
# =========================
def get_price():
    try:
        response = requests.get(BINANCE_URL, timeout=5)
        data = response.json()
        return float(data["price"])
    except:
        return None


# =========================
# TRADING LOOP
# =========================
def run_trading():
    global last_reference_price

    while True:
        price = get_price()

        if price:
            if last_reference_price is None:
                last_reference_price = price

            price_change = ((price - last_reference_price) / last_reference_price) * 100

            if price_change >= UP_THRESHOLD or price_change <= DOWN_THRESHOLD:
                for bot in bots:
                    bot.trade(price_change, price)

                last_reference_price = price

        time.sleep(5)


trading_thread = threading.Thread(target=run_trading)
trading_thread.daemon = True
trading_thread.start()


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():
    current_price = get_price()
    total_equity = sum(bot.portfolio_value(current_price) for bot in bots)

    return render_template(
        "dashboard.html",
        bots=bots,
        total_equity=round(total_equity, 2),
        current_price=current_price,
        symbol=SYMBOL
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)