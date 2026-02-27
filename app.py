import ccxt
import pandas as pd
import numpy as np
from flask import Flask, render_template_string

app = Flask(__name__)

# ---- EXCHANGE ----
exchange = ccxt.kucoin({
    'enableRateLimit': True
})

START_BALANCE = 50
RISK_PER_TRADE = 0.07

engine = {
    "balance": START_BALANCE,
    "positions": {},
    "wins": 0,
    "losses": 0,
    "total_trades": 0,
    "last_action": "Starting..."
}

# ---- GET TOP 50 USDT PAIRS ----
def get_top_50():
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets if "/USDT" in s and markets[s]['active']]

    tickers = exchange.fetch_tickers(usdt_pairs)

    sorted_pairs = sorted(
        tickers.items(),
        key=lambda x: x[1]['quoteVolume'] if x[1]['quoteVolume'] else 0,
        reverse=True
    )

    return [pair[0] for pair in sorted_pairs[:50]]

# ---- FETCH 1M DATA ----
def fetch_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=50)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

    df['ema9'] = df['close'].ewm(span=9).mean()

    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    return df

# ---- CORE ENGINE ----
def evaluate():

    balance = engine["balance"]

    # Dynamic scaling
    if balance < 200:
        min_pos = 2
        max_pos = 7
    else:
        min_pos = 7
        max_pos = 11

    symbols = get_top_50()

    # ---- EXIT LOGIC ----
    for symbol in list(engine["positions"].keys()):
        df = fetch_data(symbol)
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        entry = engine["positions"][symbol]["entry"]
        size = engine["positions"][symbol]["size"]

        current_price = latest["close"]
        pnl = (current_price - entry) / entry

        if (
            latest["close"] < latest["ema9"] or
            latest["rsi"] < 55 or
            latest["close"] < prev["close"]
        ):
            engine["balance"] += size * (1 + pnl)
            engine["total_trades"] += 1

            if pnl > 0:
                engine["wins"] += 1
                engine["last_action"] = f"Exited {symbol} Profit"
            else:
                engine["losses"] += 1
                engine["last_action"] = f"Exited {symbol} Loss"

            del engine["positions"][symbol]

    # ---- ENTRY LOGIC ----
    if len(engine["positions"]) < max_pos:
        for symbol in symbols:

            if symbol in engine["positions"]:
                continue

            df = fetch_data(symbol)
            latest = df.iloc[-1]

            if (
                latest["close"] > latest["ema9"] and
                latest["rsi"] > 55
            ):
                size = engine["balance"] * RISK_PER_TRADE
                entry_price = latest["close"]

                engine["balance"] -= size

                engine["positions"][symbol] = {
                    "entry": entry_price,
                    "size": size
                }

                engine["last_action"] = f"Entered {symbol}"

                if len(engine["positions"]) >= max_pos:
                    break

# ---- UNREALIZED PNL ----
def calculate_unrealized():
    total = 0
    open_positions = []

    for symbol, pos in engine["positions"].items():
        df = fetch_data(symbol)
        current = df.iloc[-1]["close"]

        pnl = (current - pos["entry"]) / pos["entry"]
        value = pos["size"] * (1 + pnl)
        total += value

        open_positions.append({
            "symbol": symbol,
            "entry": round(pos["entry"],4),
            "current": round(current,4),
            "pnl_pct": round(pnl * 100,2),
            "value": round(value,2)
        })

    return total, open_positions

# ---- DASHBOARD ----
@app.route("/")
def dashboard():

    evaluate()
    unrealized_total, open_positions = calculate_unrealized()

    equity = engine["balance"] + unrealized_total
    roi = ((equity - START_BALANCE) / START_BALANCE) * 100

    win_rate = 0
    if engine["total_trades"] > 0:
        win_rate = (engine["wins"] / engine["total_trades"]) * 100

    return render_template_string("""
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body { background:#0b132b; color:white; font-family:Arial; padding:30px; }
            .card { background:#1c2541; padding:20px; margin-bottom:20px; border-radius:10px; }
            table { width:100%; }
            th, td { padding:6px; text-align:left; }
        </style>
    </head>
    <body>

        <h1>🚀 Multi-Coin Momentum Engine</h1>

        <div class="card">
            <h2>Equity: ${{equity}}</h2>
            <p>Cash Balance: ${{balance}}</p>
            <p>ROI: {{roi}}%</p>
            <p>Last Action: {{last_action}}</p>
        </div>

        <div class="card">
            <p>Total Trades: {{total_trades}}</p>
            <p>Wins: {{wins}}</p>
            <p>Losses: {{losses}}</p>
            <p>Win Rate: {{win_rate}}%</p>
        </div>

        <div class="card">
            <h3>Open Positions</h3>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>P/L %</th>
                    <th>Value</th>
                </tr>
                {% for p in open_positions %}
                <tr>
                    <td>{{p.symbol}}</td>
                    <td>{{p.entry}}</td>
                    <td>{{p.current}}</td>
                    <td>{{p.pnl_pct}}%</td>
                    <td>${{p.value}}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

    </body>
    </html>
    """,
    equity=round(equity,2),
    balance=round(engine["balance"],2),
    roi=round(roi,2),
    last_action=engine["last_action"],
    total_trades=engine["total_trades"],
    wins=engine["wins"],
    losses=engine["losses"],
    win_rate=round(win_rate,2),
    open_positions=open_positions
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)