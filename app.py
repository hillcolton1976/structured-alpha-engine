from flask import Flask, render_template_string
import ccxt
import pandas as pd
import threading
import time

app = Flask(__name__)

# ===== SETTINGS =====
TIMEFRAME = '5m'
CANDLE_LIMIT = 50
REFRESH_SECONDS = 15
COINS_PER_CYCLE = 10

exchange = ccxt.binance({
    'enableRateLimit': True
})

cached_data = []
coin_list = []
cycle_index = 0


# ===== RSI =====
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# ===== GET TOP 50 USDT PAIRS =====
def load_top_coins():
    markets = exchange.load_markets()
    usdt_pairs = [m for m in markets if m.endswith('/USDT')]
    return usdt_pairs[:50]


# ===== SCAN COINS =====
def scan_cycle():
    global cached_data, cycle_index

    while True:
        try:
            results = []
            start = cycle_index
            end = start + COINS_PER_CYCLE
            symbols = coin_list[start:end]

            for symbol in symbols:
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
                    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

                    df['rsi'] = rsi(df['close'])
                    current_rsi = df['rsi'].iloc[-1]
                    price = df['close'].iloc[-1]

                    signal = "NEUTRAL"
                    if current_rsi < 30:
                        signal = "BUY"
                    elif current_rsi > 70:
                        signal = "SELL"

                    results.append({
                        "symbol": symbol,
                        "price": round(price, 4),
                        "rsi": round(current_rsi, 2),
                        "signal": signal
                    })

                except:
                    pass

            cached_data = results
            cycle_index = (cycle_index + COINS_PER_CYCLE) % 50

        except:
            pass

        time.sleep(10)


# ===== ROUTE =====
@app.route("/")
def index():
    return render_template_string("""
    <html>
    <head>
        <meta http-equiv="refresh" content="{{ refresh }}">
        <style>
            body { background:#111; color:#ddd; font-family:Arial; }
            table { width:100%; border-collapse:collapse; }
            th, td { padding:10px; text-align:center; }
            th { background:#222; }
            tr:nth-child(even) { background:#1a1a1a; }
            .buy { color:#4CAF50; }
            .sell { color:#f44336; }
        </style>
    </head>
    <body>
        <h2>🔥 Aggressive Scanner (Rotating Top 50)</h2>
        <table>
            <tr>
                <th>Coin</th>
                <th>Price</th>
                <th>RSI</th>
                <th>Signal</th>
            </tr>
            {% for coin in coins %}
            <tr>
                <td>{{ coin.symbol }}</td>
                <td>${{ coin.price }}</td>
                <td>{{ coin.rsi }}</td>
                <td class="{{ coin.signal|lower }}">{{ coin.signal }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """, coins=cached_data, refresh=REFRESH_SECONDS)


# ===== START BACKGROUND THREAD =====
if __name__ == "__main__":
    coin_list = load_top_coins()
    threading.Thread(target=scan_cycle, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)