const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

// Fetch market data + calculate signals
async function getSignals() {
  const pairs = ["XBTUSD", "ETHUSD", "SOLUSD", "XRPUSD"];
  let results = [];

  for (let pair of pairs) {
    const response = await axios.get(
      `https://api.kraken.com/0/public/Ticker?pair=${pair}`
    );

    const dataKey = Object.keys(response.data.result)[0];
    const ticker = response.data.result[dataKey];

    const price = parseFloat(ticker.c[0]);
    const volume = parseFloat(ticker.v[1]);

    let score = 0;

    if (volume > 1000000) score += 3;
    if (price > 50) score += 2;
    if (price > 1000) score += 2;

    let action = "HOLD";
    if (score >= 6) action = "BUY";
    if (score <= 1) action = "SELL";

    results.push({ pair, price, volume, score, action });
  }

  results.sort((a, b) => b.score - a.score);
  return results;
}

// API endpoint
app.get("/signals", async (req, res) => {
  try {
    const results = await getSignals();
    res.json({
      timestamp: new Date(),
      best_trade: results[0],
      all_pairs: results
    });
  } catch (error) {
    res.status(500).json({ error: "Failed to fetch market data" });
  }
});

// 🔥 PRO DASHBOARD UI
app.get("/", async (req, res) => {
  try {
    const results = await getSignals();

    let rows = results.map(r => {
      let color =
        r.action === "BUY" ? "#00ff88" :
        r.action === "SELL" ? "#ff4d4d" :
        "#ffd700";

      return `
        <tr>
          <td>${r.pair}</td>
          <td>$${r.price.toFixed(2)}</td>
          <td>${r.score}</td>
          <td style="color:${color}; font-weight:bold;">
            ${r.action}
          </td>
        </tr>
      `;
    }).join("");

    res.send(`
      <html>
      <head>
        <title>Structured Alpha Engine</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="15">
        <style>
          body {
            background: #0f172a;
            color: white;
            font-family: Arial;
            text-align: center;
            padding: 20px;
          }
          h1 {
            margin-bottom: 20px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }
          th, td {
            padding: 14px;
            border-bottom: 1px solid #334155;
          }
          th {
            background: #1e293b;
          }
          tr:hover {
            background: #1e293b;
          }
          .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
          }
        </style>
      </head>
      <body>
        <h1>📊 Structured Alpha Engine</h1>

        <div class="card">
          <h2>🔥 Best Trade</h2>
          <h3>${results[0].pair}</h3>
          <p>Price: $${results[0].price.toFixed(2)}</p>
          <p>Score: ${results[0].score}</p>
          <p style="font-size:22px; font-weight:bold;">
            ${results[0].action}
          </p>
        </div>

        <table>
          <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>Score</th>
            <th>Signal</th>
          </tr>
          ${rows}
        </table>

        <p style="margin-top:20px; opacity:0.6;">
          Auto-refresh every 15 seconds
        </p>

      </body>
      </html>
    `);

  } catch (error) {
    res.send("Error loading dashboard");
  }
});

app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});