import requests
import threading
import time
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

# =========================
# ENGINE STATE
# =========================

engine = {
    "balance": 50.0,
    "start_balance": 50.0,
    "positions": [],
    "max_positions": 3,
    "risk_per_trade": 0.10,  # 10% risk
    "recent_trades": [],
    "peak_balance": 50.0,
}

# =========================
# BINANCE HELPERS
# =========================

def get_top_50_symbols():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    data = requests.get(url).json()
    usdt_pairs = [d for d in data if d["symbol"].endswith("USDT")]
    sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [d["symbol"] for d in sorted_pairs[:50]]

def get_klines(symbol, interval="5m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data)
    df = df.iloc[:, :6]
    df.columns = ["time","open","high","low","close","volume"]
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df

# =========================
# INDICATORS
# =========================

def calculate_rsi(df, period=14):
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(df, span=9):
    return df["close"].ewm(span=span, adjust=False).mean()

# =========================
# ENTRY LOGIC
# =========================

def check_entry(symbol):
    df = get_klines(symbol)
    if len(df) < 50:
        return None

    df["rsi"] = calculate_rsi(df)
    df["ema"] = calculate_ema(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Breakout Long
    if last["close"] > prev["high"] and last["rsi"] > 55:
        return ("LONG", last["close"])

    # Breakdown Short
    if last["close"] < prev["low"] and last["rsi"] < 45:
        return ("SHORT", last["close"])

    return None

# =========================
# EXIT LOGIC (2 CONFIRMATION)
# =========================

def check_exit(position):
    df = get_klines(position["symbol"])
    df["rsi"] = calculate_rsi(df)
    df["ema"] = calculate_ema(df)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    confirmations = 0

    # Momentum reversal
    if position["side"] == "LONG" and last["rsi"] < prev["rsi"]:
        confirmations += 1
    if position["side"] == "SHORT" and last["rsi"] > prev["rsi"]:
        confirmations += 1

    # Structure break
    if position["side"] == "LONG" and last["close"] < last["ema"]:
        confirmations += 1
    if position["side"] == "SHORT" and last["close"] > last["ema"]:
        confirmations += 1

    return confirmations >= 2, last["close"]

# =========================
# TRADING LOOP
# =========================

def trading_loop():
    while True:
        try:
            symbols = get_top_50_symbols()

            # ENTRY
            for symbol in symbols:
                if len(engine["positions"]) >= engine["max_positions"]:
                    break

                if any(p["symbol"] == symbol for p in engine["positions"]):
                    continue

                entry = check_entry(symbol)
                if entry:
                    side, price = entry
                    risk_amount = engine["balance"] * engine["risk_per_trade"]
                    position_size = risk_amount

                    engine["positions"].append({
                        "symbol": symbol,
                        "side": side,
                        "entry": price,
                        "size": position_size
                    })

            # EXIT
            for position in engine["positions"][:]:
                should_exit, exit_price = check_exit(position)
                if should_exit:
                    if position["side"] == "LONG":
                        pnl = (exit_price - position["entry"]) / position["entry"]
                    else:
                        pnl = (position["entry"] - exit_price) / position["entry"]

                    profit = position["size"] * pnl
                    engine["balance"] += profit
                    engine["recent_trades"].append({
                        "symbol": position["symbol"],
                        "side": position["side"],
                        "pnl": round(profit, 2)
                    })
                    engine["positions"].remove(position)

                    if engine["balance"] > engine["peak_balance"]:
                        engine["peak_balance"] = engine["balance"]

            time.sleep(30)

        except Exception as e:
            print("Error:", e)
            time.sleep(10)

# =========================
# DASHBOARD
# =========================

@app.route("/")
def dashboard():
    roi = ((engine["balance"] - engine["start_balance"]) / engine["start_balance"]) * 100
    drawdown = ((engine["peak_balance"] - engine["balance"]) / engine["peak_balance"]) * 100

    return render_template(
        "dashboard.html",
        balance=round(engine["balance"], 2),
        roi=round(roi, 2),
        drawdown=round(drawdown, 2),
        trades=len(engine["recent_trades"]),
        open_positions=engine["positions"],
        recent_trades=engine["recent_trades"][-15:]
    )

# =========================
# START THREAD
# =========================

threading.Thread(target=trading_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)