import ccxt
import pandas as pd
import numpy as np
import time
from datetime import datetime

# ================= CONFIG =================

API_KEY = "YOUR_API_KEY"
SECRET = "YOUR_SECRET"

exchange = ccxt.binanceus({
    'apiKey': API_KEY,
    'secret': SECRET,
    'enableRateLimit': True
})

TIMEFRAME = '1m'
ROTATION_SIZE = 25
MAX_POSITIONS = 5

STOP_LOSS = -0.006
TAKE_PROFIT = 0.009
TRAIL_TRIGGER = 0.004

BASE_RISK = 0.20  # 20% of balance per trade (VERY AGGRESSIVE)
SLEEP_TIME = 2

# ==========================================

positions = {}
wins = 0
losses = 0
trade_count = 0

def get_top_symbols():
    markets = exchange.load_markets()
    usdt_pairs = [s for s in markets if "/USDT" in s and markets[s]['active']]
    tickers = exchange.fetch_tickers(usdt_pairs)

    sorted_symbols = sorted(
        usdt_pairs,
        key=lambda s: tickers[s]['quoteVolume'] if s in tickers else 0,
        reverse=True
    )

    return sorted_symbols[:50]

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=50)
    df = pd.DataFrame(ohlcv, columns=['t','o','h','l','c','v'])
    df['ema20'] = df['c'].ewm(span=20).mean()
    df['rsi'] = rsi(df['c'])
    return df

def place_market_buy(symbol, size):
    order = exchange.create_market_buy_order(symbol, size)
    return order

def place_market_sell(symbol, size):
    order = exchange.create_market_sell_order(symbol, size)
    return order

def get_balance():
    balance = exchange.fetch_balance()
    return balance['USDT']['free']

def calculate_position_size(symbol):
    balance = get_balance()
    risk_amount = balance * BASE_RISK
    ticker = exchange.fetch_ticker(symbol)
    price = ticker['last']
    size = risk_amount / price
    return round(size, 5)

# ================= MAIN LOOP =================

symbols = get_top_symbols()

print("🔥 Ultra Aggressive Adaptive Trader Started")

while True:

    for symbol in symbols[:ROTATION_SIZE]:

        try:
            df = get_data(symbol)
            last = df.iloc[-1]
            prev = df.iloc[-2]

            momentum = (last['c'] - prev['c']) / prev['c']

            # ENTRY
            if (symbol not in positions and
                len(positions) < MAX_POSITIONS and
                last['rsi'] > 35 and
                last['c'] > last['ema20'] and
                momentum > 0.002):

                size = calculate_position_size(symbol)
                order = place_market_buy(symbol, size)

                positions[symbol] = {
                    'entry': last['c'],
                    'size': size,
                    'trail_active': False
                }

                print(f"{datetime.now()} BUY {symbol} @ {last['c']}")
                trade_count += 1

            # MANAGEMENT
            if symbol in positions:
                entry = positions[symbol]['entry']
                current = last['c']
                change = (current - entry) / entry

                # activate trailing
                if change > TRAIL_TRIGGER:
                    positions[symbol]['trail_active'] = True

                # trailing stop
                if positions[symbol]['trail_active']:
                    STOP = -0.003
                else:
                    STOP = STOP_LOSS

                # exit conditions
                if change <= STOP or change >= TAKE_PROFIT:
                    size = positions[symbol]['size']
                    place_market_sell(symbol, size)

                    if change > 0:
                        wins += 1
                        print(f"{datetime.now()} WIN {symbol} {change*100:.2f}%")
                    else:
                        losses += 1
                        print(f"{datetime.now()} LOSS {symbol} {change*100:.2f}%")

                    del positions[symbol]

        except Exception as e:
            continue

    print(f"Trades: {trade_count} | Wins: {wins} | Losses: {losses}")
    time.sleep(SLEEP_TIME)