# config.py

# Kraken API keys (for future real trading)
API_KEY = "YOUR_KRAKEN_API_KEY"
API_SECRET = "YOUR_KRAKEN_API_SECRET"

# Bot settings
COINS = ["DOGE", "XRP", "BTC"]
PAIR_MAP = {"DOGE": "DOGEUSD", "XRP": "XRPUSD", "BTC": "XBTUSD"}

# Trading parameters
BUY_PERCENT = 0.2       # 20% of USD balance per buy
PROFIT_TARGET = 1.02    # 2% profit target
STOP_LOSS = 0.98        # 2% stop loss

RSI_PERIOD = 14
EMA_SHORT = 50
EMA_LONG = 200