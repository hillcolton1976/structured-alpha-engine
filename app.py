from flask import Flask, render_template
import requests
from datetime import datetime

app = Flask(__name__)

KRAKEN_URL = "https://api.kraken.com/0/public/Ticker"

# Coins we want to track
COINS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD",
    "ADAUSD", "DOTUSD", "LINKUSD",
    "AVAXUSD", "LTCUSD", "BCHUSD"
]

def clean_symbol(pair):
    return pair.replace("USD", "").replace("XBT", "BTC")

def get_market_data():
    try:
        pairs = ",".join(COINS)
        response = requests.get(f"{KRAKEN_URL}?pair={pairs}", timeout=10)
        data = response.json()["result"]

        market = []

        for pair in data:
            price = float(data[pair]["c"][0])
            vwap = float(data[pair]["p"][1]) if float(data[pair]["p"][1]) != 0 else price

            # Long-term strength logic
            score = ((price - vwap) / vwap) * 100

            if score > 5:
                strength = "STRONG"
            elif score > -5:
                strength = "ACCUMULATION"
            else:
                strength = "WEAK"

            market.append({
                "coin": clean_symbol(pair),
                "price": round(price, 2),
                "score": round(score, 2),
                "strength": strength
            })

        # Sort strongest first
        market.sort(key=lambda x: x["score"], reverse=True)

        return market

    except Exception as e:
        print("ERROR:", e)
        return []

@app.route("/")
def home():
    market = get_market_data()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return render_template("index.html", market=market, now=now)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)