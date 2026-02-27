from flask import Flask, render_template
import requests
import datetime
import statistics

app = Flask(__name__)

COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "DOT", "LINK", "LTC", "BCH"]

def get_market_data(symbol):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
    response = requests.get(url)
    data = response.json()

    price = float(data["lastPrice"])
    change = float(data["priceChangePercent"])

    return price, change


def detect_market_regime(btc_change):
    if btc_change > 1:
        return "BULL"
    elif btc_change < -1:
        return "BEAR"
    else:
        return "NEUTRAL"


def generate_signal(score, change, regime, volatility):

    signal_score = 0

    # Regime weight
    if regime == "BULL":
        signal_score += 2
    elif regime == "BEAR":
        signal_score -= 2

    # Momentum weight
    if change > 2:
        signal_score += 2
    elif change > 0.5:
        signal_score += 1
    elif change < -2:
        signal_score -= 2
    elif change < -0.5:
        signal_score -= 1

    # Strength weight
    if score > 50:
        signal_score += 2
    elif score > 20:
        signal_score += 1
    elif score < 0:
        signal_score -= 1

    # Volatility penalty
    if volatility > 5:
        signal_score -= 1

    if signal_score >= 4:
        return "BUY", "High"
    elif signal_score >= 2:
        return "BUY", "Medium"
    elif signal_score <= -4:
        return "SELL", "High"
    elif signal_score <= -2:
        return "SELL", "Medium"
    else:
        return "HOLD", "Low"


@app.route("/")
def index():

    btc_price, btc_change = get_market_data("BTC")
    regime = detect_market_regime(btc_change)

    coins_data = []

    for coin in COINS:

        price, change = get_market_data(coin)

        # Simple strength model
        score = change * 10

        volatility = abs(change)

        signal, confidence = generate_signal(score, change, regime, volatility)

        # Risk Level
        if volatility > 5:
            risk = "High"
        elif volatility > 2:
            risk = "Medium"
        else:
            risk = "Low"

        # Entry + Take Profit Zones
        entry = round(price * 0.97, 2)
        take_profit = round(price * 1.10, 2)

        # Position sizing
        if confidence == "High":
            size = "10%"
        elif confidence == "Medium":
            size = "5%"
        else:
            size = "2%"

        coins_data.append({
            "coin": coin,
            "price": round(price, 2),
            "score": round(score, 2),
            "signal": signal,
            "confidence": confidence,
            "entry": entry,
            "take_profit": take_profit,
            "risk": risk,
            "size": size
        })

    updated = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    return render_template("index.html",
                           coins=coins_data,
                           regime=regime,
                           updated=updated)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)