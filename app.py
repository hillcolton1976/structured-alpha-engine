from flask import Flask, render_template_string
import threading
import time
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
losses = 0
last_action = "Booting..."
active_trade = None
recent_trades = []

exchange = ccxt.kraken()
timeframe = "1m"

# -----------------------
# GET TOP 50 USDT PAIRS
# -----------------------
def get_top_50():
    markets = exchange.load_markets()
    tickers = exchange.fetch_tickers()

    usdt_pairs = []

    for symbol in markets:
        if "/USDT" in symbol and symbol in tickers:
            volume = tickers[symbol].get("quoteVolume", 0)
            usdt_pairs.append((symbol, volume))

    usdt_pairs.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in usdt_pairs[:50]]

# -----------------------
# ENTRY LOGIC
# -----------------------
def check_entry(df):
    last = df["close"].iloc[-1]
    prev_high = df["high"].iloc[-2]
    return last > prev_high

# -----------------------
# TRADING LOOP
# -----------------------
def trading_bot():
    global balance, total_trades, wins, losses, last_action, active_trade, recent_trades

    while True:
        try:
            symbols = get_top_50()

            # If no active trade → scan
            if active_trade is None:
                for symbol in symbols:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=20)
                    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])

                    if check_entry(df):
                        entry = df["close"].iloc[-1]
                        active_trade = {
                            "symbol": symbol,
                            "entry": entry
                        }
                        last_action = f"Entered {symbol}"
                        break

            # If active trade → monitor
            else:
                symbol = active_trade["symbol"]
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=2)
                df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])

                price = df["close"].iloc[-1]
                entry = active_trade["entry"]

                change = (price - entry) / entry

                if change >= 0.01:  # 1% take profit
                    profit = balance * 0.02
                    balance += profit
                    wins += 1
                    result = f"+${round(profit,2)}"
                    close_trade(symbol, result, "TP")

                elif change <= -0.005:  # 0.5% stop
                    loss = balance * 0.02
                    balance -= loss
                    losses += 1
                    result = f"-${round(loss,2)}"
                    close_trade(symbol, result, "SL")

            time.sleep(30)

        except Exception as e:
            last_action = f"Error: {str(e)}"
            time.sleep(10)

def close_trade(symbol, result, reason):
    global active_trade, total_trades, recent_trades, last_action

    total_trades += 1
    recent_trades.insert(0, {
        "symbol": symbol,
        "result": result,
        "balance": round(balance,2)
    })

    if len(recent_trades) > 15:
        recent_trades.pop()

    last_action = f"{reason} on {symbol}"
    active_trade = None

# -----------------------
# START THREAD
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
        <h1>🚀 Rotation Engine (Top 50)</h1>

        <div class="card">
            <h2>Balance: ${{balance}}</h2>
            <p>ROI: {{roi}}%</p>
            <p>Last Action: {{last_action}}</p>
        </div>

        <div class="card">
            <h3>Performance</h3>
            <p>Total Trades: {{total_trades}}</p>
            <p>Wins: {{wins}}</p>
            <p>Losses: {{losses}}</p>
            <p>Win Rate: {{win_rate}}%</p>
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
    wins=wins,
    losses=losses,
    win_rate=win_rate,
    trades=recent_trades
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)