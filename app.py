from flask import Flask, render_template_string
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template_string("""
<html>
<head>
<title>Momentum Bot</title>
<style>
body { background:#0e1117; color:#e6edf3; font-family:Arial; padding:20px; }
h1 { color:#58a6ff; }
.card { background:#161b22; padding:15px; margin-bottom:20px; border-radius:10px; }
table { width:100%; border-collapse:collapse; }
th, td { padding:8px; text-align:left; }
th { border-bottom:1px solid #30363d; }
tr { border-bottom:1px solid #21262d; }
.green { color:#3fb950; }
.red { color:#f85149; }
</style>
</head>
<body>

<h1>🚀 Momentum Trader</h1>

<div class="card">
<h3>Balance: $<span id="balance">50.00</span></h3>
</div>

<div class="card">
<h3>Positions</h3>
<div id="positions">None</div>
</div>

<div class="card">
<h3>Live Prices</h3>
<table>
<tr><th>Coin</th><th>Price</th></tr>
<tbody id="prices"></tbody>
</table>
</div>

<script>
let balance = 50;
let positions = {};
let lastPrices = {};
const coins = ["bitcoin","ethereum","solana","ripple","dogecoin"];

async function fetchPrices() {
    const response = await fetch(
        "https://api.coingecko.com/api/v3/simple/price?ids=" 
        + coins.join(",") 
        + "&vs_currencies=usd"
    );
    const data = await response.json();

    const table = document.getElementById("prices");
    table.innerHTML = "";

    for (let coin of coins) {
        if (!data[coin]) continue;

        let price = data[coin].usd;
        table.innerHTML += `
            <tr>
                <td>${coin.toUpperCase()}</td>
                <td>$${price}</td>
            </tr>
        `;

        // Trading Logic
        if (lastPrices[coin]) {
            let change = (price - lastPrices[coin]) / lastPrices[coin];

            // Buy if strong upward momentum
            if (!positions[coin] && change > 0.003 && balance > 5) {
                let amount = 10;
                positions[coin] = {
                    entry: price,
                    amount: amount
                };
                balance -= amount;
            }

            // Sell if 1% profit
            if (positions[coin]) {
                let entry = positions[coin].entry;
                if (price >= entry * 1.01) {
                    let profit = positions[coin].amount * 1.01;
                    balance += profit;
                    delete positions[coin];
                }
            }
        }

        lastPrices[coin] = price;
    }

    document.getElementById("balance").innerText = balance.toFixed(2);

    // Update positions display
    let posDiv = document.getElementById("positions");
    if (Object.keys(positions).length === 0) {
        posDiv.innerHTML = "None";
    } else {
        let html = "";
        for (let coin in positions) {
            html += `<div class="green">${coin.toUpperCase()} @ $${positions[coin].entry}</div>`;
        }
        posDiv.innerHTML = html;
    }
}

fetchPrices();
setInterval(fetchPrices, 5000);
</script>

</body>
</html>
""")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)