from flask import Flask, render_template_string
import threading
import time
import random
import ccxt
import pandas as pd

app = Flask(__name__)

# -----------------------
# GLOBAL STATE
# -----------------------
balance = 50.0
initial_balance = 50.0
total_trades = 0
wins = 0
last_action = "Starting..."
level = 1
recent_trades = []

# -----------------------
# EXCHANGE (1m candles)
# -----------------------
exchange = ccxt.kraken()

symbol = "BTC/USDT"
timeframe = "1m"

# -----------------------
# TRADING LOOP
# -----------------------
def trading_bot():
    global balance, total_trades, wins, last_action, recent_trades

    while True:
        try:
            # Fetch 1 minute candles
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=20)
            df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])

            last_close = df["close"].iloc[-1]
            prev_close = df["close"].iloc[-2]

            # Simple momentum logic
            if last_close > prev_close:
                profit = random.uniform(0.10, 0.40)
                balance += profit
                wins += 1
                result = f"+${round(profit,2)}"
                last_action = "BUY → Profit"
            else:
                loss = random.uniform(0.10, 0.40)
                balance -= loss
                result = f"-${round(loss,2)}"
                last_action = "SELL → Loss"

            total_trades += 1

            recent_trades.insert(0, {
                "symbol": symbol,
                "result": result,
                "balance": round(balance,2)
            })

            if len(recent_trades) > 10:
                recent_trades.pop()

        except Exception as e:
            last_action = f"Error: {str(e)}"

        time.sleep(60)  # 1 minute cycle


# -----------------------
# START BACKGROUND THREAD
# -----------------------
threading.Thread(target=trading_bot, daemon=True).start()


# -----------------------
# DASHBOARD
# -----------------------
@app.route("/")
def dashboard():
    roi = round(((balance - initial_balance) / initial_balance) * 100, 2)
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0

    return render_template_string("""
    <html>
    <head>
        <meta http-equiv="refresh" content="5">
        <style>
            body { background:#0b132b; color:white; font-family:Arial; padding:30px;}
            .card { background:#1c2541; padding:20px; margin-bottom:20px; border-radius:10px;}
        </style>
    </head>
    <body>
        <h1>🚀 Dynamic Rotation Engine</h1>

        <div class="card">
            <h2>Balance: ${{balance}}</h2>
            <p>ROI: {{roi}}%</p>
            <p>Level: 1</p>
            <p>Last Action: {{last_action}}</p>
        </div>

        <div class="card">
            <h3>Performance</h3>
            <p>Total Trades: {{total_trades}}</p>
            <p>Win Rate: {{win_rate}}%</p>
            <p>Total Profit: ${{profit}}</p>
        </div>

        <div class="card">
            <h3>Recent Trades</h3>
            {% for trade in trades %}
                <p>{{trade.symbol}} | {{trade.result}} | ${{trade.balance}}</p>
            {% endfor %}
        </div>
    </body>
    </html>
    """,
    balance=round(balance,2),
    roi=roi,
    last_action=last_action,
    total_trades=total_trades,
    win_rate=win_rate,
    profit=round(balance-initial_balance,2),
    trades=recent_trades
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)