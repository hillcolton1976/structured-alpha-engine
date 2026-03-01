from flask import Flask, render_template_string
import requests

app = Flask(__name__)

STARTING_CASH = 50.0

account = {
    "cash": STARTING_CASH,
    "positions": {},
    "trades": 0,
    "wins": 0,
    "losses": 0
}

# -----------------------------
# COINGECKO MARKET DATA
# -----------------------------
def get_top_35():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 35,
            "page": 1,
            "price_change_percentage": "24h"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            return [], f"HTTP ERROR {response.status_code}"

        data = response.json()

        coins = []
        for coin in data:
            coins.append({
                "symbol": coin["symbol"].upper(),
                "price": coin["current_price"],
                "change": coin.get("price_change_percentage_24h", 0)
            })

        return coins, None

    except Exception as e:
        return [], str(e)


# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/")
def dashboard():

    coins, error = get_top_35()

    html = """
    <html>
    <meta http-equiv="refresh" content="15">
    <style>
    body { background:#0b1220; color:white; font-family:Arial; padding:20px;}
    .card { background:#1e293b; padding:20px; border-radius:12px; margin-bottom:20px;}
    table { width:100%; border-collapse:collapse;}
    th, td { padding:8px; border-bottom:1px solid #334155;}
    th { text-align:left;}
    .error { color:#ff6b6b; font-weight:bold;}
    </style>

    <h2>🔥 ELITE AI TRADER v4 (LIVE MARKET)</h2>

    {% if error %}
        <div class="card error">
            MARKET ERROR:<br>
            {{error}}
        </div>
    {% endif %}

    <div class="card">
    <h3>Top 35 Coins (Live)</h3>
    <table>
    <tr><th>Coin</th><th>Price</th><th>24h %</th></tr>
    {% for c in coins %}
    <tr>
    <td>{{c.symbol}}</td>
    <td>${{c.price}}</td>
    <td>{{c.change}}%</td>
    </tr>
    {% endfor %}
    </table>
    </div>

    </html>
    """

    return render_template_string(html, coins=coins, error=error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)