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

      // Scoring Logic (Max 7)
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
        ? "🚨 TRADE SIGNAL ACTIVE 🚨"
        : "⏸ MARKET CONDITIONS WEAK";

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

        h1 {
          margin-bottom: 10px;
          font-size: 24px;
        }

        .status {
          font-size: 16px;
          margin-bottom: 15px;
        }

        .pair {
          font-size: 28px;
          font-weight: bold;
          margin: 10px 0;
        }

        .price {
          font-size: 20px;
          margin: 5px 0;
        }

        .score {
          font-size: 18px;
          margin: 5px 0;
        }

        .volume {
          font-size: 14px;
          opacity: 0.8;
          margin-bottom: 10px;
        }

        .action {
          font-size: 22px;
          font-weight: bold;
          color: ${actionColor};
        }

        .small {
          font-size: 12px;
          opacity: 0.6;
          margin-top: 10px;
        }

      </style>
    </head>
    <body>
      <div class="container">
        <div class="card">
          <h1>Structured Alpha Engine</h1>
          <div class="status">${status}</div>
          <div class="pair">${best.pair}</div>
          <div class="price">Price: $${best.price.toLocaleString()}</div>
          <div class="score">Score: ${best.score} / 7</div>
          <div class="volume">Volume: ${best.volume.toLocaleString()}</div>
          <div class="action">${best.action}</div>
          <div class="small">Auto-refresh every 30 seconds</div>
        </div>

        ${results
          .map(
            (r) => `
          <div class="card">
            <div class="pair">${r.pair}</div>
            <div class="price">$${r.price.toLocaleString()}</div>
            <div class="score">Score: ${r.score} / 7</div>
            <div class="action" style="color:${r.score >= 6 ? "#00ff99" : "#facc15"}">
              ${r.action}
            </div>
          </div>
        `
          )
          .join("")}
      </div>

      <script>
        setTimeout(() => {
          window.location.reload();
        }, 30000);
      </script>

    </body>
    </html>
    `;

    res.send(html);
  } catch (error) {
    res.status(500).send("Failed to fetch market data");
  }
});

app.listen(PORT, () => {
  console.log(\`Server running on port \${PORT}\`);
});