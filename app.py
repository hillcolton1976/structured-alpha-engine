from flask import Flask, render_template
import requests
import time
import threading
import random
import math

app = Flask(__name__)

engine = {
    "balance": 50.0,
    "peak_balance": 50.0,
    "level": 1,
    "roi": 0,
    "wins": 0,
    "losses": 0,
    "total_trades": 0,
    "current_symbol": None,
    "entry_price": 0,
    "position_size": 0,
    "last_action": "WAITING",
    "recent_trades": []
}

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]

def get_price(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(requests.get(url).json()["price"])

def get_klines(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=30"
    data = requests.get(url).json()
    closes = [float(candle[4]) for candle in data]
    return closes

def calculate_rsi(closes, period=14):
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def score_coin(symbol):
    closes = get_klines(symbol)
    rsi = calculate_rsi(closes)
    momentum = (closes[-1] - closes[-5]) / closes[-5]
    volatility = abs(closes[-1] - closes[-10]) / closes[-10]
    score = (50 - abs(rsi - 50)) + (momentum * 200)
    return score, rsi, volatility

def update_level():
    if engine["balance"] >= 200:
        engine["level"] = 2
    if engine["balance"] >= 1000:
        engine["level"] = 3
    if engine["balance"] >= 5000:
        engine["level"] = 4

def trading_loop():
    while True:
        try:
            best_symbol = None
            best_score = -999
            best_rsi = 50
            best_vol = 0

            for symbol in symbols:
                score, rsi, vol = score_coin(symbol)
                if score > best_score:
                    best_score = score
                    best_symbol = symbol
                    best_rsi = rsi
                    best_vol = vol

            drawdown = (engine["peak_balance"] - engine["balance"]) / engine["peak_balance"]

            base_risk = 0.10
            if drawdown > 0.10:
                base_risk = 0.05
            if drawdown > 0.20:
                base_risk = 0.02

            volatility_adjustment = max(0.5, 1 - best_vol)
            risk_percent = base_risk * volatility_adjustment

            if engine["current_symbol"] is None and best_rsi < 40:
                engine["current_symbol"] = best_symbol
                engine["entry_price"] = get_price(best_symbol)
                engine["position_size"] = engine["balance"] * risk_percent
                engine["last_action"] = f"BUY {best_symbol}"

            elif engine["current_symbol"] is not None:
                current_price = get_price(engine["current_symbol"])
                change = (current_price - engine["entry_price"]) / engine["entry_price"]

                if best_rsi > 60 or change > 0.01 or change < -0.02:
                    profit = engine["position_size"] * change
                    engine["balance"] += profit
                    engine["total_trades"] += 1

                    if profit > 0:
                        engine["wins"] += 1
                        result = "WIN"
                    else:
                        engine["losses"] += 1
                        result = "LOSS"

                    engine["recent_trades"].insert(0, {
                        "symbol": engine["current_symbol"],
                        "result": result,
                        "balance": round(engine["balance"], 2)
                    })

                    engine["current_symbol"] = None
                    engine["last_action"] = f"SELL {result}"

            if engine["balance"] > engine["peak_balance"]:
                engine["peak_balance"] = engine["balance"]

            engine["roi"] = round(((engine["balance"] - 50) / 50) * 100, 2)

            update_level()

        except:
            pass

        time.sleep(15)

@app.route("/")
def dashboard():
    win_rate = 0
    if engine["total_trades"] > 0:
        win_rate = round((engine["wins"] / engine["total_trades"]) * 100, 2)

    max_dd = round((engine["peak_balance"] - engine["balance"]) / engine["peak_balance"] * 100, 2)

    return render_template("dashboard.html",
        balance=round(engine["balance"],2),
        roi=engine["roi"],
        level=engine["level"],
        last_action=engine["last_action"],
        total_trades=engine["total_trades"],
        win_rate=win_rate,
        total_profit=round(engine["balance"] - 50,2),
        max_drawdown=max_dd,
        trades=engine["recent_trades"][:15]
    )

if __name__ == "__main__":
    threading.Thread(target=trading_loop).start()
    app.run(host="0.0.0.0", port=5000)