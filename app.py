from flask import Flask, render_template_string
import requests
from datetime import datetime
import statistics

app = Flask(__name__)

ASSET_PAIRS_API = "https://api.kraken.com/0/public/AssetPairs"
OHLC_API = "https://api.kraken.com/0/public/OHLC"


def get_usd_pairs():
    response = requests.get(ASSET_PAIRS_API)
    data = response.json().get("result", {})
    return [
        pair for pair, details in data.items()
        if details.get("quote") == "ZUSD" and details.get("wsname")
    ]


def get_daily_closes(pair):
    response = requests.get(f"{OHLC_API}?pair={pair}&interval=1440")
    data = response.json().get("result", {})
    if not data:
        return []

    key = list(data.keys())[0]
    candles = data[key]

    closes = [float(c[4]) for c in candles]
    return closes


def score_pair(pair):
    try:
        closes = get_daily_closes(pair)

        if len(closes) < 200:
            return None

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
            "ma50": round(ma50, 4),
            "ma200": round(ma200, 4),
            "90d_change": round(change_90, 2),
            "score": score,
            "action": action
        }

    except:
        return None


@app.route("/")
def home():

    pairs = get_usd_pairs()[:60]  # limit for speed
    results = []

    for pair in pairs:
        scored = score_pair(pair)
        if scored:
            results.append(scored)

    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
    top_30 = results_sorted[:30]

    html = """
    <h1>📈 Long-Term Crypto Scanner (6–8 Month Model)</h1>
    <p>Updated: {{ time }}</p>

    <table border=1 cellpadding=6>
        <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>MA50</th>
            <th>MA200</th>
            <th>90d %</th>
            <th>Score</th>
            <th>Action</th>
        </tr>

        {% for coin in top %}
        <tr>
            <td>{{ coin.pair }}</td>
            <td>{{ coin.price }}</td>
            <td>{{ coin.ma50 }}</td>
            <td>{{ coin.ma200 }}</td>
            <td>{{ coin.90d_change }}%</td>
            <td>{{ coin.score }}</td>
            <td>{{ coin.action }}</td>
        </tr>
        {% endfor %}
    </table>
    """

    return render_template_string(
        html,
        time=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        top=top_30
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)