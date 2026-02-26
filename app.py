from flask import Flask, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

TICKER_API = "https://api.kraken.com/0/public/Ticker"
ASSET_PAIRS_API = "https://api.kraken.com/0/public/AssetPairs"


# -------------------------
# Get All USD Crypto Pairs
# -------------------------
def get_usd_pairs():
    response = requests.get(ASSET_PAIRS_API)
    data = response.json().get("result", {})

    usd_pairs = []

    for pair_name, details in data.items():
        if details.get("quote") == "ZUSD":
            if details.get("wsname"):
                usd_pairs.append(pair_name)

    return usd_pairs


# -------------------------
# Scoring Engine
# -------------------------
def score_market():

    pairs = get_usd_pairs()
    batch_size = 20
    results = []

    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i+batch_size]
        pairs_string = ",".join(batch)

        response = requests.get(f"{TICKER_API}?pair={pairs_string}")
        data = response.json().get("result", {})

        for pair, ticker in data.items():

            try:
                price = float(ticker["c"][0])
                vwap_24h = float(ticker["p"][1])
                volume_24h = float(ticker["v"][1])
                low_24h = float(ticker["l"][1])
                high_24h = float(ticker["h"][1])
            except:
                continue

            # 🔒 Prevent division by zero (fixes 500 error)
            if vwap_24h == 0 or high_24h == low_24h:
                continue

            change_percent = ((price - vwap_24h) / vwap_24h) * 100
            range_position = (price - low_24h) / (high_24h - low_24h)

            score = 0

            # Momentum
            if change_percent > 2:
                score += 2
            elif change_percent < -2:
                score -= 2

            # VWAP Trend
            if price > vwap_24h:
                score += 1
            else:
                score -= 1

            # Daily range position
            if range_position > 0.75:
                score += 1
            elif range_position < 0.25:
                score -= 1

            # Volume strength
            if volume_24h > 1_000_000:
                score += 1

            # Action mapping
            if score >= 4:
                action = "STRONG BUY"
            elif score >= 2:
                action = "BUY"
            elif score <= -4:
                action = "STRONG SELL"
            elif score <= -2:
                action = "SELL"
            else:
                action = "HOLD"

            results.append({
                "pair": pair,
                "price": round(price, 6),
                "change": round(change_percent, 2),
                "score": score,
                "action": action
            })

    return results


# -------------------------
# Route
# -------------------------
@app.route("/")
def home():

    market = score_market()

    # Sort strongest first
    market_sorted = sorted(market, key=lambda x: x["score"], reverse=True)

    top_30 = market_sorted[:30]
    all_sells = [m for m in market if m["action"] in ["SELL", "STRONG SELL"]]

    html = """
    <html>
    <head>
        <title>Kraken Market Scanner</title>
        <style>
            body { font-family: Arial; background: #111; color: white; padding: 20px; }
            h1 { color: #00ffcc; }
            table { border-collapse: collapse; margin-bottom: 40px; }
            th, td { padding: 8px 12px; border: 1px solid #333; }
            th { background: #222; }
            .BUY { color: #00ff00; font-weight: bold; }
            .STRONGBUY { color: #00ff88; font-weight: bold; }
            .SELL { color: #ff4444; font-weight: bold; }
            .STRONGSELL { color: #ff0000; font-weight: bold; }
            .HOLD { color: #cccccc; }
        </style>
    </head>
    <body>

    <h1>🚀 Kraken Market Scanner</h1>
    <p>Updated: {{ time }}</p>

    <h2>🔥 Top 30 Strongest</h2>
    <table>
        <tr>
            <th>Pair</th><th>Price</th><th>24h %</th><th>Score</th><th>Action</th>
        </tr>
        {% for coin in top %}
        <tr>
            <td>{{ coin.pair }}</td>
            <td>{{ coin.price }}</td>
            <td>{{ coin.change }}%</td>
            <td>{{ coin.score }}</td>
            <td class="{{ coin.action.replace(' ', '') }}">{{ coin.action }}</td>
        </tr>
        {% endfor %}
    </table>

    <h2>📉 All SELL Signals</h2>
    <table>
        <tr>
            <th>Pair</th><th>Price</th><th>24h %</th><th>Score</th><th>Action</th>
        </tr>
        {% for coin in sells %}
        <tr>
            <td>{{ coin.pair }}</td>
            <td>{{ coin.price }}</td>
            <td>{{ coin.change }}%</td>
            <td>{{ coin.score }}</td>
            <td class="{{ coin.action.replace(' ', '') }}">{{ coin.action }}</td>
        </tr>
        {% endfor %}
    </table>

    </body>
    </html>
    """

    return render_template_string(
        html,
        time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        top=top_30,
        sells=all_sells
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)