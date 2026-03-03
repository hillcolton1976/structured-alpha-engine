from flask import Flask, render_template

app = Flask(__name__)

SYMBOL = "BTCUSDT"

# =========================
# BOT CLASS
# =========================
class TradingBot:
    def __init__(self, name):
        self.name = name
        self.cash = 50
        self.coins = 0.0
        self.trades = 0

    def total_value(self, price):
        return self.cash + (self.coins * price)

    def profit(self, price):
        return self.total_value(price) - 50


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
# STATIC PRICE (SAFE)
# =========================
def get_price():
    # Static price so nothing external can crash
    return 50000.0


# =========================
# DASHBOARD ROUTE
# =========================
@app.route("/")
def dashboard():
    price = get_price()

    total_equity = sum(bot.total_value(price) for bot in bots)

    return render_template(
        "dashboard.html",
        bots=bots,
        current_price=price,
        total_equity=round(total_equity, 2),
        symbol=SYMBOL
    )


# =========================
# RAILWAY SAFE START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)