import requests
import threading
import time
from flask import Flask, render_template

app = Flask(__name__)

SYMBOL = "BTCUSDT"
BINANCE_URL = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"

last_price = None

# =========================
# BOT CLASS
# =========================
class TradingBot:
    def __init__(self, strategy, capital=50):
        self.strategy = strategy
        self.capital = capital
        self.pnl = 0
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.memory = []
        self.aggression = 1.0

    def trade(self, price_change_percent):
        # Strategy modifiers
        if self.strategy == "Scalper":
            multiplier = 0.5
        elif self.strategy == "Momentum":
            multiplier = 1.3
        elif self.strategy == "Mean Reversion":
            multiplier = -0.8  # trades opposite
        elif self.strategy == "Breakout":
            multiplier = 1.6
        else:
            multiplier = 1.0

        # Position sizing (paper)
        position_size = self.capital * 0.2  # 20% per trade

        profit = position_size * (price_change_percent / 100) * multiplier
        profit *= self.aggression

        self.capital += profit
        self.pnl += profit
        self.trades += 1

        if profit > 0:
            self.wins += 1
        else:
            self.losses += 1

        # Learning
        self.memory.append(profit)
        if len(self.memory) > 20:
            recent_avg = sum(self.memory[-20:]) / 20
            if recent_avg > 0:
                self.aggression *= 1.02
            else:
                self.aggression *= 0.98

            self.aggression = max(0.5, min(self.aggression, 2.5))


# =========================
# CREATE BOTS
# =========================
bots = [
    TradingBot("Scalper", 50),
    TradingBot("Momentum", 50),
    TradingBot("Mean Reversion", 50),
    TradingBot("Breakout", 50),
]


# =========================
# GET LIVE PRICE
# =========================
def get_price():
    global last_price
    try:
        response = requests.get(BINANCE_URL, timeout=5)
        data = response.json()
        price = float(data["price"])
        return price
    except:
        return None


# =========================
# BACKGROUND TRADING LOOP
# =========================
def run_trading():
    global last_price

    while True:
        price = get_price()

        if price:
            if last_price:
                price_change = ((price - last_price) / last_price) * 100

                for bot in bots:
                    bot.trade(price_change)

            last_price = price

        time.sleep(10)  # checks every 10 seconds


trading_thread = threading.Thread(target=run_trading)
trading_thread.daemon = True
trading_thread.start()


# =========================
# DASHBOARD
# =========================
@app.route("/")
def dashboard():
    total_equity = sum(bot.capital for bot in bots)
    return render_template(
        "dashboard.html",
        bots=bots,
        total_equity=round(total_equity, 2),
        symbol=SYMBOL
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)