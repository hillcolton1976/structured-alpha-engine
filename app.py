from flask import Flask, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

KRAKEN_API = "https://api.kraken.com/0/public/Ticker"

PAIRS = {
    "XRP": "XRPUSD",
    "SOL": "SOLUSD",
    "PEPE": "PEPEUSD",
    "SHIB": "SHIBUSD",
    "COQ": "COQUSD"
}

def get_market_data():
    pairs_string = ",".join(PAIRS.values())
    response = requests.get(f"{KRAKEN_API}?pair={pairs_string}")
    data = response.json().get("result", {})

    results = []

    for coin, pair in PAIRS.items():
        if pair not in data:
            continue

        ticker = data[pair]

        price = float(ticker["c"][0])
        vwap_24h = float(ticker["p"][1])
        volume_24h = float(ticker["v"][1])
        low_24h = float(ticker["l"][1])
        high_24h = float(ticker["h"][1])

        change_percent = ((price - vwap_24h) / vwap_24h) * 100

        score = 0

        # Momentum
        if change_percent > 2:
            score += 2
        elif change_percent < -2:
            score -= 2

        # Trend
        if price > vwap_24h:
            score += 1
        else:
            score -= 1

        # Range position
        range_position = (price - low_24h) / (high_24h - low_24h + 1e-9)
        if range_position > 0.75:
            score += 1
        elif range_position < 0.25:
            score -= 1

        # Volume boost
        if volume_24h > 1_000_000:
            score += 1

        # Signal mapping
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
            "coin": coin,
            "price": price,
            "change_24h_percent": round(change_percent, 2),
            "volume_24h": volume_24h,
            "score": score,
            "action": action
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)


@app.route("/")
def home():
    market = get_market_data()

    html = """
    <html>
    <head>
        <title>Crypto Signal Engine</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="30">
        <style>
            body {
                font-family: Arial;
                background:#0f1117;
                color:white;
                margin:0;
                padding:20px;
                text-align:center;
            }
            table {
                width:100%;
                max-width:1000px;
                margin:auto;
                border-collapse: collapse;
                background:#161b22;
            }
            th, td {
                padding:14px;
                border-bottom:1px solid #222;
            }
            th { background:#1f2937; }
            tr:hover { background:#1c2128; }

            .positive { color:#00ff88; font-weight:bold; }
            .negative { color:#ff4d4d; font-weight:bold; }
            .neutral  { color:#ffaa00; font-weight:bold; }

            .strongbuy { background:#003d1f; }
            .buy { background:#002a15; }
            .sell { background:#2a0000; }
            .strongsell { background:#3d0000; }
        </style>
    </head>
    <body>

        <h1>🚀 Crypto Signal Engine</h1>
        <p>Updated: {{timestamp}}</p>
        <p>Auto refresh every 30 seconds</p>

        <table>
            <tr>
                <th>Rank</th>
                <th>Coin</th>
                <th>Price</th>
                <th>24h %</th>
                <th>Volume</th>
                <th>Score</th>
                <th>Action</th>
            </tr>

            {% for item in market %}
            <tr class="{{item.action.lower().replace(' ','')}}">
                <td>{{loop.index}}</td>
                <td>{{item.coin}}</td>
                <td>${{item.price}}</td>

                <td class="{% if item.change_24h_percent > 0 %}positive{% elif item.change_24h_percent < 0 %}negative{% else %}neutral{% endif %}">
                    {{item.change_24h_percent}}%
                </td>

                <td>{{"{:,.0f}".format(item.volume_24h)}}</td>

                <td class="{% if item.score > 0 %}positive{% elif item.score < 0 %}negative{% else %}neutral{% endif %}">
                    {{item.score}}
                </td>

                <td><strong>{{item.action}}</strong></td>
            </tr>
            {% endfor %}
        </table>

    </body>
    </html>
    """

    return render_template_string(
        html,
        market=market,
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)