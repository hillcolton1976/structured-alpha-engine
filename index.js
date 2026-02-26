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

      if (volume > 1000000) score += 3;
      if (price > 50) score += 2;
      if (price > 1000) score += 2;

      let action = "HOLD";
      if (score >= 6) action = "BUY";

      results.push({ pair, price, volume, score, action });
    }

    const qualified = results.filter(r => r.score >= 6);

    if (qualified.length === 0) {
      return res.json({ message: "NO TRADE - Market not strong enough" });
    }

    qualified.sort((a, b) => b.score - a.score);

    res.json({
      best_trade: qualified[0],
      qualified_trades: qualified
    });

  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});