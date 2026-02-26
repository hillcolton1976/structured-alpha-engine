const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

async function getSignals() {
  // 1️⃣ Get all Kraken trading pairs
  const assetPairs = await axios.get(
    "https://api.kraken.com/0/public/AssetPairs"
  );

  const allPairs = Object.values(assetPairs.data.result);

  // 2️⃣ Filter USD pairs only
  const usdPairs = allPairs
    .filter(p => p.wsname && p.wsname.endsWith("/USD"))
    .map(p => p.altname);

  // Limit scan to top 25 pairs (performance safety)
  const pairsToScan = usdPairs.slice(0, 25);

  // 3️⃣ Fetch all tickers in parallel
  const requests = pairsToScan.map(pair =>
    axios.get(`https://api.kraken.com/0/public/Ticker?pair=${pair}`)
  );

  const responses = await Promise.all(requests);

  let results = [];

  responses.forEach((response, index) => {
    const pair = pairsToScan[index];
    const dataKey = Object.keys(response.data.result)[0];
    const ticker = response.data.result[dataKey];

    const price = parseFloat(ticker.c[0]);
    const volume = parseFloat(ticker.v[1]);
    const high = parseFloat(ticker.h[1]);
    const low = parseFloat(ticker.l[1]);
    const open = parseFloat(ticker.o);

    const changePercent = ((price - open) / open) * 100;
    const volatility = ((high - low) / low) * 100;

    let score = 0;

    // Volume strength
    if (volume > 5000000) score += 3;
    else if (volume > 1000000) score += 2;

    // Momentum
    if (changePercent > 3) score += 3;
    else if (changePercent > 1) score += 2;

    // Volatility expansion
    if (volatility > 5) score += 2;

    // Premium asset tier
    if (price > 100) score += 1;

    let action = "HOLD";
    if (score >= 7) action = "BUY";
    if (score <= 2) action = "AVOID";

    results.push({
      pair,
      price,
      volume,
      changePercent: changePercent.toFixed(2),
      volatility: volatility.toFixed(2),
      score,
      action
    });
  });

  results.sort((a, b) => b.score - a.score);

  return results.slice(0, 15); // top 15 only
}

// API endpoint
app.get("/signals", async (req, res) => {
  try {
    const results = await getSignals();
    res.json({
      timestamp: new Date(),
      best_trade: results[0],
      top_trades: results
    });
  } catch (error) {
    res.status(500).json({ error: "Engine failed" });
  }
});

// Dashboard UI
app.get("/", async (req, res) => {
  try {
    const results = await getSignals();

    let rows = results.map(r => {
      let color =
        r.action === "BUY" ? "#00ff88" :
        r.action === "AVOID" ? "#ff4d4d" :
        "#ffd700";

      return `
        <tr>
          <td>${r.pair}</td>
          <td>$${r.price.toFixed(2)}</td>
          <td>${r.changePercent}%</td>
          <td>${r.volatility}%</td>
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
        <meta http-equiv="refresh" content="20">
        <style>
          body {
            background: #0f172a;
            color: white;
            font-family: Arial;
            padding: 20px;
          }
          h1 {
            text-align: center;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
          }
          th, td {
            padding: 12px;
            border-bottom: 1px solid #334155;
            text-align: center;
          }
          th {
            background: #1e293b;
          }
          tr:hover {
            background: #1e293b;
          }
        </style>
      </head>
      <body>
        <h1>📊 Structured Alpha Market Scanner</h1>

        <table>
          <tr>
            <th>Pair</th>
            <th>Price</th>
            <th>24h %</th>
            <th>Volatility %</th>
            <th>Score</th>
            <th>Signal</th>
          </tr>
          ${rows}
        </table>

        <p style="text-align:center; margin-top:20px; opacity:0.6;">
          Auto-refresh every 20 seconds
        </p>

      </body>
      </html>
    `);

  } catch (error) {
    res.send("Engine error");
  }
});

app.listen(PORT, () => {
  console.log("Scanner running on port " + PORT);
});