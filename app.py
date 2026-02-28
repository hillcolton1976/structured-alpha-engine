import ccxt
import pandas as pd
import numpy as np
import threading
import time
from flask import Flask, render_template_string

app = Flask(__name__)

# ===== CONFIG =====
TIMEFRAME = '1m'
ROTATION_SIZE = 20
MAX_POSITIONS = 7
START_BALANCE = 50
BASE_RISK = 0.10  # 10% per trade
STOP_LOSS = -0.007
TAKE_PROFIT = 0.012
TRAIL_TRIGGER = 0.006
TIME_STOP = 60 * 12

# ===== STATE =====
exchange = ccxt.binance({'enableRateLimit': True})
balance = START_BALANCE
cash = START_BALANCE
positions = {}
recent_signals = []
stats = {"trades": 0, "wins": 0, "losses": 0}
setup_performance = {"momentum": {"wins": 0, "losses": 0}}

# ===== HELPERS =====
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_top_50():
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets if "/USDT" in s and markets[s]['active']]
    return usdt_pairs[:50]

def position_size():
    perf = setup_performance["momentum"]
    total = perf["wins"] + perf["losses"]
    if total < 5:
        return BASE_RISK
    winrate = perf["wins"] / total
    if winrate > 0.55:
        return BASE_RISK * 1.5
    elif winrate < 0.45:
        return BASE_RISK * 0.5
    return BASE_RISK

# ===== TRADING LOGIC =====
def trade_engine():
    global cash, balance
    coins = get_top_50()
    rotation_index = 0

    while True:
        batch = coins[rotation_index:rotation_index+ROTATION_SIZE]
        rotation_index = (rotation_index + ROTATION_SIZE) % len(coins)

        for symbol in batch:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=50)
                df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
                df['ema20'] = df['c'].ewm(span=20).mean()
                df['rsi'] = rsi(df['c'])
                df['vol_avg'] = df['v'].rolling(20).mean()

                last = df.iloc[-1]
                prev = df.iloc[-2]

                momentum = (last['c'] - prev['c']) / prev['c']

                # ENTRY
                if (symbol not in positions and
                    len(positions) < MAX_POSITIONS and
                    last['rsi'] > 40 and
                    last['c'] > last['ema20'] and
                    last['v'] > last['vol_avg'] * 1.5 and
                    momentum > 0.004):

                    size_pct = position_size()
                    allocation = cash * size_pct
                    qty = allocation / last['c']

                    positions[symbol] = {
                        "entry": last['c'],
                        "qty": qty,
                        "time": time.time(),
                        "trail": None
                    }

                    cash -= allocation
                    recent_signals.insert(0, f"Entered {symbol}")
                    recent_signals[:] = recent_signals[:20]

                # EXIT
                if symbol in positions:
                    entry = positions[symbol]["entry"]
                    pnl = (last['c'] - entry) / entry

                    if pnl >= TRAIL_TRIGGER:
                        positions[symbol]["trail"] = last['c'] * 0.995

                    trail_hit = (
                        positions[symbol]["trail"] and
                        last['c'] < positions[symbol]["trail"]
                    )

                    if (pnl <= STOP_LOSS or
                        pnl >= TAKE_PROFIT or
                        trail_hit or
                        time.time() - positions[symbol]["time"] > TIME_STOP):

                        qty = positions[symbol]["qty"]
                        cash += qty * last['c']
                        stats["trades"] += 1

                        if pnl > 0:
                            stats["wins"] += 1
                            setup_performance["momentum"]["wins"] += 1
                        else:
                            stats["losses"] += 1
                            setup_performance["momentum"]["losses"] += 1

                        recent_signals.insert(0, f"Exited {symbol} ({round(pnl*100,2)}%)")
                        recent_signals[:] = recent_signals[:20]
                        del positions[symbol]

            except:
                continue

        balance = cash + sum(
            positions[s]["qty"] *
            exchange.fetch_ticker(s)["last"]
            for s in positions
        )

        time.sleep(5)

# ===== WEB UI =====
@app.route("/")
def dashboard():
    winrate = 0
    if stats["trades"] > 0:
        winrate = (stats["wins"] / stats["trades"]) * 100

    return render_template_string("""
    <html>
    <body style="background:#0f172a;color:white;font-family:sans-serif;padding:20px">
    <h2>🔥 Adaptive Aggressive Paper Trader</h2>

    <div>
    <b>Equity:</b> ${{ balance|round(2) }}<br>
    <b>Cash:</b> ${{ cash|round(2) }}<br>
    <b>Trades:</b> {{ trades }}<br>
    <b>Wins:</b> {{ wins }}<br>
    <b>Losses:</b> {{ losses }}<br>
    <b>Win Rate:</b> {{ winrate|round(1) }}%
    </div>

    <h3>Open Positions ({{ positions|length }})</h3>
    {% for s,p in positions.items() %}
        {{ s }} @ {{ p.entry|round(4) }}<br>
    {% endfor %}

    <h3>Recent Signals</h3>
    {% for sig in recent_signals %}
        {{ sig }}<br>
    {% endfor %}
    </body>
    </html>
    """,
    balance=balance,
    cash=cash,
    trades=stats["trades"],
    wins=stats["wins"],
    losses=stats["losses"],
    winrate=winrate,
    positions=positions,
    recent_signals=recent_signals
    )

# ===== START THREAD =====
threading.Thread(target=trade_engine, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)