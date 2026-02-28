import threading
import time
import requests
import statistics
from flask import Flask, render_template_string

app = Flask(__name__)

# ===== CONFIG =====
START_BALANCE = 50.0
SCAN_INTERVAL = 8
MAX_POSITIONS = 3
MAX_CAPITAL_USE = 0.30
BASE_AGGRESSION = 0.18

balance = START_BALANCE
equity = START_BALANCE
peak_equity = START_BALANCE
drawdown = 0

wins = 0
losses = 0
trades = 0
losing_streak = 0

AGGRESSION = BASE_AGGRESSION
TAKE_PROFIT_MULT = 1.6
STOP_LOSS_MULT = 1.1

positions = {}
price_history = {}
coins = []
recent_signals = []
last_scan = 0


# ===== API =====
def get_pairs():
    try:
        data = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
        usdt = [x for x in data if x["symbol"].endswith("USDT")]
        sorted_pairs = sorted(usdt, key=lambda x: abs(float(x["priceChangePercent"])), reverse=True)
        return [x["symbol"] for x in sorted_pairs[:20]]
    except:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def get_price(symbol):
    try:
        data = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}").json()
        return float(data["price"])
    except:
        return None


# ===== INDICATORS =====
def EMA(prices, period):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p * k + ema * (1 - k)
    return ema


def RSI(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, -1):
        diff = prices[i+1] - prices[i]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    avg_gain = sum(gains)/period if gains else 0
    avg_loss = sum(losses)/period if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100/(1+rs))


def ATR(prices, period=14):
    if len(prices) < period:
        return None
    return sum(abs(prices[i] - prices[i-1]) for i in range(-period, 0)) / period


# ===== MARKET MODE =====
def detect_regime(prices):
    if len(prices) < 30:
        return "CHOP"
    trend_strength = abs(EMA(prices[-20:], 20) - EMA(prices[-50:], 50))
    volatility = ATR(prices)
    if trend_strength and volatility and trend_strength > volatility:
        return "TREND"
    return "CHOP"


# ===== AI ENGINE =====
def trader():
    global balance, equity, wins, losses, trades
    global AGGRESSION, TAKE_PROFIT_MULT, STOP_LOSS_MULT
    global peak_equity, drawdown, losing_streak
    global coins, last_scan

    while True:
        try:
            now = time.time()

            if now - last_scan > 900:
                coins = get_pairs()
                last_scan = now

            # Update prices
            for coin in coins:
                price = get_price(coin)
                if not price:
                    continue
                price_history.setdefault(coin, []).append(price)
                if len(price_history[coin]) > 120:
                    price_history[coin].pop(0)

            # ENTRY LOGIC
            if len(positions) < MAX_POSITIONS:
                capital_in_use = sum(p["size"] for p in positions.values())
                available_capital = balance * MAX_CAPITAL_USE - capital_in_use

                for coin in coins:
                    if coin in positions:
                        continue
                    prices = price_history.get(coin, [])
                    if len(prices) < 40:
                        continue

                    regime = detect_regime(prices)
                    ema12 = EMA(prices[-12:], 12)
                    ema26 = EMA(prices[-26:], 26)
                    rsi = RSI(prices)
                    atr = ATR(prices)

                    if not all([ema12, ema26, rsi, atr]):
                        continue

                    breakout = prices[-1] > max(prices[-5:-1])

                    if regime == "TREND":
                        condition = ema12 > ema26 and rsi < 70 and breakout
                    else:
                        condition = rsi < 40 and breakout

                    if condition and available_capital > 5:
                        size = balance * AGGRESSION
                        balance -= size
                        positions[coin] = {
                            "entry": prices[-1],
                            "size": size,
                            "atr": atr
                        }
                        recent_signals.insert(0, f"🚀 BUY {coin}")
                        break

            # EXIT LOGIC
            for coin in list(positions.keys()):
                prices = price_history.get(coin, [])
                if not prices:
                    continue

                current = prices[-1]
                entry = positions[coin]["entry"]
                size = positions[coin]["size"]
                atr = positions[coin]["atr"]

                change = (current - entry) / entry
                tp = (atr/entry) * TAKE_PROFIT_MULT
                sl = (atr/entry) * STOP_LOSS_MULT

                if change >= tp or change <= -sl:
                    result = size * change
                    balance += size + result
                    trades += 1

                    if result > 0:
                        wins += 1
                        losing_streak = 0
                        recent_signals.insert(0, f"✅ SELL {coin} +{result:.2f}")
                    else:
                        losses += 1
                        losing_streak += 1
                        recent_signals.insert(0, f"❌ SELL {coin} {result:.2f}")

                    del positions[coin]

            # EQUITY
            equity = balance
            for coin, data in positions.items():
                current = price_history[coin][-1]
                equity += data["size"] + (data["size"] * ((current - data["entry"]) / data["entry"]))

            # Drawdown
            peak_equity = max(peak_equity, equity)
            drawdown = (peak_equity - equity) / peak_equity

            # Adaptive Learning
            if trades > 0 and trades % 5 == 0:
                winrate = wins / trades

                if winrate > 0.6:
                    AGGRESSION = min(0.35, AGGRESSION + 0.04)
                    TAKE_PROFIT_MULT += 0.1
                else:
                    AGGRESSION = max(0.10, AGGRESSION - 0.04)
                    STOP_LOSS_MULT += 0.1

            # Cooldown Protection
            if drawdown > 0.15 or losing_streak >= 3:
                AGGRESSION = max(0.10, AGGRESSION - 0.05)

        except Exception as e:
            print("ERROR:", e)

        time.sleep(SCAN_INTERVAL)


threading.Thread(target=trader, daemon=True).start()


@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
    <title>Elite AI Trader</title>
    <style>
        body {
            background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
            font-family: Arial;
            color: white;
            padding: 40px;
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
        <h1>🔥 ELITE AI TRADER</h1>

        <div class="card">
            <h2>Account</h2>
            <p><b>Equity:</b> ${{equity}}</p>
            <p><b>Balance:</b> ${{balance}}</p>
            <p><b>Trades:</b> {{trades}}</p>
            <p><b>Wins:</b> {{wins}}</p>
            <p><b>Losses:</b> {{losses}}</p>
            <p><b>Win Rate:</b> {{winrate}}%</p>
            <p><b>Drawdown:</b> {{drawdown}}%</p>
            <p><b>Aggression:</b> {{aggression}}%</p>
        </div>

        <div class="card">
            <h2>Open Positions</h2>
            {% for p in positions %}
                <p>{{p}}</p>
            {% endfor %}
        </div>

        <div class="card">
            <h2>Recent Signals</h2>
            {% for s in signals %}
                <p>{{s}}</p>
            {% endfor %}
        </div>
    </body>
    </html>
    """,
    equity=round(equity,2),
    balance=round(balance,2),
    trades=trades,
    wins=wins,
    losses=losses,
    winrate=round((wins/trades*100),2) if trades>0 else 0,
    drawdown=round(drawdown*100,2),
    aggression=round(AGGRESSION*100,1),
    positions=list(positions.keys()) if positions else ["None"],
    signals=recent_signals[:10]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)