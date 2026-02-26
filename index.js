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

      let action = score >= 6 ? "BUY" : "HOLD";

      results.push({ pair, price, volume, score, action });
    }

    results.sort((a, b) => b.score - a.score);
    const best = results[0];

    const status =
      best.score >= 6
        ? "TRADE SIGNAL ACTIVE"
        : "MARKET CONDITIONS WEAK";

    const actionColor = best.score >= 6 ? "#00ff99" : "#facc15";

    const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Structured Alpha Engine</title>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {
          margin: 0;
          font-family: -apple-system, BlinkMacSystemFont, sans-serif;
          background: linear-gradient(135deg, #0f172a, #1e293b);
          color: white;
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 100vh;
        }
        .container {
          width: 90%;
          max-width: 420px;
        }
        .card {
          background: #1e293b;
          padding: 25px;
          border-radius: 18px;
          box-shadow: 0 10px 25px rgba(0,0,0,0.4);
          text-align: center;
          margin-bottom: 20px;
        }
        h1 { font-size: 24px; margin-bottom: 10px; }
        .pair { font-size: 28px; font-weight: bold; margin: 10px 0; }
        .price { font-size: 20px; }
        .score { font-size: 18px; }
        .volume { font-size: 14px; opacity: 0.7; }
        .action { font-size: 22px; font-weight: bold; color: ${actionColor}; }
        .small { font-size: 12px; opacity: 0.6; margin-top: 10px; }
      </style>
    </head>
    <body>
      <div class="container">
        <div class="card">
          <h1>Structured Alpha Engine</h1>
          <div>${status}</div>
          <div class="pair">${best.pair}</div>
          <div class="price">$${best.price.toLocaleString()}</div>
          <div class="score">Score: ${best.score} / 7</div>
          <div class="volume">Volume: ${best.volume.toLocaleString()}</div>
          <div class="action">${best.action}</div>
          <div class="small">Auto refresh every 30s</div>
        </div>
      </div>

      <script>
        setTimeout(() => location.reload(), 30000);
      </script>
    </body>
    </html>
    `;

    res.send(html);
  } catch (err) {
    res.status(500).send("Failed to fetch market data");
  }
});

app.listen(PORT, () => {
  console.log("Server running on port " + PORT);
});