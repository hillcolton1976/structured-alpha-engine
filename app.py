import json
import threading
import time
import random
import requests
from flask import Flask
from websocket import WebSocketApp

app = Flask(__name__)

# =============================
# CONFIG
# =============================

START_BALANCE = 50.0
MAX_COINS = 15
BASE_AGGRESSION = 0.20
MIN_AGGRESSION = 0.05
MAX_AGGRESSION = 0.50

# =============================
# ACCOUNT STATE
# =============================

balance = START_BALANCE
equity = START_BALANCE
wins = 0
losses = 0
trades = 0
aggression = BASE_AGGRESSION

positions = {}
price_data = {}
recent_signals = []

lock = threading.Lock()

# =============================
# GET TOP COINS (SAFE)
# =============================

def get_top_pairs():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr", timeout=5)
        data = r.json()

        if not isinstance(data, list):
            return fallback_coins()

        usdt = [x for x in data if x["symbol"].endswith("USDT")]
        sorted_pairs = sorted(
            usdt,
            key=lambda x: float(x.get("quoteVolume", 0)),
            reverse=True
        )

        return [x["symbol"].lower() for x in sorted_pairs[:MAX_COINS]]

    except:
        return fallback_coins()

def fallback_coins():
    return [
        "btcusdt","ethusdt","solusdt","xrpusdt",
        "bnbusdt","adausdt","dogeusdt","linkusdt",
        "avaxusdt","dotusdt","maticusdt","atomusdt",
        "ltcusdt","nearusdt","filusdt"
    ][:MAX_COINS]

coins = get_top_pairs()

# =============================
# WEBSOCKET PRICE STREAM
# =============================

def on_message(ws, message):
    data = json.loads(message)
    symbol = data["s"].lower()
    price = float(data["c"])

    with lock:
        price_data[symbol] = price

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connected")

def start_socket():
    streams = "/".join([f"{c}@ticker" for c in coins])
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    ws = WebSocketApp(
        url,
        on_message=lambda ws, msg: on_message(ws, json.loads(msg)["data"]),
        on_error=on_error,
        on_close=on_close
    )

    ws.on_open = on_open
    ws.run_forever()

# =============================
# SELF-ADJUSTING AI LOGIC
# =============================

def adjust_aggression():
    global aggression

    if trades < 10:
        return

    win_rate = wins / trades

    if win_rate > 0.6:
        aggression = min(aggression + 0.05, MAX_AGGRESSION)
    elif win_rate < 0.4:
        aggression = max(aggression - 0.05, MIN_AGGRESSION)

def trader():
    global balance, equity, wins, losses, trades

    while True:
        time.sleep(2)

        with lock:
            for symbol, price in price_data.items():

                # OPEN TRADE
                if symbol not in positions and balance > 5:
                    if random.random() < aggression:
                        size = balance * aggression
                        qty = size / price

                        positions[symbol] = {
                            "entry": price,
                            "qty": qty
                        }

                        balance -= size
                        recent_signals.insert(0, f"🚀 BUY {symbol.upper()} @ {round(price,4)}")

                # CLOSE TRADE
                elif symbol in positions:
                    entry = positions[symbol]["entry"]
                    qty = positions[symbol]["qty"]

                    pnl = (price - entry) * qty

                    # aggressive take profit / stop loss
                    if pnl > entry * 0.005 or pnl < -entry * 0.005:
                        balance += qty * price
                        trades += 1

                        if pnl > 0:
                            wins += 1
                        else:
                            losses += 1

                        recent_signals.insert(
                            0,
                            f"💰 SELL {symbol.upper()} @ {round(price,4)} | PnL {round(pnl,2)}"
                        )

                        del positions[symbol]

            # UPDATE EQUITY
            equity = balance
            for sym, pos in positions.items():
                if sym in price_data:
                    equity += pos["qty"] * price_data[sym]

            adjust_aggression()

        if len(recent_signals) > 15:
            recent_signals.pop()

# =============================
# UI
# =============================

@app.route("/")
def dashboard():
    win_rate = (wins / trades * 100) if trades > 0 else 0

    return f"""
    <html>
    <head>
    <meta http-equiv="refresh" content="3">
    <style>
    body {{
        font-family: Arial;
        background: linear-gradient(to right, #0f2027, #203a43, #2c5364);
        color: white;
        padding: 20px;
    }}
    .card {{
        background: rgba(255,255,255,0.08);
        padding: 20px;
        margin-bottom: 20px;
        border-radius: 10px;
    }}
    h1 {{ color: orange; }}
    .green {{ color: #4cff88; }}
    .red {{ color: #ff4c4c; }}
    </style>
    </head>
    <body>
        <h1>🔥 Aggressive AI Trader (WebSocket)</h1>

        <div class="card">
            <h2>Account</h2>
            <p><b>Equity:</b> ${round(equity,2)}</p>
            <p><b>Balance:</b> ${round(balance,2)}</p>
            <p><b>Trades:</b> {trades}</p>
            <p class="green"><b>Wins:</b> {wins}</p>
            <p class="red"><b>Losses:</b> {losses}</p>
            <p><b>Win Rate:</b> {round(win_rate,2)}%</p>
            <p><b>Aggression:</b> {round(aggression*100,1)}%</p>
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            { "<br>".join([f"{k.upper()} @ {round(v['entry'],4)}" for k,v in positions.items()]) or "None" }
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {"<br>".join(recent_signals[:10])}
        </div>
    </body>
    </html>
    """

# =============================
# START THREADS
# =============================

threading.Thread(target=start_socket, daemon=True).start()
threading.Thread(target=trader, daemon=True).start()