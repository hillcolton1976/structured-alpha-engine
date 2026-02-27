from flask import Flask, render_template_string
import ccxt
import pandas as pd
import threading
import time

app = Flask(__name__)

# ===============================
# CONFIG
# ===============================

TIMEFRAME = '1m'
SCAN_INTERVAL = 60
MAX_COINS = 7   # You can raise to 11 later

# ===============================
# GLOBAL STATE
# ===============================

stats = {
    "trades": 0,
    "wins": 0,
    "losses": 0
}

open_positions = {}
signals = []
coin_list = []

# ===============================
# EXCHANGE (Binance US SAFE)
# ===============================

exchange = ccxt.binanceus({
    'enableRateLimit': True
})

# ===============================
# HELPERS
# ===============================

def get_top_coins():
    markets = exchange.load_markets()
    usdt_pairs = [
        s for s in markets
        if "/USDT" in s and markets[s]['active']
    ]
    return usdt_pairs[:MAX_COINS]

def fetch_dataframe(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=50)
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp','open','high','low','close','volume']
        )
        return df
    except:
        return None

def add_indicators(df):
    if df is None or len(df) < 30:
        return None

    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()
    return df

def check_entry(df):
    if df is None or len(df) < 30:
        return False

    if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
        return True
    return False

# ===============================
# ENGINE LOOP
# ===============================

def engine():
    global signals, open_positions, stats, coin_list

    while True:
        try:
            coin_list = get_top_coins()

            for symbol in coin_list:
                df = fetch_dataframe(symbol)
                df = add_indicators(df)

                if df is None:
                    continue

                price = df['close'].iloc[-1]

                # ENTRY
                if symbol not in open_positions:
                    if check_entry(df):
                        open_positions[symbol] = price
                        stats["trades"] += 1
                        signals.append(f"BUY {symbol} @ {price}")

                # EXIT
                else:
                    entry_price = open_positions[symbol]

                    if price > entry_price * 1.003:
                        stats["wins"] += 1
                        signals.append(f"WIN {symbol}")
                        del open_positions[symbol]

                    elif price < entry_price * 0.997:
                        stats["losses"] += 1
                        signals.append(f"LOSS {symbol}")
                        del open_positions[symbol]

        except Exception as e:
            print("Engine error:", e)

        time.sleep(SCAN_INTERVAL)

# ===============================
# START BACKGROUND THREAD
# ===============================

threading.Thread(target=engine, daemon=True).start()

# ===============================
# DASHBOARD
# ===============================

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <title>Trading Bot</title>
    </head>
    <body style="font-family: Arial; background:#111; color:#0f0;">
        <h1>🚀 Trading Bot Dashboard</h1>

        <h2>Stats</h2>
        <p>Trades: {{stats.trades}}</p>
        <p>Wins: {{stats.wins}}</p>
        <p>Losses: {{stats.losses}}</p>

        <h2>Scanning Coins</h2>
        <ul>
        {% for coin in coin_list %}
            <li>{{coin}}</li>
        {% endfor %}
        </ul>

        <h2>Open Positions</h2>
        <ul>
        {% for coin, price in open_positions.items() %}
            <li>{{coin}} @ {{price}}</li>
        {% endfor %}
        </ul>

        <h2>Recent Signals</h2>
        <ul>
        {% for s in signals[-10:] %}
            <li>{{s}}</li>
        {% endfor %}
        </ul>

    </body>
    </html>
    """, stats=stats,
         signals=signals,
         open_positions=open_positions,
         coin_list=coin_list)

if __name__ == "__main__":
    app.run()