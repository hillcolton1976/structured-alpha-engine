from flask import Flask, render_template_string
import requests
from datetime import datetime
import statistics

app = Flask(__name__)

ASSET_PAIRS_API = "https://api.kraken.com/0/public/AssetPairs"
OHLC_API = "https://api.kraken.com/0/public/OHLC"


def get_usd_pairs():
    try:
        response = requests.get(ASSET_PAIRS_API, timeout=10)
        data = response.json().get("result", {})
        return [
            pair for pair, details in data.items()
            if details.get("quote") == "ZUSD"
        ][:25]  # LIMIT to 25 for stability
    except:
        return []


def get_daily_closes(pair):
    try:
        response = requests.get(
            f"{OHLC_API}?pair={pair}&interval=1440",
            timeout=10
        )
        data = response.json().get("result", {})
        if not data:
            return []

        key = list(data.keys())[0]
        candles = data[key]

        closes = [float(c[4]) for c in candles]
        return closes

    except:
        return []


def score_pair(pair):
    closes = get_daily_closes(pair)

    if len(closes) < 200:
        return None

    try:
        price = closes[-1]
        ma50 = statistics.mean(closes[-50:])
        ma200 = statistics.mean(closes[-200:])
        change_90 = ((price - closes[-90]) / closes[-90]) * 100

        score = 0

        if price > ma200:
            score += 2
        if ma50 > ma200:
            score += 2
        if change_90 > 10:
            score += 1

        if score == 5:
            action = "STRONG LONG BUY"
        elif score >= 3:
            action = "LONG BUY"
        elif score >= 1:
            action = "HOLD"
        else:
            action = "AVOID"

        return {
            "pair": pair,
            "price": round(price, 4),
            "score": score,
            "action": action
        }

    except:
        return None


@app.route("/")
def home():

    pairs = get_usd_pairs()
    results = []

    for pair in pairs:
        scored = score_pair(pair)
        if scored:
            results.append(scored)

    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)

    html = """
    <h1>📈 Long-Term Crypto Scanner</h1>
    <p>Updated: {{ time }}</p>

    <table border=1 cellpadding=6>
        <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>Score</th>
            <th>Action</th>
        </tr>

        {% for coin in results %}
        <tr>
            <td>{{ coin.pair }}</td>
            <td>{{ coin.price }}</td>
            <td>{{ coin.score }}</td>
            <td>{{ coin.action }}</td>
        </tr>
        {% endfor %}
    </table>
    """

    return render_template_string(
        html,
        time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        results=results_sorted
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)