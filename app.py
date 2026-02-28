from flask import Flask, render_template_string
import ccxt
import pandas as pd
import time

app = Flask(__name__)

# ===== SETTINGS =====
TIMEFRAME = '5m'
CANDLE_LIMIT = 120
TOP_COINS_LIMIT = 50
REFRESH_SECONDS = 20

exchange = ccxt.kraken({
    'enableRateLimit': True
})

# ===== RSI FUNCTION =====
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===== GET TOP COINS =====
def get_top_symbols():
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and markets[s]['active']]
    return symbols[:TOP_COINS_LIMIT]

# ===== FETCH DATA =====
def get_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema21'] = df['c'].ewm(span=21).mean()
        df['rsi'] = rsi(df['c'])
        return df
    except:
        return None

# ===== SIGNAL LOGIC (AGGRESSIVE) =====
def check_signal(df):
    if df is None or len(df) < 30:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Strong breakout momentum
    if prev['ema9'] < prev['ema21'] and last['ema9'] > last['ema21'] and last['rsi'] > 55:
        return "🚀 BUY"

    # Strong breakdown
    if prev['ema9'] > prev['ema21'] and last['ema9'] < last['ema21'] and last['rsi'] < 45:
        return "🔻 SELL"

    return None

# ===== ROUTE =====
@app.route("/")
def index():
    symbols = get_top_symbols()
    signals = []

    for symbol in symbols:
        df = get_data(symbol)
        signal = check_signal(df)

        if signal:
            price = round(df['c'].iloc[-1], 4)
            signals.append({
                "symbol": symbol,
                "signal": signal,
                "price": price
            })

        time.sleep(0.1)

    template = """
    <html>
    <head>
        <meta http-equiv="refresh" content="{{refresh}}">
        <style>
            body { background:#111; color:#ddd; font-family:Arial; }
            h1 { color:#ff3b3b; }
            table { width:100%; border-collapse:collapse; }
            th, td { padding:10px; border-bottom:1px solid #333; text-align:left; }
            tr:hover { background:#1c1c1c; }
            .buy { color:#00ff99; font-weight:bold; }
            .sell { color:#ff4444; font-weight:bold; }
        </style>
    </head>
    <body>
        <h1>🔥 AGGRESSIVE TOP 50 SCANNER</h1>
        <table>
            <tr>
                <th>Coin</th>
                <th>Signal</th>
                <th>Price</th>
            </tr>
            {% for row in signals %}
            <tr>
                <td>{{row.symbol}}</td>
                <td class="{{'buy' if 'BUY' in row.signal else 'sell'}}">
                    {{row.signal}}
                </td>
                <td>{{row.price}}</td>
            </tr>
            {% endfor %}
        </table>
        <p>Auto refresh: {{refresh}}s</p>
    </body>
    </html>
    """

    return render_template_string(template, signals=signals, refresh=REFRESH_SECONDS)

# ===== START =====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)