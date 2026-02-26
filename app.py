from flask import Flask, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

TICKER_API = "https://api.kraken.com/0/public/Ticker"
ASSET_PAIRS_API = "https://api.kraken.com/0/public/AssetPairs"


# -------------------------
# Get USD Crypto Pairs (LIMITED)
# -------------------------
def get_usd_pairs(limit=120):
    try:
        response = requests.get(ASSET_PAIRS_API, timeout=10)
        data = response.json().get("result", {})
    except:
        return []

    usd_pairs = []

    for pair_name, details in data.items():
        if details.get("quote") == "ZUSD":
            usd_pairs.append(pair_name)

    return usd_pairs[:limit]   # LIMIT TO SAFE SIZE


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

        try:
            response = requests.get(
                f"{TICKER_API}?pair={pairs_string}",
                timeout=10
            )
            data = response.json().get("result", {})
        except:
            continue

        for pair, ticker in data.items():

            try:
                price = float(ticker["c"][0])
                vwap_24h = float(ticker["p"][1])
                volume_24h = float(ticker["v"][1])
                low_24h = float(ticker["l"][1])
                high_24h = float(ticker["h"][1])
            except:
                continue

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

    market_sorted = sorted(market, key=lambda x: x["score"], reverse=True)

    top_30 = market_sorted[:30]
    all_sells = [m for m in market if m["action"] in ["SELL", "STRONG SELL"]]

    html = """
    <h1>🚀 Kraken Market Scanner</h1>
    <p>Updated: {{ time }}</p>

    <h2>🔥 Top 30 Strongest</h2>
    <table border=1 cellpadding=6>
    <tr>
        <th>Pair</th><th>Price</th><th>24h %</th><th>Score</th><th>Action</th>
    </tr>
    {% for coin in top %}
    <tr>
        <td>{{ coin.pair }}</td>
        <td>{{ coin.price }}</td>
        <td>{{ coin.change }}%</td>
        <td>{{ coin.score }}</td>
        <td>{{ coin.action }}</td>
    </tr>
    {% endfor %}
    </table>

    <h2>📉 All SELL Signals</h2>
    <table border=1 cellpadding=6>
    <tr>
        <th>Pair</th><th>Price</th><th>24h %</th><th>Score</th><th>Action</th>
    </tr>
    {% for coin in sells %}
    <tr>
        <td>{{ coin.pair }}</td>
        <td>{{ coin.price }}</td>
        <td>{{ coin.change }}%</td>
        <td>{{ coin.score }}</td>
        <td>{{ coin.action }}</td>
    </tr>
    {% endfor %}
    </table>
    """

    return render_template_string(
        html,
        time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        top=top_30,
        sells=all_sells
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)