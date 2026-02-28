import ccxt
import pandas as pd
import numpy as np
import time
import threading
from flask import Flask, jsonify, render_template_string

# ================================
# CONFIG
# ================================

TIMEFRAME = '3m'
START_BALANCE = 1000
MAX_COINS = 10
BASE_RISK = 0.10
SLEEP_SECONDS = 15

app = Flask(__name__)

# ================================
# GLOBAL STATE
# ================================

state = {
    "balance": START_BALANCE,
    "wins": 0,
    "losses": 0,
    "trades": 0,
    "positions": {},
    "signals": [],
    "aggression": BASE_RISK
}

# ================================
# TRADER ENGINE
# ================================

class Trader:
    def __init__(self):
        self.exchange = ccxt.binanceus()
        self.symbols = []

    def get_symbols(self):
        markets = self.exchange.load_markets()
        pairs = [
            s for s in markets
            if '/USDT' in s and markets[s]['active']
        ]
        return pairs[:MAX_COINS]

    def fetch_data(self, symbol):
        ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        return df

    def score(self, df):
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema21'] = df['c'].ewm(span=21).mean()
        score = 0

        if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
            score += 1

        if df['v'].iloc[-1] > df['v'].rolling(20).mean().iloc[-1]:
            score += 1

        return score, df['c'].iloc[-1]

    def adjust_aggression(self):
        total = state["wins"] + state["losses"]
        if total > 5:
            winrate = state["wins"] / total
            if winrate < 0.4:
                state["aggression"] *= 0.9
            elif winrate > 0.6:
                state["aggression"] *= 1.1

            state["aggression"] = max(0.05, min(0.25, state["aggression"]))

    def run(self):
        self.symbols = self.get_symbols()
        print("Monitoring:", self.symbols)

        while True:
            try:
                for symbol in self.symbols:
                    df = self.fetch_data(symbol)
                    score, price = self.score(df)

                    if score >= 2 and symbol not in state["positions"]:
                        size = state["balance"] * state["aggression"]
                        state["positions"][symbol] = {
                            "entry": price,
                            "size": size
                        }
                        state["signals"].append(f"🚀 BUY {symbol} @ {round(price,2)}")

                    if symbol in state["positions"]:
                        entry = state["positions"][symbol]["entry"]
                        pnl = (price - entry) / entry

                        if pnl > 0.01 or pnl < -0.01:
                            state["trades"] += 1
                            if pnl > 0:
                                state["wins"] += 1
                                state["balance"] *= 1.01
                            else:
                                state["losses"] += 1
                                state["balance"] *= 0.99

                            state["signals"].append(
                                f"💥 SELL {symbol} | PnL {round(pnl*100,2)}%"
                            )
                            del state["positions"][symbol]
                            self.adjust_aggression()

                time.sleep(SLEEP_SECONDS)

            except Exception as e:
                print("Error:", e)
                time.sleep(5)

# ================================
# ROUTES
# ================================

@app.route("/")
def dashboard():
    return render_template_string("""
    <html>
    <head>
        <title>Adaptive AI Trader</title>
        <style>
            body {
                background: linear-gradient(135deg,#0f172a,#1e293b);
                color: white;
                font-family: Arial;
                padding: 20px;
            }
            .card {
                background: #1e293b;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }
            h1 { color: #f97316; }
            .green { color: #22c55e; }
            .red { color: #ef4444; }
        </style>
        <script>
            async function refresh() {
                const res = await fetch('/data');
                const data = await res.json();
                document.getElementById("balance").innerText = "$" + data.balance.toFixed(2);
                document.getElementById("wins").innerText = data.wins;
                document.getElementById("losses").innerText = data.losses;
                document.getElementById("trades").innerText = data.trades;
                document.getElementById("agg").innerText = (data.aggression*100).toFixed(1)+"%";
                document.getElementById("signals").innerText = data.signals.slice(-8).join("\\n");
            }
            setInterval(refresh, 3000);
            window.onload = refresh;
        </script>
    </head>
    <body>
        <h1>🔥 Adaptive AI Trader</h1>

        <div class="card">
            <b>Balance:</b> <span id="balance"></span><br>
            <b>Trades:</b> <span id="trades"></span><br>
            <b>Wins:</b> <span id="wins" class="green"></span><br>
            <b>Losses:</b> <span id="losses" class="red"></span><br>
            <b>Aggression Level:</b> <span id="agg"></span>
        </div>

        <div class="card">
            <b>Recent Signals</b><br><br>
            <pre id="signals"></pre>
        </div>
    </body>
    </html>
    """)

@app.route("/data")
def data():
    return jsonify(state)

# ================================
# START TRADER THREAD
# ================================

threading.Thread(target=Trader().run, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)