from flask import Flask, render_template_string
import requests
import threading
import time
from datetime import datetime

app = Flask(__name__)

KRAKEN_TICKER_URL = "https://api.kraken.com/0/public/Ticker"
KRAKEN_ASSETS_URL = "https://api.kraken.com/0/public/AssetPairs"

UPDATE_INTERVAL = 60  # seconds

# In-memory cache
market_cache = {
    "last_update": None,
    "top_30": [],
    "sell_list": [],
    "market_mode": "Loading..."
}

# ----------------------------
# Get All USD Pairs
# ----------------------------
def get_usd_pairs():
    try:
        response = requests.get(KRAKEN_ASSETS_URL, timeout=10)
        data = response.json().get("result", {})

        usd_pairs = []
        for pair_name, details in data.items():
            if details.get("quote") == "ZUSD":
                usd_pairs.append(pair_name)

        return usd_pairs
    except:
        return []

# ----------------------------
# Scoring Logic
# ----------------------------
def score_pair(pair, ticker):

    try:
        price = float(ticker["c"][0])
        vwap_24h = float(ticker["p"][1])
        volume_24h = float(ticker["v"][1])
        low_24h = float(ticker["l"][1])
        high_24h = float(ticker["h"][1])

        if vwap_24h == 0:
            return None

        change_percent = ((price - vwap_24h) / vwap_24h) * 100
        range_position = (price - low_24h) / (high_24h - low_24h + 1e-9)

        score = 0

        if change_percent > 2:
            score += 2
        elif change_percent < -2:
            score -= 2

        if price > vwap_24h:
            score += 1
        else:
            score -= 1

        if range_position > 0.75:
            score += 1
        elif range_position < 0.25:
            score -= 1

        if volume_24h > 1_000_000:
            score += 1

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

        return {
            "pair": pair,
            "price": round(price, 6),
            "change": round(change_percent, 2),
            "score": score,
            "action": action
        }

    except:
        return None

# ----------------------------
# Background Market Updater
# ----------------------------
def market_updater():
    global market_cache

    while True:
        try:
            pairs = get_usd_pairs()
            results = []

            batch_size = 20

            for i in range(0, len(pairs), batch_size):
                batch = pairs[i:i+batch_size]
                pairs_string = ",".join(batch)

                response = requests.get(
                    KRAKEN_TICKER_URL,
                    params={"pair": pairs_string},
                    timeout=10
                )

                data = response.json().get("result", {})

                for pair, ticker in data.items():
                    scored = score_pair(pair, ticker)
                    if scored:
                        results.append(scored)

            # Sort strongest first
            results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)

            top_30 = results_sorted[:30]
            sell_list = [r for r in results if r["action"] in ["SELL", "STRONG SELL"]]

            # Determine market mode from top score average
            avg_score = sum(r["score"] for r in top_30) / max(len(top_30), 1)

            if avg_score > 2:
                market_mode = "🟢 RISK ON"
            elif avg_score < -2:
                market_mode = "🔴 RISK OFF"
            else:
                market_mode = "🟡 NEUTRAL"

            market_cache = {
                "last_update": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "top_30": top_30,
                "sell_list": sell_list,
                "market_mode": market_mode
            }

            print("Market updated successfully")

        except Exception as e:
            print("Update error:", e)

        time.sleep(UPDATE_INTERVAL)

# Start background thread
threading.Thread(target=market_updater, daemon=True).start()

# ----------------------------
# Web Route
# ----------------------------
@app.route("/")
def home():

    html = """
    <html>
    <head>
        <meta http-equiv="refresh" content="60">
        <style>
            body { font-family: Arial; background: #0f172a; color: white; }
            h1 { color: #38bdf8; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }
            th, td { padding: 8px; text-align: center; }
            th { background: #1e293b; }
            tr:nth-child(even) { background: #1e293b; }
            .buy { color: #22c55e; }
            .sell { color: #ef4444; }
            .hold { color: #facc15; }
        </style>
    </head>
    <body>

    <h1>🚀 Kraken Market Scanner</h1>
    <h3>Market Mode: {{ mode }}</h3>
    <p>Last Update: {{ time }}</p>

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
        <td class="{{ coin.action.lower().replace(' ', '') }}">
            {{ coin.action }}
        </td>
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
        <td class="sell">{{ coin.action }}</td>
    </tr>
    {% endfor %}
    </table>

    </body>
    </html>
    """

    return render_template_string(
        html,
        top=market_cache["top_30"],
        sells=market_cache["sell_list"],
        time=market_cache["last_update"],
        mode=market_cache["market_mode"]
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)