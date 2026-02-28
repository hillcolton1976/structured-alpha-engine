from flask import Flask, render_template_string
import ccxt
import pandas as pd
import time

app = Flask(__name__)

# ================= CONFIG =================

TIMEFRAME = '1m'
CANDLE_LIMIT = 80
START_BALANCE = 50.0
MAX_POSITIONS = 2
POSITION_SIZE = 0.50
SCAN_INTERVAL = 20
TRAILING_STOP = 0.975

SYMBOLS = [
'ETH/USDT','SOL/USDT','XRP/USDT','ADA/USDT',
'AVAX/USDT','LINK/USDT','BNB/USDT','DOGE/USDT','MATIC/USDT',
'ATOM/USDT','NEAR/USDT','ARB/USDT','OP/USDT','INJ/USDT',
'APT/USDT','SUI/USDT','LTC/USDT','FIL/USDT','RNDR/USDT'
]

BTC_SYMBOL = 'BTC/USDT'

exchange = ccxt.coinbase()

# ================= STATE =================

balance = START_BALANCE
positions = {}
total_trades = 0
wins = 0
losses = 0
last_action = "Booting..."
recent_signals = []
last_scan_time = 0

# ================= INDICATORS =================

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_data(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME