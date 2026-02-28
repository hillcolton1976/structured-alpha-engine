import ccxt
import pandas as pd
import numpy as np
import time
import threading
from flask import Flask

# ================================
# CONFIG
# ================================

TIMEFRAME = '3m'
START_BALANCE = 1000
MAX_COINS = 8
RISK_PER_TRADE = 0.10
SLEEP_SECONDS = 20

# ================================
# WEB APP
# ================================

app = Flask(__name__)

@app.route("/")
def home():
    return "🔥 AGGRESSIVE AI SIM TRADER RUNNING 🔥"

# ================================
# TRADER ENGINE
# ================================

class Trader:
    def __init__(self):
        self.exchange = ccxt.binanceus()
        self.balance = START_BALANCE
        self.open_positions = []
        self.symbols = []
        self.score_threshold = 3

    def get_symbols(self):
        markets = self.exchange.load_markets()
        pairs = [
            s for s in markets
            if '/USDT' in s and markets[s]['active']
        ]
        return pairs[:MAX_COINS]

    def fetch_data(self, symbol):
        ohlcv = self.exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
        return df

    def score(self, df):
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        score = 0
        if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
            score += 1
        if df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1]:
            score += 1
        return score, df['close'].iloc[-1]

    def run(self):
        print("🔥 Trader Started")

        try:
            self.symbols = self.get_symbols()
            print("Monitoring:", self.symbols)
        except Exception as e:
            print("Market load error:", e)
            return

        while True:
            try:
                for symbol in self.symbols:
                    df = self.fetch_data(symbol)
                    score, price = self.score(df)

                    if score >= self.score_threshold:
                        print(f"🚀 Signal on {symbol} @ {price}")

                time.sleep(SLEEP_SECONDS)

            except Exception as e:
                print("Loop error:", e)
                time.sleep(5)

# ================================
# START BACKGROUND TRADER
# ================================

def start_trader():
    trader = Trader()
    trader.run()

threading.Thread(target=start_trader, daemon=True).start()

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)