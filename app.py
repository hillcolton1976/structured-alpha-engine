import ccxt
import pandas as pd
import time
import threading
from flask import Flask, render_template_string

app = Flask(__name__)

# =========================
# CONFIG
# =========================

TIMEFRAME = "3m"
START_BALANCE = 50.0

state = {
    "balance": START_BALANCE,
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "aggression": 0.15,  # 15% per trade (aggressive)
    "positions": {},
    "signals": []
}

# =========================
# TRADER ENGINE
# =========================

class Trader:
    def __init__(self):
        self.exchange = ccxt.binanceus()
        self.symbols = self.get_symbols()

    def get_symbols(self):
        markets = self.exchange.load_markets()
        pairs = [
            s for s in markets
            if "/USDT" in s and markets[s]["active"]
        ]
        return pairs[:20]  # scan top 20 for speed

    def fetch_data(self, symbol):
        ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=120)
        df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
        return df

    def score(self, df):
        df["ema9"] = df["c"].ewm(span=9).mean()
        df["ema21"] = df["c"].ewm(span=21).mean()

        delta = df["c"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df["rsi"] = 100 - (100 / (1 + rs))

        score = 0

        if df["ema9"].iloc[-1] > df["ema21"].iloc[-1]:
            score += 1

        if df["rsi"].iloc[-1] > 55:
            score += 1

        if df["v"].iloc[-1] > df["v"].rolling(20).mean().iloc[-1]:
            score += 1

        return score, df["c"].iloc[-1]

    def adjust_aggression(self):
        total = state["wins"] + state["losses"]
        if total >= 5:
            winrate = state["wins"] / total

            if winrate < 0.45:
                state["aggression"] *= 0.85
            elif winrate > 0.55:
                state["aggression"] *= 1.15

            state["aggression"] = max(0.08, min(0.30, state["aggression"]))

    def run(self):
        print("🔥 Aggressive AI Trader Running...")
        print("Monitoring:", self.symbols)

        while True:
            try:
                for symbol in self.symbols:
                    df = self.fetch_data(symbol)
                    score, price = self.score(df)

                    # ENTRY
                    if score >= 2 and symbol not in state["positions"]:
                        size = state["balance"] * state["aggression"]

                        if size > 1:
                            state["positions"][symbol] = {
                                "entry": price,
                                "size": size
                            }

                            state["signals"].append(
                                f"🚀 BUY {symbol} @ {round(price,4)}"
                            )

                    # EXIT
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
                                f"💥 SELL {symbol} | {round(pnl*100,2)}%"
                            )

                            del state["positions"][symbol]
                            self.adjust_aggression()

                time.sleep(8)

            except Exception as e:
                print("Error:", e)
                time.sleep(5)

# =========================
# WEB UI
# =========================

@app.route("/")
def dashboard():
    total = state["wins"] + state["losses"]
    winrate = round((state["wins"]/total)*100,2) if total > 0 else 0

    return render_template_string("""
    <html>
    <head>
        <title>🔥 Aggressive AI Trader</title>
        <style>
            body {
                background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
                font-family: Arial;
                color: white;
                padding: 20px;
            }
            .card {
                background: rgba(255,255,255,0.08);
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 20px;
            }
            h1 { color: orange; }
        </style>
    </head>
    <body>
        <h1>🔥 Aggressive AI Trader</h1>

        <div class="card">
            <h2>Account</h2>
            Balance: ${{balance}}<br>
            Trades: {{trades}}<br>
            Wins: {{wins}}<br>
            Losses: {{losses}}<br>
            Win Rate: {{winrate}}%<br>
            Aggression: {{aggression}}%
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            {% for s in positions %}
                {{s}}<br>
            {% else %}
                None
            {% endfor %}
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {% for sig in signals[-10:] %}
                {{sig}}<br>
            {% endfor %}
        </div>

    </body>
    </html>
    """,
    balance=round(state["balance"],2),
    trades=state["trades"],
    wins=state["wins"],
    losses=state["losses"],
    winrate=winrate,
    aggression=round(state["aggression"]*100,1),
    positions=state["positions"],
    signals=state["signals"]
    )

# =========================
# START THREAD
# =========================

def start_trader():
    trader = Trader()
    trader.run()

threading.Thread(target=start_trader, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)