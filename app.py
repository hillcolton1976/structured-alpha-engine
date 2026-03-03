from flask import Flask, render_template_string, request, jsonify
import os

app = Flask(__name__)

balance = 50.0
positions = {}

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
            th, td { padding:8px; }
            th { border-bottom:1px solid #30363d; }
            tr { border-bottom:1px solid #21262d; }
        </style>
    </head>
    <body>

        <h1>🚀 Browser Powered Momentum Bot</h1>

        <div class="card">
            <h3>Balance: $<span id="balance">50.00</span></h3>
        </div>

        <div class="card">
            <h3>Live Prices</h3>
            <table>
                <tr><th>Coin</th><th>Price</th></tr>
                <tbody id="prices"></tbody>
            </table>
        </div>

        <script>
            const coins = ["bitcoin","ethereum","solana","ripple","dogecoin"];

            async function fetchPrices() {
                try {
                    const response = await fetch(
                        "https://api.coingecko.com/api/v3/simple/price?ids=" 
                        + coins.join(",") 
                        + "&vs_currencies=usd"
                    );

                    const data = await response.json();

                    const table = document.getElementById("prices");
                    table.innerHTML = "";

                    for (let coin of coins) {
                        if (data[coin]) {
                            table.innerHTML += `
                                <tr>
                                    <td>${coin.toUpperCase()}</td>
                                    <td>$${data[coin].usd}</td>
                                </tr>
                            `;
                        }
                    }

                } catch (error) {
                    console.log("Fetch error:", error);
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