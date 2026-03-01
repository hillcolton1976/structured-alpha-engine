import requests
import time
import random
from flask import Flask

app = Flask(__name__)

STARTING_BALANCE = 50.0
cash = STARTING_BALANCE
positions = {}
trade_history = []

level = 1
wins = 0
losses = 0
trades = 0

MIN_HOLD_TIME = 600
TRADE_COOLDOWN = 180
CONFIDENCE_THRESHOLD = 0.65
last_trade_time = 0

# -------------------------
# MARKET DATA
# -------------------------

def get_market():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 35,
            "page": 1,
            "sparkline": False
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        return data
    except:
        return []

# -------------------------
# SIGNAL ENGINE
# -------------------------

def analyze_coin(coin):
    change = coin.get("price_change_percentage_24h") or 0
    volume = coin.get("total_volume") or 0

    momentum_score = 0

    if change > 2:
        momentum_score += 0.4
    if change > 5:
        momentum_score += 0.3
    if volume > 500000000:
        momentum_score += 0.2

    noise = random.uniform(0, 0.2)

    confidence = momentum_score + noise
    return confidence

# -------------------------
# LEVEL SYSTEM
# -------------------------

def update_level(total_equity):
    global level

    win_rate = wins / trades if trades > 0 else 0

    if total_equity > 60 and win_rate > 0.55:
        level = 2
    if total_equity > 75 and win_rate > 0.6:
        level = 3
    if total_equity > 100 and win_rate > 0.65:
        level = 4

# -------------------------
# TRADING ENGINE
# -------------------------

def trade_logic():
    global cash, trades, wins, losses, last_trade_time

    market = get_market()
    if not market:
        return

    now = time.time()

    for coin in market:
        symbol = coin["symbol"].upper()
        price = coin["current_price"]

        # Skip invalid price
        if not price or price <= 0:
            continue

        # EXIT LOGIC
        if symbol in positions:
            position = positions[symbol]
            hold_time = now - position["entry_time"]

            if hold_time < MIN_HOLD_TIME:
                continue

            pnl = (price - position["entry_price"]) / position["entry_price"]

            if pnl > 0.04 or pnl < -0.03:
                cash += position["amount"] * price
                trades += 1
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                del positions[symbol]
                last_trade_time = now

        # ENTRY LOGIC
        else:
            if now - last_trade_time < TRADE_COOLDOWN:
                continue

            confidence = analyze_coin(coin)

            if confidence > CONFIDENCE_THRESHOLD and cash > 5:
                allocation = 0.1 * level
                size = cash * allocation

                amount = size / price

                positions[symbol] = {
                    "entry_price": price,
                    "amount": amount,
                    "entry_time": now
                }

                cash -= size
                last_trade_time = now

# -------------------------
# DASHBOARD
# -------------------------

@app.route("/")
def dashboard():
    global cash

    trade_logic()

    total_positions_value = 0
    market = get_market()
    price_lookup = {c["symbol"].upper(): c["current_price"] for c in market}

    for symbol, position in positions.items():
        current_price = price_lookup.get(symbol, 0)
        total_positions_value += position["amount"] * current_price

    total_equity = cash + total_positions_value
    update_level(total_equity)

    win_rate = round((wins / trades) * 100, 2) if trades > 0 else 0

    html = f"""
    <h1>ELITE AI TRADER LIVE SIM</h1>
    <h2>Level: {level}</h2>
    <h3>Total Equity: ${round(total_equity,2)}</h3>
    <h3>Cash: ${round(cash,2)}</h3>
    <h3>In Positions: ${round(total_positions_value,2)}</h3>
    <h3>Trades: {trades}</h3>
    <h3>Wins: {wins}</h3>
    <h3>Losses: {losses}</h3>
    <h3>Win Rate: {win_rate}%</h3>
    <hr>
    <h2>Open Positions</h2>
    """

    for symbol, position in positions.items():
        html += f"<p>{symbol} — Entry: ${position['entry_price']}</p>"

    return html