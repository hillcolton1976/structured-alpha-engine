const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

app.get("/", async (req, res) => {
  try {
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

      results.push({ pair, price, volume, score, action });
    }

    results.sort((a, b) => b.score - a.score);
    const best = results[0];

    const status = best.score >= 6 ? "🔥 TRADE ACTIVE" : "⏸ NO TRADE";

    res.send(`
      <html>
      <head>
        <title>Structured Alpha</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            background: #0f172a;
            color: white;
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 20px;
          }
          .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 16px;
            margin: 20px auto;
            max-width: 400px;
            box-shadow: 0 0 20px rgba(0,0,0,0.4);
          }
          h1 {
            font-size: 24px;
          }
          .status {
            font-size: 20px;
            margin-bottom: 15px;
          }
          .buy {
            color: #22c55e;
            font-weight: bold;
          }
          .hold {
            color: #facc15;
            font-weight: bold;
          }
          .pair {
            font-size: 22px;
            margin-top: 10px;
          }
          .refresh {
            margin-top: 20px;
            font-size: 14px;
            opacity: 0.6;
          }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Structured Alpha Engine</h1>
          <div class="status">${status}</div>
          <div class="pair">${best.pair}</div>
          <p>Price: $${best.price.toFixed(2)}</p>
          <p>Score: ${best.score}</p>
          <p class="${best.action === "BUY" ? "buy" : "hold"}">
            ${best.action}
          </p>
          <div class="refresh">Refresh page to update</div>
        </div>
      </body>
      </html>
    `);

  } catch (error) {
    res.status(500).send("Error loading market data");
  }
});

app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});