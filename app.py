import random
import threading
import time
from flask import Flask, render_template

app = Flask(__name__)

# =========================
# BOT CLASS
# =========================
class TradingBot:
    def __init__(self, strategy, capital=1000):
        self.strategy = strategy
        self.capital = capital
        self.pnl = 0
        self.trades = 0

        # Performance tracking
        self.wins = 0
        self.losses = 0

        # Learning memory
        self.memory = []
        self.aggression = 1.0

    def trade(self):
        """
        Simulated trade logic.
        Each strategy behaves slightly differently.
        """

        base_move = random.uniform(-20, 25)

        # Strategy adjustments
        if self.strategy == "Scalper":
            base_move *= 0.5
        elif self.strategy == "Momentum":
            base_move *= 1.3
        elif self.strategy == "Mean Reversion":
            base_move *= 0.8
        elif self.strategy == "Breakout":
            base_move *= 1.6

        # Aggression multiplier (learning)
        profit = base_move * self.aggression

        # Apply trade
        self.pnl += profit
        self.capital += profit
        self.trades += 1

        # Track wins/losses
        if profit > 0:
            self.wins += 1
        else:
            self.losses += 1

        # Learning logic
        self.memory.append(profit)

        if len(self.memory) > 20:
            recent_avg = sum(self.memory[-20:]) / 20

            # Adjust aggression based on recent performance
            if recent_avg > 0:
                self.aggression *= 1.02
            else:
                self.aggression *= 0.98

            # Prevent runaway growth
            self.aggression = max(0.5, min(self.aggression, 2.5))


# =========================
# CREATE BOTS (Independent)
# =========================
bots = [
    TradingBot("Scalper", 1000),
    TradingBot("Momentum", 1000),
    TradingBot("Mean Reversion", 1000),
    TradingBot("Breakout", 1000),
]

# =========================
# BACKGROUND AUTO TRADING
# =========================
def run_trading():
    while True:
        for bot in bots:
            bot.trade()
        time.sleep(5)  # trades every 5 seconds

trading_thread = threading.Thread(target=run_trading)
trading_thread.daemon = True
trading_thread.start()

# =========================
# DASHBOARD ROUTE
# =========================
@app.route("/")
def dashboard():
    total_equity = sum(bot.capital for bot in bots)

    return render_template(
        "dashboard.html",
        bots=bots,
        total_equity=round(total_equity, 2)
    )

# =========================
# REQUIRED FOR GUNICORN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)