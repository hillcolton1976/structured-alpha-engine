from flask import Flask, render_template_string
import requests
from datetime import datetime

app = Flask(__name__)

TICKER_API = "https://api.kraken.com/0/public/Ticker"
ASSET_PAIRS_API = "https://api.kraken.com/0/public/AssetPairs"


def get_usd_pairs():
    response = requests.get(ASSET_PAIRS_API)
    data = response.json().get("result", {})
    return [
        pair for pair, details in data.items()
        if details.get("quote") == "ZUSD" and details.get("wsname")
    ]


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

            if vwap_24h == 0 or high_24h == low_24h:
                continue

            change_percent = ((price - vwap_24h) / vwap_24h) * 100
            range_position = (price - low_24h) / (high_24h - low_24h)

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


@app.route("/")
def home():
    market = score_market()
    market_sorted = sorted(market, key=lambda x: x["score"], reverse=True)

    top_30 = market_sorted[:30]
    all_sells = [m for m in market if m["action"] in ["SELL", "STRONG SELL"]]

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kraken Market Scanner</title>

        <meta name="viewport" content="width=device-width, initial-scale=1">

        <script>
            setTimeout(function(){
               window.location.reload(1);
            }, 30000);
        </script>

        <style>
            body {
                margin: 0;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
                color: white;
                padding: 30px;
            }

            h1 {
                font-size: 28px;
                margin-bottom: 5px;
            }

            .card {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(12px);
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 30px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.3);
            }

            table {
                width: 100%;
                border-collapse: collapse;
            }

            th {
                text-align: left;
                padding: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.2);
                font-size: 14px;
                opacity: 0.8;
            }

            td {
                padding: 10px;
                border-bottom: 1px solid rgba(255,255,255,0.08);
                font-size: 14px;
            }

            tr:hover {
                background: rgba(255,255,255,0.05);
            }

            .badge {
                padding: 4px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                display: inline-block;
            }

            .BUY { background: #00c853; }
            .STRONGBUY { background: #00e676; }
            .SELL { background: #ff5252; }
            .STRONGSELL { background: #d50000; }
            .HOLD { background: #757575; }

            .positive { color: #00e676; }
            .negative { color: #ff5252; }

            .timestamp {
                font-size: 13px;
                opacity: 0.7;
                margin-bottom: 20px;
            }

            @media(max-width: 600px) {
                body { padding: 15px; }
                th, td { font-size: 12px; }
            }
        </style>
    </head>

    <body>

        <h1>🚀 Kraken Market Scanner</h1>
        <div class="timestamp">
            Updated: {{ time }} • Auto refresh 30s
        </div>

        <div class="card">
            <h2>🔥 Top 30 Strongest</h2>
            <table>
                <tr>
                    <th>Pair</th>
                    <th>Price</th>
                    <th>24h %</th>
                    <th>Score</th>
                    <th>Action</th>
                </tr>
                {% for coin in top %}
                <tr>
                    <td>{{ coin.pair }}</td>
                    <td>{{ coin.price }}</td>
                    <td class="{{ 'positive' if coin.change > 0 else 'negative' }}">
                        {{ coin.change }}%
                    </td>
                    <td>{{ coin.score }}</td>
                    <td>
                        <span class="badge {{ coin.action.replace(' ', '') }}">
                            {{ coin.action }}
                        </span>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <div class="card">
            <h2>📉 All SELL Signals</h2>
            <table>
                <tr>
                    <th>Pair</th>
                    <th>Price</th>
                    <th>24h %</th>
                    <th>Score</th>
                    <th>Action</th>
                </tr>
                {% for coin in sells %}
                <tr>
                    <td>{{ coin.pair }}</td>
                    <td>{{ coin.price }}</td>
                    <td class="negative">{{ coin.change }}%</td>
                    <td>{{ coin.score }}</td>
                    <td>
                        <span class="badge {{ coin.action.replace(' ', '') }}">
                            {{ coin.action }}
                        </span>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>

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