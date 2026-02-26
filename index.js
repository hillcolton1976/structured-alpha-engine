const express = require("express");
const axios = require("axios");

const app = express();
const PORT = process.env.PORT || 8080;

app.get("/", (req, res) => {
  res.send("Structured Alpha Engine Running");
});

app.get("/signals", async (req, res) => {
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

      if (price > 1) score += 2;
      if (volume > 100000) score += 2;
      if (Math.random() > 0.5) score += 2;

      let action = "HOLD";
      if (score >= 4) action = "BUY";
      if (score <= 1) action = "SELL";

      results.push({
        pair,
        price,
        volume,
        score,
        action
      });
    }

    results.sort((a, b) => b.score - a.score);

    res.json({
      best_trade: results[0],
      all_pairs: results
    });

  } catch (error) {
    res.status(500).json({ error: "Failed to fetch market data" });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});