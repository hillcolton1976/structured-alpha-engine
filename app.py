import ccxt
import pandas as pd
import numpy as np
import time
import random
from collections import deque

# ================================
# CONFIG
# ================================

TIMEFRAME = '3m'
START_BALANCE = 1000
MAX_COINS = 12
RISK_PER_TRADE = 0.10        # 10% per trade (aggressive)
AI_ADJUST_EVERY = 20         # learn every 20 trades
SLEEP_SECONDS = 20

# ================================
# EXCHANGE (PUBLIC DATA ONLY)
# ================================

exchange = ccxt.binanceus()

# ================================
# AI PARAMETERS (SELF TUNING)
# ================================

class Brain:
    def __init__(self):
        self.score_threshold = 3
        self.rsi_low = 35
        self.tp_mult = 1.5
        self.sl_mult = 1.0
        self.trade_history = deque(maxlen=AI_ADJUST_EVERY)

    def learn(self):
        if len(self.trade_history) < AI_ADJUST_EVERY:
            return
        
        wins = sum(1 for t in self.trade_history if t > 0)
        win_rate = wins / len(self.trade_history)

        print("\n🧠 AI LEARNING PHASE")
        print("Win Rate:", round(win_rate * 100, 2), "%")

        if win_rate < 0.45:
            self.score_threshold += 0.5
            self.rsi_low -= 2
            self.tp_mult += 0.1
            print("AI: Tightening entries")

        elif win_rate > 0.60:
            self.score_threshold -= 0.5
            self.rsi_low += 2
            self.tp_mult -= 0.1
            print("AI: Increasing aggression")

        self.trade_history.clear()

brain = Brain()

# ================================
# HELPERS
# ================================

def get_top_symbols():
    markets = exchange.load_markets()
    pairs = [
        s for s in markets 
        if '/USDT' in s and markets[s]['active']
    ]
    return pairs[:MAX_COINS]

def fetch_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=120)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    return df

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def score_signal(df):
    df['rsi'] = rsi(df['close'])
    df['ema9'] = df['close'].ewm(span=9).mean()
    df['ema21'] = df['close'].ewm(span=21).mean()

    score = 0

    if df['ema9'].iloc[-1] > df['ema21'].iloc[-1]:
        score += 1

    if df['rsi'].iloc[-1] < brain.rsi_low:
        score += 1

    if df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1]:
        score += 1

    momentum = df['close'].pct_change().iloc[-1]
    if momentum > 0:
        score += 1

    return score, df['close'].iloc[-1]

# ================================
# SIMULATION ENGINE
# ================================

balance = START_BALANCE
open_positions = []

def open_trade(symbol, price):
    global balance
    size = balance * RISK_PER_TRADE
    tp = price * (1 + 0.01 * brain.tp_mult)
    sl = price * (1 - 0.01 * brain.sl_mult)

    trade = {
        "symbol": symbol,
        "entry": price,
        "size": size,
        "tp": tp,
        "sl": sl
    }

    open_positions.append(trade)
    print(f"🚀 OPEN {symbol} @ {price:.4f}")

def check_positions():
    global balance
    for trade in open_positions[:]:
        price = exchange.fetch_ticker(trade["symbol"])['last']

        if price >= trade["tp"]:
            profit = trade["size"] * 0.01 * brain.tp_mult
            balance += profit
            brain.trade_history.append(1)
            print(f"✅ TP HIT {trade['symbol']} +${profit:.2f}")
            open_positions.remove(trade)

        elif price <= trade["sl"]:
            loss = trade["size"] * 0.01 * brain.sl_mult
            balance -= loss
            brain.trade_history.append(-1)
            print(f"❌ SL HIT {trade['symbol']} -${loss:.2f}")
            open_positions.remove(trade)

# ================================
# MAIN LOOP
# ================================

symbols = get_top_symbols()

print("\n🔥 AGGRESSIVE AI SIM MODE ACTIVE")
print("Starting Balance:", balance)
print("Monitoring:", symbols)
print("Timeframe:", TIMEFRAME)

while True:
    try:
        for symbol in symbols:
            df = fetch_data(symbol)
            score, price = score_signal(df)

            if score >= brain.score_threshold and len(open_positions) < 5:
                open_trade(symbol, price)

        check_positions()
        brain.learn()

        print("Balance:", round(balance, 2),
              "| Open:", len(open_positions))

        time.sleep(SLEEP_SECONDS)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)